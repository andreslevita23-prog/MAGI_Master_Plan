from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_V2_DIR = RUN_DIR / "ceo_v2_tradeable"
DEFAULT_V1_MODEL = RUN_DIR / "models" / "ceo_baseline_model.joblib"

TARGET = "ceo_label_h48_tradeable"
LABELS = ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"]
THRESHOLDS = [0.50, 0.60, 0.70, 0.80]

CATEGORICAL_FEATURES = [
    "session",
    "weekday",
    "regime",
    "melchor_signal",
    "melchor_risk_flags",
    "baltasar_signal",
    "gaspar_signal",
    "mage_agreement",
    "baltasar_gaspar_alignment",
]

NUMERIC_FEATURES = [
    "hour",
    "spread",
    "atr",
    "daily_range_position",
    "melchor_confidence",
    "baltasar_confidence",
    "gaspar_confidence",
]

FEATURES = [
    "session",
    "hour",
    "weekday",
    "spread",
    "atr",
    "daily_range_position",
    "regime",
    "melchor_signal",
    "melchor_confidence",
    "melchor_risk_flags",
    "baltasar_signal",
    "baltasar_confidence",
    "gaspar_signal",
    "gaspar_confidence",
    "mage_agreement",
    "baltasar_gaspar_alignment",
]

FORBIDDEN_FEATURES = {
    "future_outcome_h12",
    "future_outcome_h48",
    "future_outcome_h96",
    "future_outcome_h288",
    "future_return",
    "future_return_pips",
    "MFE",
    "MAE",
    "max_favorable_excursion",
    "max_adverse_excursion",
    "ceo_label_h48",
    "ceo_label_h48_tradeable",
}


