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
DEFAULT_BASELINES_DIR = RUN_DIR / "baselines"
DEFAULT_MODELS_DIR = RUN_DIR / "models"

TRAIN_PATH = DEFAULT_BASELINES_DIR / "train.parquet"
VALIDATION_PATH = DEFAULT_BASELINES_DIR / "validation.parquet"
TEST_PATH = DEFAULT_BASELINES_DIR / "test.parquet"
BASELINE_METRICS_PATH = DEFAULT_BASELINES_DIR / "baseline_metrics.json"

MODEL_OUTPUT = DEFAULT_MODELS_DIR / "ceo_baseline_model.joblib"
METRICS_OUTPUT = DEFAULT_MODELS_DIR / "ceo_baseline_metrics.json"
SUMMARY_OUTPUT = DEFAULT_MODELS_DIR / "ceo_baseline_summary.md"
FEATURE_IMPORTANCE_OUTPUT = DEFAULT_MODELS_DIR / "ceo_feature_importance.csv"

TARGET = "ceo_label_h48"
LABELS = ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"]

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
    "ceo_label_h48",
}


def main() -> int:
    args = parse_args()
    setup_logging()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    verify_no_leakage()
    train_df = read_split(Path(args.train))
    validation_df = read_split(Path(args.validation))
    test_df = read_split(Path(args.test))

    logging.info("Train rows: %s", len(train_df))
    logging.info("Validation rows: %s", len(validation_df))
    logging.info("Test rows: %s", len(test_df))

    pipeline = build_pipeline()
    logging.info("Training RandomForestClassifier baseline")
    pipeline.fit(train_df[FEATURES], train_df[TARGET])

    model_payload = {
        "schema_version": "ceo_baseline_model_v0.1",
        "trained_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model_type": "RandomForestClassifier",
        "features": FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "target": TARGET,
        "pipeline": pipeline,
    }
    joblib.dump(model_payload, output_dir / MODEL_OUTPUT.name)
    logging.info("Model written: %s", output_dir / MODEL_OUTPUT.name)

    baseline_metrics = load_baseline_metrics(Path(args.baseline_metrics))
    metrics = build_metrics(pipeline, train_df, validation_df, test_df, baseline_metrics)
    (output_dir / METRICS_OUTPUT.name).write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    logging.info("Metrics written: %s", output_dir / METRICS_OUTPUT.name)

    importances = feature_importances(pipeline)
    write_feature_importance(output_dir / FEATURE_IMPORTANCE_OUTPUT.name, importances)
    logging.info("Feature importance written: %s", output_dir / FEATURE_IMPORTANCE_OUTPUT.name)

    (output_dir / SUMMARY_OUTPUT.name).write_text(markdown_summary(metrics, importances), encoding="utf-8")
    logging.info("Summary written: %s", output_dir / SUMMARY_OUTPUT.name)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train first CEO-MAGI ML baseline model.")
    parser.add_argument("--train", default=str(TRAIN_PATH), help="Train split parquet path.")
    parser.add_argument("--validation", default=str(VALIDATION_PATH), help="Validation split parquet path.")
    parser.add_argument("--test", default=str(TEST_PATH), help="Test split parquet path.")
    parser.add_argument("--baseline-metrics", default=str(BASELINE_METRICS_PATH), help="No-ML baseline metrics JSON path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_MODELS_DIR), help="Output model directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def verify_no_leakage() -> None:
    forbidden = sorted(set(FEATURES) & FORBIDDEN_FEATURES)
    if forbidden:
        raise ValueError(f"Forbidden future/target columns in feature list: {forbidden}")


def read_split(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing split parquet: {path}")
    df = pd.read_parquet(path)
    missing = [column for column in [*FEATURES, TARGET] if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")
    return df


def build_pipeline() -> Pipeline:
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )
    model = RandomForestClassifier(
        n_estimators=120,
        max_depth=12,
        min_samples_leaf=100,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=1,
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def build_metrics(
    pipeline: Pipeline,
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
    baseline_metrics: dict[str, Any],
) -> dict[str, Any]:
    split_frames = {
        "train": train_df,
        "validation": validation_df,
        "test": test_df,
    }
    split_metrics = {
        split_name: evaluate_split(pipeline, split_df)
        for split_name, split_df in split_frames.items()
    }
    comparisons = {
        split_name: compare_to_baltasar_only(split_name, split_metrics[split_name], baseline_metrics)
        for split_name in ("validation", "test")
    }
    return {
        "schema_version": "ceo_baseline_model_metrics_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model": {
            "type": "RandomForestClassifier",
            "params": {
                "n_estimators": 120,
                "max_depth": 12,
                "min_samples_leaf": 100,
                "class_weight": "balanced_subsample",
                "random_state": 42,
                "n_jobs": 1,
            },
        },
        "features": FEATURES,
        "forbidden_features_checked": sorted(FORBIDDEN_FEATURES),
        "leakage_check": {
            "passed": True,
            "forbidden_features_in_model": [],
        },
        "split_metrics": split_metrics,
        "comparison_against_baltasar_only": comparisons,
        "technical_decisions": [
            "Only approved non-future columns are used as model features.",
            "Categorical columns use SimpleImputer plus OneHotEncoder(handle_unknown='ignore').",
            "Numeric columns use median imputation fit only on train through the sklearn pipeline.",
            "RandomForestClassifier uses limited depth and large min_samples_leaf for a conservative first baseline.",
            "n_jobs=1 is used because parallel joblib workers are blocked in the local Windows sandbox.",
            "class_weight='balanced_subsample' is used to reduce collapse into DO_NOTHING under class imbalance.",
            "No hyperparameter search or neural network model is used.",
        ],
    }


def evaluate_split(pipeline: Pipeline, df: pd.DataFrame) -> dict[str, Any]:
    y_true = df[TARGET].astype(str)
    y_pred = pd.Series(pipeline.predict(df[FEATURES]), index=df.index, name="prediction")
    report = classification_report(y_true, y_pred, labels=LABELS, output_dict=True, zero_division=0)
    trades = y_pred.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = y_pred == "ENTER_BUY"
    sell_trades = y_pred == "ENTER_SELL"
    trades_taken = int(trades.sum())
    correct_trades = int((y_pred[trades] == y_true[trades]).sum()) if trades_taken else 0
    return {
        "rows": int(len(df)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)), 6),
        "precision_by_class": {
            label: round(float(report[label]["precision"]), 6)
            for label in LABELS
        },
        "recall_by_class": {
            label: round(float(report[label]["recall"]), 6)
            for label in LABELS
        },
        "confusion_matrix": matrix_dict(y_true, y_pred),
        "trades_taken": trades_taken,
        "coverage": safe_div(trades_taken, len(df)),
        "trade_precision": safe_div(correct_trades, trades_taken),
        "buy_precision": precision_for(y_pred, y_true, buy_trades),
        "sell_precision": precision_for(y_pred, y_true, sell_trades),
        "prediction_distribution": value_counts(y_pred),
        "actual_distribution": value_counts(y_true),
    }


def matrix_dict(y_true: pd.Series, y_pred: pd.Series) -> dict[str, dict[str, int]]:
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)
    return {
        actual: {
            predicted: int(matrix[row_index][col_index])
            for col_index, predicted in enumerate(LABELS)
        }
        for row_index, actual in enumerate(LABELS)
    }


