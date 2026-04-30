from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from sklearn.utils.class_weight import compute_sample_weight


DEFAULT_DATASET = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet")
DEFAULT_SUMMARY = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features_summary.json")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_v2_rich_features_model")
PURE_DIRECTIONAL_METRICS = Path("data/output/magi_v2/baltasar_v2_pure_directional/baltasar_v2_pure_directional_metrics.json")

TARGET = "tradeable_direction_rr2_first_touch"
LABELS = ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"]
THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70]

TRAIN_START = "2020-01-15"
TRAIN_END = "2023-12-31 23:59:59"
VALIDATION_START = "2024-01-01"
VALIDATION_END = "2024-12-31 23:59:59"
TEST_START = "2025-01-01"
TEST_END = "2026-04-14 23:59:59"

FORBIDDEN_FEATURES = {
    TARGET,
    "buy_R",
    "sell_R",
    "buy_first_touch",
    "sell_first_touch",
    "same_bar_ambiguous_flag",
    "buy_outcome",
    "sell_outcome",
    "buy_bars_to_exit",
    "sell_bars_to_exit",
    "future_outcomes",
    "future_return",
    "future_return_pips",
}


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = load_json(Path(args.summary))
    feature_columns = list(summary["feature_columns"])
    diagnostic_columns = list(summary["diagnostic_columns"])
    verify_no_leakage(feature_columns, diagnostic_columns)

    df = read_dataset(Path(args.dataset), feature_columns, diagnostic_columns)
    train_df, validation_df, test_df = split_temporally(df)
    train_df.to_parquet(output_dir / "train.parquet", index=False)
    validation_df.to_parquet(output_dir / "validation.parquet", index=False)
    test_df.to_parquet(output_dir / "test.parquet", index=False)
    logging.info("Split rows train=%s validation=%s test=%s", len(train_df), len(validation_df), len(test_df))

    categorical_features, numeric_features = infer_feature_types(train_df, feature_columns)
    pipeline = build_pipeline(categorical_features, numeric_features)
    weights = compute_sample_weight(class_weight="balanced", y=train_df[TARGET])
    logging.info("Training HistGradientBoostingClassifier with %s features", len(feature_columns))
    pipeline.fit(train_df[feature_columns], train_df[TARGET], model__sample_weight=weights)

    payload = {
        "schema_version": "baltasar_v2_rich_model_v0.1",
        "trained_at": utc_now(),
        "model_type": "HistGradientBoostingClassifier",
        "target": TARGET,
        "features": feature_columns,
        "categorical_features": categorical_features,
        "numeric_features": numeric_features,
        "diagnostic_columns": diagnostic_columns,
        "pipeline": pipeline,
    }
    joblib.dump(payload, output_dir / "baltasar_v2_rich_model.joblib")

    metrics = build_metrics(pipeline, train_df, validation_df, test_df, feature_columns, summary)
    (output_dir / "baltasar_v2_rich_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    importances = feature_importances(pipeline, validation_df, feature_columns)
    write_feature_importance(output_dir / "baltasar_v2_rich_feature_importance.csv", importances)
    (output_dir / "baltasar_v2_rich_summary.md").write_text(markdown_summary(metrics, importances), encoding="utf-8")
    logging.info("Outputs written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Baltasar v2 rich features model.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Rich feature dataset parquet.")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="Rich feature dataset summary JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_no_leakage(feature_columns: list[str], diagnostic_columns: list[str]) -> None:
    forbidden = sorted(set(feature_columns) & (FORBIDDEN_FEATURES | set(diagnostic_columns)))
    if forbidden:
        raise ValueError(f"Forbidden columns in feature_columns: {forbidden}")


def read_dataset(path: Path, feature_columns: list[str], diagnostic_columns: list[str]) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    required = ["timestamp", TARGET, *feature_columns, *diagnostic_columns]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df.sort_values("timestamp").reset_index(drop=True)


def split_temporally(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        between(df, TRAIN_START, TRAIN_END),
        between(df, VALIDATION_START, VALIDATION_END),
        between(df, TEST_START, TEST_END),
    )


def between(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    return df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)].copy()