def main() -> int:
    args = parse_args()
    setup_logging()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    verify_no_leakage()

    train_df = read_split(output_dir / "train.parquet")
    validation_df = read_split(output_dir / "validation.parquet")
    test_df = read_split(output_dir / "test.parquet")
    logging.info("Rows train=%s validation=%s test=%s", len(train_df), len(validation_df), len(test_df))

    pipeline = build_pipeline()
    logging.info("Training CEO v2 RandomForestClassifier")
    pipeline.fit(train_df[FEATURES], train_df[TARGET])

    model_payload = {
        "schema_version": "ceo_v2_tradeable_model_v0.1",
        "trained_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model_type": "RandomForestClassifier",
        "target": TARGET,
        "features": FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "pipeline": pipeline,
    }
    joblib.dump(model_payload, output_dir / "ceo_v2_tradeable_model.joblib")
    logging.info("Model written: %s", output_dir / "ceo_v2_tradeable_model.joblib")

    v1_model = load_v1_model(Path(args.v1_model))
    metrics = build_metrics(pipeline, v1_model, train_df, validation_df, test_df)
    (output_dir / "ceo_v2_tradeable_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    importances = feature_importances(pipeline)
    write_feature_importance(output_dir / "ceo_v2_feature_importance.csv", importances)
    (output_dir / "ceo_v2_tradeable_summary.md").write_text(markdown_summary(metrics, importances), encoding="utf-8")
    logging.info("Metrics, summary and feature importance written to %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train CEO-MAGI v2 tradeable model.")
    parser.add_argument("--output-dir", default=str(DEFAULT_V2_DIR), help="CEO v2 output directory containing splits.")
    parser.add_argument("--v1-model", default=str(DEFAULT_V1_MODEL), help="CEO v1 model joblib path.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def verify_no_leakage() -> None:
    forbidden = sorted(set(FEATURES) & FORBIDDEN_FEATURES)
    if forbidden:
        raise ValueError(f"Forbidden columns in FEATURES: {forbidden}")


def read_split(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing split: {path}")
    df = pd.read_parquet(path)
    missing = [column for column in [*FEATURES, TARGET] if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")
    return df


def build_pipeline() -> Pipeline:
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    numeric = Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))])
    preprocess = ColumnTransformer(
        transformers=[
            ("categorical", categorical, CATEGORICAL_FEATURES),
            ("numeric", numeric, NUMERIC_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )
    model = RandomForestClassifier(
        n_estimators=160,
        max_depth=10,
        min_samples_leaf=80,
        class_weight="balanced_subsample",
        random_state=84,
        n_jobs=1,
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def build_metrics(
    pipeline: Pipeline,
    v1_model: Pipeline | None,
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict[str, Any]:
    frames = {"train": train_df, "validation": validation_df, "test": test_df}
    split_metrics = {name: evaluate_split(pipeline, frame) for name, frame in frames.items()}
    threshold_metrics = {
        name: {
            f"{threshold:.2f}": evaluate_predictions(frame[TARGET], threshold_predictions(pipeline, frame, threshold))
            for threshold in THRESHOLDS
        }
        for name, frame in frames.items()
    }
    comparisons = {
        name: comparison_metrics(frame, v1_model)
        for name, frame in frames.items()
    }
    return {
        "schema_version": "ceo_v2_tradeable_metrics_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model": {
            "type": "RandomForestClassifier",
            "params": {
                "n_estimators": 160,
                "max_depth": 10,
                "min_samples_leaf": 80,
                "class_weight": "balanced_subsample",
                "random_state": 84,
                "n_jobs": 1,
            },
        },
        "target": TARGET,
        "features": FEATURES,
        "leakage_check": {"passed": True, "forbidden_features_in_model": []},
        "split_metrics_argmax": split_metrics,
        "threshold_metrics": threshold_metrics,
        "comparisons": comparisons,
        "technical_decisions": [
            "The v2 model is trained against ceo_label_h48_tradeable, not ceo_label_h48.",
            "No future outcome columns or labels are used as features.",
            "Threshold decisions only execute ENTER_BUY/ENTER_SELL when that class probability is the largest action probability and exceeds the threshold; otherwise DO_NOTHING.",
            "CEO v1 comparison loads the saved v1 pipeline and evaluates its predictions against the v2 tradeable target.",
            "n_jobs=1 avoids Windows sandbox/joblib worker permission issues.",
        ],
    }


def evaluate_split(pipeline: Pipeline, df: pd.DataFrame) -> dict[str, Any]:
    predictions = pd.Series(pipeline.predict(df[FEATURES]), index=df.index)
    return evaluate_predictions(df[TARGET], predictions)


def threshold_predictions(pipeline: Pipeline, df: pd.DataFrame, threshold: float) -> pd.Series:
    probabilities = pipeline.predict_proba(df[FEATURES])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY") if "ENTER_BUY" in classes else None
    sell_idx = classes.index("ENTER_SELL") if "ENTER_SELL" in classes else None
    predictions = []
    for row in probabilities:
        buy_prob = row[buy_idx] if buy_idx is not None else 0.0
        sell_prob = row[sell_idx] if sell_idx is not None else 0.0
        if buy_prob >= sell_prob and buy_prob >= threshold:
            predictions.append("ENTER_BUY")
        elif sell_prob > buy_prob and sell_prob >= threshold:
            predictions.append("ENTER_SELL")
        else:
            predictions.append("DO_NOTHING")
    return pd.Series(predictions, index=df.index)


def evaluate_predictions(y_true: pd.Series, predictions: pd.Series) -> dict[str, Any]:
    y_true = y_true.astype(str)
    predictions = predictions.astype(str)
    report = classification_report(y_true, predictions, labels=LABELS, output_dict=True, zero_division=0)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    trades_taken = int(trades.sum())
    correct_trades = int((predictions[trades] == y_true[trades]).sum()) if trades_taken else 0
    return {
        "accuracy": round(float(accuracy_score(y_true, predictions)), 6),
        "macro_f1": round(float(f1_score(y_true, predictions, labels=LABELS, average="macro", zero_division=0)), 6),
        "precision_by_class": {label: round(float(report[label]["precision"]), 6) for label in LABELS},
        "recall_by_class": {label: round(float(report[label]["recall"]), 6) for label in LABELS},
        "confusion_matrix": matrix_dict(y_true, predictions),
        "trades_taken": trades_taken,
        "coverage": safe_div(trades_taken, len(y_true)),
        "trade_precision": safe_div(correct_trades, trades_taken),
        "buy_precision": precision_for(predictions, y_true, buy_trades),
        "sell_precision": precision_for(predictions, y_true, sell_trades),
        "prediction_distribution": value_counts(predictions),
        "actual_distribution": value_counts(y_true),
    }


def comparison_metrics(df: pd.DataFrame, v1_model: Pipeline | None) -> dict[str, Any]:
    y_true = df[TARGET]
    comparisons = {
        "always_do_nothing": evaluate_predictions(y_true, pd.Series(["DO_NOTHING"] * len(df), index=df.index)),
        "baltasar_only": evaluate_predictions(y_true, baltasar_only_predictions(df)),
    }
    if v1_model is not None:
        comparisons["ceo_v1_model"] = evaluate_predictions(y_true, pd.Series(v1_model.predict(df[FEATURES]), index=df.index))
    else:
        comparisons["ceo_v1_model"] = None
    return comparisons


def baltasar_only_predictions(df: pd.DataFrame) -> pd.Series:
    signal = df["baltasar_signal"].fillna("").astype(str).str.upper()
    predictions = pd.Series(["DO_NOTHING"] * len(df), index=df.index)
    predictions.loc[signal == "BUY"] = "ENTER_BUY"
    predictions.loc[signal == "SELL"] = "ENTER_SELL"
    return predictions


def load_v1_model(path: Path) -> Pipeline | None:
    if not path.exists():
        logging.warning("CEO v1 model not found: %s", path)
        return None
    payload = joblib.load(path)
    pipeline = payload.get("pipeline") if isinstance(payload, dict) else payload
    return pipeline


def matrix_dict(y_true: pd.Series, y_pred: pd.Series) -> dict[str, dict[str, int]]:
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)
    return {
        actual: {predicted: int(matrix[row][col]) for col, predicted in enumerate(LABELS)}
        for row, actual in enumerate(LABELS)
    }


def precision_for(predictions: pd.Series, actual: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if not total:
        return None
    return round(float((predictions[mask] == actual[mask]).sum()) / total, 6)


def feature_importances(pipeline: Pipeline) -> list[dict[str, Any]]:
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    importances = pipeline.named_steps["model"].feature_importances_
    rows = [
        {"feature": str(name), "importance": round(float(importance), 10)}
        for name, importance in zip(names, importances, strict=False)
    ]
    rows.sort(key=lambda item: item["importance"], reverse=True)
    return rows


def write_feature_importance(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["feature", "importance"])
        writer.writeheader()
        writer.writerows(rows)


def value_counts(series: pd.Series) -> dict[str, int]:
    return dict(sorted(Counter("UNKNOWN" if pd.isna(value) else str(value) for value in series).items()))


def safe_div(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 6)


def markdown_summary(metrics: dict[str, Any], importances: list[dict[str, Any]]) -> str:
    lines = [
        "# CEO-MAGI v2 Tradeable Model",
        "",
        f"- generated_at: {metrics['generated_at']}",
        "- model: RandomForestClassifier",
        f"- target: `{metrics['target']}`",
        f"- leakage_check_passed: {metrics['leakage_check']['passed']}",
        "",
        "## Argmax Metrics",
        "| Split | Accuracy | Macro F1 | Trades | Coverage | Trade precision | BUY precision | SELL precision |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("train", "validation", "test"):
        row = metrics["split_metrics_argmax"][split]
        lines.append(metric_row(split, row))

    lines.extend(["", "## Threshold Metrics", "| Split | Threshold | Trades | Coverage | Trade precision | BUY precision | SELL precision | Predictions |", "|---|---:|---:|---:|---:|---:|---:|---|"])
    for split in ("validation", "test"):
        for threshold, row in metrics["threshold_metrics"][split].items():
            lines.append(
                f"| {split} | {threshold} | {row['trades_taken']} | {fmt_pct(row['coverage'])} | "
                f"{fmt_pct(row['trade_precision'])} | {fmt_pct(row['buy_precision'])} | {fmt_pct(row['sell_precision'])} | "
                f"{json.dumps(row['prediction_distribution'], sort_keys=True)} |"
            )

    lines.extend(["", "## Comparisons", "| Split | Policy | Trades | Coverage | Trade precision | BUY precision | SELL precision |", "|---|---|---:|---:|---:|---:|---:|"])
    for split in ("validation", "test"):
        for policy, row in metrics["comparisons"][split].items():
            if row is None:
                continue
            lines.append(
                f"| {split} | {policy} | {row['trades_taken']} | {fmt_pct(row['coverage'])} | "
                f"{fmt_pct(row['trade_precision'])} | {fmt_pct(row['buy_precision'])} | {fmt_pct(row['sell_precision'])} |"
            )

    lines.extend(["", "## Top Feature Importances", "| Rank | Feature | Importance |", "|---:|---|---:|"])
    for index, row in enumerate(importances[:20], 1):
        lines.append(f"| {index} | `{row['feature']}` | {row['importance']:.6f} |")
    lines.extend(["", "## Technical Decisions"])
    lines.extend(f"- {item}" for item in metrics["technical_decisions"])
    return "\n".join(lines) + "\n"


def metric_row(split: str, row: dict[str, Any]) -> str:
    return (
        f"| {split} | {fmt_pct(row['accuracy'])} | {fmt_pct(row['macro_f1'])} | {row['trades_taken']} | "
        f"{fmt_pct(row['coverage'])} | {fmt_pct(row['trade_precision'])} | "
        f"{fmt_pct(row['buy_precision'])} | {fmt_pct(row['sell_precision'])} |"
    )


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