def precision_for(predictions: pd.Series, actual: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if not total:
        return None
    return round(float((predictions[mask] == actual[mask]).sum()) / total, 6)


def compare_to_baltasar_only(split_name: str, model_metrics: dict[str, Any], baseline_metrics: dict[str, Any]) -> dict[str, Any]:
    baseline = (
        baseline_metrics
        .get("split_metrics", {})
        .get(split_name, {})
        .get("baselines", {})
        .get("baltasar_only", {})
    )
    baseline_trade_precision = baseline.get("label_precision_trades")
    baseline_coverage = baseline.get("coverage")
    return {
        "baseline_trade_precision": baseline_trade_precision,
        "model_trade_precision": model_metrics.get("trade_precision"),
        "trade_precision_delta": delta(model_metrics.get("trade_precision"), baseline_trade_precision),
        "baseline_coverage": baseline_coverage,
        "model_coverage": model_metrics.get("coverage"),
        "coverage_delta": delta(model_metrics.get("coverage"), baseline_coverage),
        "baseline_trades_taken": baseline.get("trades_taken"),
        "model_trades_taken": model_metrics.get("trades_taken"),
    }


def delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 6)


def load_baseline_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        logging.warning("No baseline metrics found at %s; comparison will be empty", path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def feature_importances(pipeline: Pipeline) -> list[dict[str, Any]]:
    preprocess = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]
    names = preprocess.get_feature_names_out()
    rows = [
        {"feature": str(name), "importance": round(float(importance), 10)}
        for name, importance in zip(names, model.feature_importances_, strict=False)
    ]
    rows.sort(key=lambda item: item["importance"], reverse=True)
    return rows