def infer_feature_types(df: pd.DataFrame, feature_columns: list[str]) -> tuple[list[str], list[str]]:
    categorical = []
    numeric = []
    for column in feature_columns:
        if pd.api.types.is_numeric_dtype(df[column]):
            numeric.append(column)
        else:
            categorical.append(column)
    return categorical, numeric


def build_pipeline(categorical_features: list[str], numeric_features: list[str]) -> Pipeline:
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("ordinal", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
        ]
    )
    numeric = Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))])
    preprocess = ColumnTransformer(
        transformers=[
            ("categorical", categorical, categorical_features),
            ("numeric", numeric, numeric_features),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )
    model = HistGradientBoostingClassifier(
        max_iter=90,
        learning_rate=0.06,
        max_leaf_nodes=31,
        l2_regularization=0.03,
        early_stopping=True,
        validation_fraction=0.12,
        n_iter_no_change=10,
        random_state=707,
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def build_metrics(
    pipeline: Pipeline,
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: list[str],
    dataset_summary: dict[str, Any],
) -> dict[str, Any]:
    frames = {"train": train_df, "validation": validation_df, "test": test_df}
    metrics = {
        "schema_version": "baltasar_v2_rich_metrics_v0.1",
        "generated_at": utc_now(),
        "model": {
            "type": "HistGradientBoostingClassifier",
            "params": {
                "max_iter": 90,
                "learning_rate": 0.06,
                "max_leaf_nodes": 31,
                "l2_regularization": 0.03,
                "early_stopping": True,
                "random_state": 707,
            },
        },
        "target": TARGET,
        "features": feature_columns,
        "feature_count": len(feature_columns),
        "diagnostic_columns": dataset_summary["diagnostic_columns"],
        "leakage_check": {"passed": True, "forbidden_features_in_model": []},
        "splits": {
            split: {
                "rows": len(frame),
                "start": frame["timestamp"].min().isoformat(),
                "end": frame["timestamp"].max().isoformat(),
                "target_distribution": dict(Counter(frame[TARGET])),
            }
            for split, frame in frames.items()
        },
        "argmax": {
            split: evaluate_predictions(frame, pd.Series(pipeline.predict(frame[feature_columns]), index=frame.index))
            for split, frame in frames.items()
        },
        "thresholds": {
            split: {
                f"{threshold:.2f}": evaluate_predictions(frame, threshold_predictions(pipeline, frame, feature_columns, threshold))
                for threshold in THRESHOLDS
            }
            for split, frame in frames.items()
        },
        "comparisons": {
            "always_do_nothing": {
                split: evaluate_predictions(frame, pd.Series(["DO_NOTHING"] * len(frame), index=frame.index))
                for split, frame in frames.items()
            },
            "baltasar_v1_signal": load_baltasar_v1_comparison(),
            "baltasar_v2_pure_directional": load_pure_directional_comparison(),
        },
        "technical_decisions": [
            "Feature list is loaded exclusively from baltasar_v2_rich_features_summary.json.",
            "Diagnostic columns are used only for operational R metrics.",
            "Categorical features use OrdinalEncoder for HGB runtime practicality.",
            "RandomForest was not trained in this run because HGB was prioritized and previous RF baselines were slower/weaker.",
            "No mage logic or Baltasar v1 artifact is modified.",
        ],
    }
    return metrics


def threshold_predictions(pipeline: Pipeline, df: pd.DataFrame, feature_columns: list[str], threshold: float) -> pd.Series:
    probabilities = pipeline.predict_proba(df[feature_columns])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    out = []
    for row in probabilities:
        buy_prob = float(row[buy_idx])
        sell_prob = float(row[sell_idx])
        if buy_prob >= sell_prob and buy_prob >= threshold:
            out.append("ENTER_BUY")
        elif sell_prob > buy_prob and sell_prob >= threshold:
            out.append("ENTER_SELL")
        else:
            out.append("DO_NOTHING")
    return pd.Series(out, index=df.index)


def evaluate_predictions(df: pd.DataFrame, predictions: pd.Series) -> dict[str, Any]:
    y_true = df[TARGET].astype(str)
    predictions = predictions.astype(str)
    report = classification_report(y_true, predictions, labels=LABELS, output_dict=True, zero_division=0)
    matrix = confusion_matrix(y_true, predictions, labels=LABELS)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    trade_r = [value for value, is_trade in zip(realized_r(df, predictions), trades, strict=False) if is_trade and value is not None]
    return {
        "accuracy": round_float(accuracy_score(y_true, predictions)),
        "macro_f1": round_float(f1_score(y_true, predictions, labels=LABELS, average="macro", zero_division=0)),
        "precision_by_class": {label: round_float(report[label]["precision"]) for label in LABELS},
        "recall_by_class": {label: round_float(report[label]["recall"]) for label in LABELS},
        "confusion_matrix": matrix_dict(matrix),
        "actual_distribution": dict(Counter(y_true)),
        "prediction_distribution": dict(Counter(predictions)),
        "trades_taken": int(trades.sum()),
        "coverage": round_float(safe_div(trades.sum(), len(predictions))),
        "trade_precision": precision_on_mask(y_true, predictions, trades),
        "buy_precision": precision_on_mask(y_true, predictions, buy_trades),
        "sell_precision": precision_on_mask(y_true, predictions, sell_trades),
        "avg_r": round_float(sum(trade_r) / len(trade_r)) if trade_r else None,
        "total_r": round_float(sum(trade_r)) if trade_r else None,
        "profit_factor": profit_factor(trade_r),
        "max_drawdown_r": round_float(max_drawdown(trade_r)),
    }


def realized_r(df: pd.DataFrame, predictions: pd.Series) -> list[float | None]:
    out = []
    for pred, buy_r, sell_r in zip(predictions, df["buy_R"], df["sell_R"], strict=False):
        if pred == "ENTER_BUY":
            out.append(as_float(buy_r))
        elif pred == "ENTER_SELL":
            out.append(as_float(sell_r))
        else:
            out.append(0.0)
    return out


def load_baltasar_v1_comparison() -> dict[str, Any]:
    pure = load_pure_metrics()
    if not pure:
        return {"available": False, "reason": "pure_directional_metrics_missing"}
    return {"available": True, **pure["comparisons"]["baltasar_v1_signal"]}


def load_pure_directional_comparison() -> dict[str, Any]:
    pure = load_pure_metrics()
    if not pure:
        return {"available": False, "reason": "pure_directional_metrics_missing"}
    selected = pure.get("selected_model")
    return {
        "available": True,
        "selected_model": selected,
        "test_thresholds": pure["models"][selected]["thresholds"]["test"] if selected else {},
        "validation_thresholds": pure["models"][selected]["thresholds"]["validation"] if selected else {},
    }


def load_pure_metrics() -> dict[str, Any] | None:
    if not PURE_DIRECTIONAL_METRICS.exists():
        return None
    return load_json(PURE_DIRECTIONAL_METRICS)


def feature_importances(pipeline: Pipeline, validation_df: pd.DataFrame, feature_columns: list[str]) -> list[dict[str, Any]]:
    sample = validation_df.sample(n=min(12000, len(validation_df)), random_state=808)
    result = permutation_importance(
        pipeline,
        sample[feature_columns],
        sample[TARGET],
        n_repeats=3,
        random_state=909,
        scoring="f1_macro",
        n_jobs=1,
    )
    rows = [
        {"feature": feature, "importance": round_float(float(mean), 10), "method": "permutation_f1_macro"}
        for feature, mean in zip(feature_columns, result.importances_mean, strict=False)
    ]
    rows.sort(key=lambda row: row["importance"], reverse=True)
    return rows


def write_feature_importance(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["feature", "importance", "method"])
        writer.writeheader()
        writer.writerows(rows)


def markdown_summary(metrics: dict[str, Any], importances: list[dict[str, Any]]) -> str:
    lines = [
        "# Baltasar v2 Rich Features Model",
        "",
        "## Scope",
        "",
        f"- Model: `{metrics['model']['type']}`",
        f"- Target: `{TARGET}`",
        f"- Feature count: `{metrics['feature_count']}`",
        "- Experiment isolated; Baltasar v1 is not replaced.",
        "",
        "## Splits",
        "",
        table_from_rows(split_rows(metrics)),
        "",
        "## Validation Thresholds",
        "",
        threshold_table(metrics, "validation"),
        "",
        "## Test Thresholds",
        "",
        threshold_table(metrics, "test"),
        "",
        "## Comparisons",
        "",
        "### Baltasar v1 signal",
        "",
        comparison_table(metrics["comparisons"]["baltasar_v1_signal"]),
        "",
        "### Baltasar v2 pure directional",
        "",
        pure_table(metrics["comparisons"]["baltasar_v2_pure_directional"]),
        "",
        "## Top Feature Importance",
        "",
        table_from_rows(importances[:25]),
        "",
        "## Leakage Check",
        "",
        f"- Passed: `{metrics['leakage_check']['passed']}`",
        f"- Forbidden features in model: `{metrics['leakage_check']['forbidden_features_in_model']}`",
        "",
        "## Technical Decisions",
        "",
    ]
    lines.extend(f"- {item}" for item in metrics["technical_decisions"])
    return "\n".join(lines) + "\n"


def split_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "split": split,
            "rows": data["rows"],
            "DO_NOTHING": data["target_distribution"].get("DO_NOTHING", 0),
            "ENTER_BUY": data["target_distribution"].get("ENTER_BUY", 0),
            "ENTER_SELL": data["target_distribution"].get("ENTER_SELL", 0),
        }
        for split, data in metrics["splits"].items()
    ]


