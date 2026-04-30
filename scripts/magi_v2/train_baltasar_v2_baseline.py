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


DEFAULT_INPUT = Path("data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_v2_baseline")

TARGET = "tradeable_direction_rr2_first_touch"
LABELS = ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"]
THRESHOLDS = [0.50, 0.60, 0.70, 0.80]

TRAIN_START = "2020-01-15"
TRAIN_END = "2023-12-31 23:59:59"
VALIDATION_START = "2024-01-01"
VALIDATION_END = "2024-12-31 23:59:59"
TEST_START = "2025-01-01"
TEST_END = "2026-04-14 23:59:59"

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
    "spread_pips",
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
    "spread_pips",
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
    "buy_outcome",
    "sell_outcome",
    "buy_R",
    "sell_R",
    "buy_first_touch",
    "sell_first_touch",
    "buy_bars_to_exit",
    "sell_bars_to_exit",
    TARGET,
    "same_bar_ambiguous_flag",
    "future_outcome_h12",
    "future_outcome_h48",
    "future_outcome_h96",
    "future_outcome_h288",
    "future_return",
    "future_return_pips",
    "max_favorable_excursion",
    "max_adverse_excursion",
}

EVAL_REQUIRED = ["buy_R", "sell_R", "timestamp", TARGET]


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    verify_no_leakage()

    df = read_dataset(Path(args.input))
    train_df, validation_df, test_df = split_temporally(df)
    train_df.to_parquet(output_dir / "train.parquet", index=False)
    validation_df.to_parquet(output_dir / "validation.parquet", index=False)
    test_df.to_parquet(output_dir / "test.parquet", index=False)
    logging.info("Split rows train=%s validation=%s test=%s", len(train_df), len(validation_df), len(test_df))

    pipeline = build_pipeline()
    logging.info("Training Baltasar v2 RandomForestClassifier baseline")
    pipeline.fit(train_df[FEATURES], train_df[TARGET])

    payload = {
        "schema_version": "baltasar_v2_baseline_model_v0.1",
        "trained_at": utc_now(),
        "model_type": "RandomForestClassifier",
        "target": TARGET,
        "features": FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "pipeline": pipeline,
    }
    joblib.dump(payload, output_dir / "baltasar_v2_baseline_model.joblib")

    metrics = build_metrics(pipeline, train_df, validation_df, test_df)
    (output_dir / "baltasar_v2_baseline_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    importances = feature_importances(pipeline)
    write_feature_importance(output_dir / "baltasar_v2_feature_importance.csv", importances)
    (output_dir / "baltasar_v2_baseline_summary.md").write_text(markdown_summary(metrics, importances), encoding="utf-8")
    logging.info("Outputs written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Baltasar v2 baseline with RR 1:2 first-touch M5 labels.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="RR2 first-touch labels parquet.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_no_leakage() -> None:
    forbidden = sorted(set(FEATURES) & FORBIDDEN_FEATURES)
    if forbidden:
        raise ValueError(f"Forbidden columns in FEATURES: {forbidden}")


def read_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    missing = [column for column in [*FEATURES, *EVAL_REQUIRED] if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df.sort_values("timestamp").reset_index(drop=True)


def split_temporally(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = between(df, TRAIN_START, TRAIN_END)
    validation = between(df, VALIDATION_START, VALIDATION_END)
    test = between(df, TEST_START, TEST_END)
    if min(len(train), len(validation), len(test)) <= 0:
        raise ValueError("One or more temporal splits are empty.")
    return train, validation, test


def between(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    return df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)].copy()


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
        n_estimators=180,
        max_depth=12,
        min_samples_leaf=90,
        class_weight="balanced_subsample",
        random_state=202,
        n_jobs=1,
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def build_metrics(pipeline: Pipeline, train_df: pd.DataFrame, validation_df: pd.DataFrame, test_df: pd.DataFrame) -> dict[str, Any]:
    frames = {"train": train_df, "validation": validation_df, "test": test_df}
    argmax = {name: evaluate_predictions(frame, pd.Series(pipeline.predict(frame[FEATURES]), index=frame.index)) for name, frame in frames.items()}
    threshold = {
        name: {f"{th:.2f}": evaluate_predictions(frame, threshold_predictions(pipeline, frame, th)) for th in THRESHOLDS}
        for name, frame in frames.items()
    }
    baseline = {name: evaluate_predictions(frame, baltasar_v1_predictions(frame)) for name, frame in frames.items()}
    return {
        "schema_version": "baltasar_v2_baseline_metrics_v0.1",
        "generated_at": utc_now(),
        "model": {
            "type": "RandomForestClassifier",
            "params": {
                "n_estimators": 180,
                "max_depth": 12,
                "min_samples_leaf": 90,
                "class_weight": "balanced_subsample",
                "random_state": 202,
                "n_jobs": 1,
            },
        },
        "target": TARGET,
        "features": FEATURES,
        "leakage_check": {"passed": True, "forbidden_features_in_model": []},
        "splits": {
            name: {
                "rows": len(frame),
                "start": frame["timestamp"].min().isoformat(),
                "end": frame["timestamp"].max().isoformat(),
                "target_distribution": dict(Counter(frame[TARGET])),
            }
            for name, frame in frames.items()
        },
        "metrics_argmax": argmax,
        "threshold_metrics": threshold,
        "comparisons": {"baltasar_v1_signal": baseline},
        "technical_decisions": [
            "buy_R and sell_R are used only for evaluation, never as model features.",
            "Threshold decisions execute only if ENTER_BUY or ENTER_SELL probability exceeds the threshold; otherwise DO_NOTHING.",
            "Baltasar v1 comparison maps baltasar_signal BUY/SELL to ENTER_BUY/ENTER_SELL and all other values to DO_NOTHING.",
            "n_jobs=1 avoids Windows sandbox/joblib worker permission issues.",
        ],
    }


def threshold_predictions(pipeline: Pipeline, df: pd.DataFrame, threshold: float) -> pd.Series:
    probabilities = pipeline.predict_proba(df[FEATURES])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    predictions: list[str] = []
    for row in probabilities:
        buy_prob = float(row[buy_idx])
        sell_prob = float(row[sell_idx])
        if buy_prob >= sell_prob and buy_prob >= threshold:
            predictions.append("ENTER_BUY")
        elif sell_prob > buy_prob and sell_prob >= threshold:
            predictions.append("ENTER_SELL")
        else:
            predictions.append("DO_NOTHING")
    return pd.Series(predictions, index=df.index)


def baltasar_v1_predictions(df: pd.DataFrame) -> pd.Series:
    signal = df["baltasar_signal"].fillna("").astype(str).str.upper()
    mapped = signal.map({"BUY": "ENTER_BUY", "SELL": "ENTER_SELL"})
    return mapped.fillna("DO_NOTHING")


def evaluate_predictions(df: pd.DataFrame, predictions: pd.Series) -> dict[str, Any]:
    y_true = df[TARGET].astype(str)
    predictions = predictions.astype(str)
    report = classification_report(y_true, predictions, labels=LABELS, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, predictions, labels=LABELS)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    r_values = realized_r(df, predictions)
    trade_r = [value for value, is_trade in zip(r_values, trades, strict=False) if is_trade and value is not None]
    return {
        "accuracy": round_float(accuracy_score(y_true, predictions)),
        "macro_f1": round_float(f1_score(y_true, predictions, labels=LABELS, average="macro", zero_division=0)),
        "precision_by_class": {label: round_float(report[label]["precision"]) for label in LABELS},
        "recall_by_class": {label: round_float(report[label]["recall"]) for label in LABELS},
        "confusion_matrix": matrix_dict(cm),
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
        "by_year": period_metrics(df, predictions, "year"),
        "by_month": period_metrics(df, predictions, "month"),
    }


def realized_r(df: pd.DataFrame, predictions: pd.Series) -> list[float | None]:
    values: list[float | None] = []
    for pred, buy_r, sell_r in zip(predictions, df["buy_R"], df["sell_R"], strict=False):
        if pred == "ENTER_BUY":
            values.append(as_float(buy_r))
        elif pred == "ENTER_SELL":
            values.append(as_float(sell_r))
        else:
            values.append(0.0)
    return values


def period_metrics(df: pd.DataFrame, predictions: pd.Series, period: str) -> list[dict[str, Any]]:
    temp = df[["timestamp", TARGET, "buy_R", "sell_R"]].copy()
    temp["prediction"] = predictions.values
    temp["period"] = temp["timestamp"].dt.year.astype(str) if period == "year" else temp["timestamp"].dt.strftime("%Y-%m")
    rows = []
    for name, group in temp.groupby("period", sort=True):
        rows.append(compact_operational_metrics(group, name))
    return rows


def compact_operational_metrics(df: pd.DataFrame, period: str) -> dict[str, Any]:
    predictions = df["prediction"].astype(str)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    r_values = realized_r(df, predictions)
    trade_r = [value for value, is_trade in zip(r_values, trades, strict=False) if is_trade and value is not None]
    return {
        "period": period,
        "rows": int(len(df)),
        "trades": int(trades.sum()),
        "coverage": round_float(safe_div(trades.sum(), len(df))),
        "trade_precision": precision_on_mask(df[TARGET].astype(str), predictions, trades),
        "avg_r": round_float(sum(trade_r) / len(trade_r)) if trade_r else None,
        "total_r": round_float(sum(trade_r)) if trade_r else None,
        "profit_factor": profit_factor(trade_r),
        "max_drawdown_r": round_float(max_drawdown(trade_r)),
    }


def precision_on_mask(y_true: pd.Series, predictions: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if total == 0:
        return None
    return round_float((y_true[mask] == predictions[mask]).sum() / total)


def matrix_dict(matrix: Any) -> dict[str, dict[str, int]]:
    return {actual: {pred: int(matrix[i][j]) for j, pred in enumerate(LABELS)} for i, actual in enumerate(LABELS)}


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


def feature_importances(pipeline: Pipeline) -> list[dict[str, Any]]:
    preprocess = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]
    names = list(preprocess.get_feature_names_out())
    rows = [
        {"feature": name, "importance": round_float(float(importance), 10)}
        for name, importance in zip(names, model.feature_importances_, strict=False)
    ]
    rows.sort(key=lambda row: row["importance"], reverse=True)
    return rows


def write_feature_importance(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["feature", "importance"])
        writer.writeheader()
        writer.writerows(rows)


def markdown_summary(metrics: dict[str, Any], importances: list[dict[str, Any]]) -> str:
    lines = [
        "# Baltasar v2 Baseline",
        "",
        "## Scope",
        "",
        f"- Target: `{TARGET}`.",
        "- Model: `RandomForestClassifier`.",
        "- This is an experimental baseline; Baltasar v1 is not replaced.",
        "",
        "## Splits",
        "",
        table_from_rows([
            {
                "split": split,
                "rows": data["rows"],
                "start": data["start"],
                "end": data["end"],
                "DO_NOTHING": data["target_distribution"].get("DO_NOTHING", 0),
                "ENTER_BUY": data["target_distribution"].get("ENTER_BUY", 0),
                "ENTER_SELL": data["target_distribution"].get("ENTER_SELL", 0),
            }
            for split, data in metrics["splits"].items()
        ]),
        "",
        "## Threshold Metrics",
        "",
        "### Validation",
        "",
        threshold_table(metrics, "validation"),
        "",
        "### Test",
        "",
        threshold_table(metrics, "test"),
        "",
        "## Baltasar v1 Signal Comparison",
        "",
        comparison_table(metrics),
        "",
        "## Top Feature Importance",
        "",
        table_from_rows(importances[:20]),
        "",
        "## Leakage Check",
        "",
        f"- Passed: `{metrics['leakage_check']['passed']}`",
        f"- Forbidden features in model: `{metrics['leakage_check']['forbidden_features_in_model']}`",
        "",
        "## Technical Notes",
        "",
    ]
    lines.extend(f"- {item}" for item in metrics["technical_decisions"])
    return "\n".join(lines) + "\n"


def threshold_table(metrics: dict[str, Any], split: str) -> str:
    rows = []
    for threshold, data in metrics["threshold_metrics"][split].items():
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


def comparison_table(metrics: dict[str, Any]) -> str:
    rows = []
    for split in ["validation", "test"]:
        data = metrics["comparisons"]["baltasar_v1_signal"][split]
        rows.append(
            {
                "split": split,
                "trades": data["trades_taken"],
                "coverage": data["coverage"],
                "trade_precision": data["trade_precision"],
                "avg_r": data["avg_r"],
                "total_r": data["total_r"],
                "PF": data["profit_factor"],
                "max_DD": data["max_drawdown_r"],
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


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


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


def safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def round_float(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


if __name__ == "__main__":
    raise SystemExit(main())