def write_feature_importance(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["feature", "importance"])
        writer.writeheader()
        writer.writerows(rows)


def value_counts(series: pd.Series) -> dict[str, int]:
    counts = Counter("UNKNOWN" if pd.isna(value) else str(value) for value in series)
    return dict(sorted(counts.items()))


def safe_div(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 6)


def markdown_summary(metrics: dict[str, Any], importances: list[dict[str, Any]]) -> str:
    lines = [
        "# CEO-MAGI Baseline Model",
        "",
        f"- generated_at: {metrics['generated_at']}",
        "- model: RandomForestClassifier",
        f"- features: {len(metrics['features'])}",
        f"- leakage_check_passed: {metrics['leakage_check']['passed']}",
        "",
        "## Metrics",
        "| Split | Accuracy | Macro F1 | Trades | Coverage | Trade precision | BUY precision | SELL precision |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split_name in ("train", "validation", "test"):
        row = metrics["split_metrics"][split_name]
        lines.append(
            f"| {split_name} | {fmt_pct(row['accuracy'])} | {fmt_pct(row['macro_f1'])} | "
            f"{row['trades_taken']} | {fmt_pct(row['coverage'])} | {fmt_pct(row['trade_precision'])} | "
            f"{fmt_pct(row['buy_precision'])} | {fmt_pct(row['sell_precision'])} |"
        )

    lines.extend(["", "## Prediction Distribution", "| Split | Distribution |", "|---|---|"])
    for split_name in ("train", "validation", "test"):
        lines.append(f"| {split_name} | {json.dumps(metrics['split_metrics'][split_name]['prediction_distribution'], sort_keys=True)} |")

    lines.extend(["", "## Comparison Against baltasar_only", "| Split | Model trade precision | Baseline trade precision | Delta | Model coverage | Baseline coverage | Delta |", "|---|---:|---:|---:|---:|---:|---:|"])
    for split_name in ("validation", "test"):
        row = metrics["comparison_against_baltasar_only"][split_name]
        lines.append(
            f"| {split_name} | {fmt_pct(row['model_trade_precision'])} | {fmt_pct(row['baseline_trade_precision'])} | "
            f"{fmt_pct(row['trade_precision_delta'])} | {fmt_pct(row['model_coverage'])} | "
            f"{fmt_pct(row['baseline_coverage'])} | {fmt_pct(row['coverage_delta'])} |"
        )

    lines.extend(["", "## Top Feature Importances", "| Rank | Feature | Importance |", "|---:|---|---:|"])
    for index, row in enumerate(importances[:20], 1):
        lines.append(f"| {index} | `{row['feature']}` | {row['importance']:.6f} |")

    lines.extend(["", "## Technical Decisions"])
    lines.extend(f"- {item}" for item in metrics["technical_decisions"])
    return "\n".join(lines) + "\n"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