def threshold_table(metrics: dict[str, Any], split: str) -> str:
    rows = []
    for threshold, data in metrics["thresholds"][split].items():
        rows.append(
            {
                "threshold": threshold,
                "trades": data["trades_taken"],
                "coverage": data["coverage"],
                "trade_precision": data["trade_precision"],
                "avg_r": data["avg_r"],
                "total_r": data["total_r"],
                "PF": data["profit_factor"],
                "max_DD": data["max_drawdown_r"],
                "BUY_precision": data["buy_precision"],
                "SELL_precision": data["sell_precision"],
            }
        )
    return table_from_rows(rows)


def comparison_table(data: dict[str, Any]) -> str:
    if not data.get("available"):
        return table_from_rows([data])
    rows = []
    for split in ["validation", "test"]:
        row = data.get(split, {})
        rows.append(
            {
                "split": split,
                "trades": row.get("trades_taken"),
                "coverage": row.get("coverage"),
                "trade_precision": row.get("trade_precision"),
                "avg_r": row.get("avg_r"),
                "total_r": row.get("total_r"),
                "PF": row.get("profit_factor"),
                "max_DD": row.get("max_drawdown_r"),
            }
        )
    return table_from_rows(rows)


def pure_table(data: dict[str, Any]) -> str:
    if not data.get("available"):
        return table_from_rows([data])
    rows = []
    for split_key, label in [("validation_thresholds", "validation"), ("test_thresholds", "test")]:
        for threshold in ["0.40", "0.50"]:
            row = data[split_key].get(threshold, {})
            rows.append(
                {
                    "split": label,
                    "threshold": threshold,
                    "trades": row.get("trades_taken"),
                    "coverage": row.get("coverage"),
                    "avg_r": row.get("avg_r"),
                    "PF": row.get("profit_factor"),
                    "total_r": row.get("total_r"),
                }
            )
    return table_from_rows(rows)


def table_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(format_value(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def matrix_dict(matrix: Any) -> dict[str, dict[str, int]]:
    return {actual: {pred: int(matrix[i][j]) for j, pred in enumerate(LABELS)} for i, actual in enumerate(LABELS)}


def precision_on_mask(y_true: pd.Series, predictions: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if total == 0:
        return None
    return round_float((y_true[mask] == predictions[mask]).sum() / total)


def profit_factor(values: list[float | None]) -> float | None:
    wins = [value for value in values if value is not None and value > 0]
    losses = [value for value in values if value is not None and value < 0]
    gross_loss = abs(sum(losses))
    if gross_loss == 0:
        return None
    return round_float(sum(wins) / gross_loss)


def max_drawdown(values: list[float | None]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in values:
        if value is None:
            continue
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def round_float(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
