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


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_V2_DIR = RUN_DIR / "ceo_v2_tradeable"
DEFAULT_VALIDATION = DEFAULT_V2_DIR / "validation.parquet"
DEFAULT_TEST = DEFAULT_V2_DIR / "test.parquet"
DEFAULT_MODEL = DEFAULT_V2_DIR / "ceo_v2_tradeable_model.joblib"
DEFAULT_OUTPUT_DIR = DEFAULT_V2_DIR / "policy"

TARGET = "ceo_label_h48_tradeable"
THRESHOLD = 0.70
ALLOWED_SESSIONS = {"london", "new_york", "overlap"}
POLICIES = {
    "threshold_070_pure": {"min_d1": None, "max_d1": None, "apply_context_filters": False},
    "conservative_core": {"min_d1": 0.15, "max_d1": 0.65, "apply_context_filters": True},
    "conservative_extended": {"min_d1": 0.15, "max_d1": 0.85, "apply_context_filters": True},
}


def main() -> int:
    args = parse_args()
    setup_logging()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = joblib.load(Path(args.model))
    pipeline = payload["pipeline"] if isinstance(payload, dict) else payload
    features = payload.get("features") if isinstance(payload, dict) else infer_features()

    validation = load_split(Path(args.validation))
    test = load_split(Path(args.test))

    validation_eval = add_policy_predictions(validation, pipeline, features)
    test_eval = add_policy_predictions(test, pipeline, features)

    write_policy_trades(output_dir / "policy_trades_validation.csv", validation_eval, "validation")
    write_policy_trades(output_dir / "policy_trades_test.csv", test_eval, "test")

    metrics = {
        "schema_version": "ceo_v2_policy_metrics_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "threshold": THRESHOLD,
        "policies": policy_descriptions(),
        "validation": evaluate_split(validation_eval),
        "test": evaluate_split(test_eval),
    }
    metrics["stability"] = stability(metrics["validation"], metrics["test"])
    (output_dir / "ceo_v2_policy_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "ceo_v2_policy_summary.md").write_text(markdown_summary(metrics), encoding="utf-8")
    logging.info("Policy audit written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate CEO v2 conservative policy variants.")
    parser.add_argument("--validation", default=str(DEFAULT_VALIDATION), help="Validation split parquet.")
    parser.add_argument("--test", default=str(DEFAULT_TEST), help="Test split parquet.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="CEO v2 model joblib.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output policy directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def infer_features() -> list[str]:
    return [
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


def load_split(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing split: {path}")
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["month"] = df["timestamp"].dt.strftime("%Y-%m")
    df["daily_range_bucket"] = df["daily_range_position"].map(bucket_daily_range)
    return df


def add_policy_predictions(df: pd.DataFrame, pipeline: Any, features: list[str]) -> pd.DataFrame:
    result = df.copy()
    probabilities = pipeline.predict_proba(result[features])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    base_predictions = threshold_predictions(probabilities, buy_idx, sell_idx, THRESHOLD)
    result["threshold_070_pure_prediction"] = base_predictions
    for policy_name, config in POLICIES.items():
        if policy_name == "threshold_070_pure":
            result[f"{policy_name}_prediction"] = base_predictions
            continue
        allowed = context_mask(result, config["min_d1"], config["max_d1"])
        result[f"{policy_name}_prediction"] = [
            prediction if allowed_flag else "DO_NOTHING"
            for prediction, allowed_flag in zip(base_predictions, allowed, strict=False)
        ]
    return result


def threshold_predictions(probabilities: Any, buy_idx: int, sell_idx: int, threshold: float) -> list[str]:
    predictions = []
    for row in probabilities:
        buy_prob = float(row[buy_idx])
        sell_prob = float(row[sell_idx])
        if buy_prob >= sell_prob and buy_prob >= threshold:
            predictions.append("ENTER_BUY")
        elif sell_prob > buy_prob and sell_prob >= threshold:
            predictions.append("ENTER_SELL")
        else:
            predictions.append("DO_NOTHING")
    return predictions


def context_mask(df: pd.DataFrame, min_d1: float, max_d1: float) -> pd.Series:
    session = df["session"].fillna("").astype(str).str.lower()
    melchor = df["melchor_signal"].fillna("").astype(str).str.upper()
    gaspar = df["gaspar_signal"].fillna("").astype(str).str.upper()
    baltasar = df["baltasar_signal"].fillna("").astype(str).str.upper()
    d1 = pd.to_numeric(df["daily_range_position"], errors="coerce")
    return (
        session.isin(ALLOWED_SESSIONS)
        & (melchor == "APPROVE")
        & (gaspar != "POOR")
        & baltasar.isin(["BUY", "SELL"])
        & (d1 >= min_d1)
        & (d1 <= max_d1)
    )


def evaluate_split(df: pd.DataFrame) -> dict[str, Any]:
    return {
        policy_name: {
            **evaluate_predictions(df, f"{policy_name}_prediction"),
            "by_session": grouped_metrics(df, f"{policy_name}_prediction", "session"),
            "by_daily_range_bucket": grouped_metrics(df, f"{policy_name}_prediction", "daily_range_bucket"),
            "by_month": grouped_metrics(df, f"{policy_name}_prediction", "month"),
        }
        for policy_name in POLICIES
    }


def evaluate_predictions(df: pd.DataFrame, prediction_column: str) -> dict[str, Any]:
    predictions = df[prediction_column].astype(str)
    actual = df[TARGET].astype(str)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    trades_taken = int(trades.sum())
    correct = int((predictions[trades] == actual[trades]).sum()) if trades_taken else 0
    return {
        "rows_evaluated": int(len(df)),
        "trades_taken": trades_taken,
        "coverage": safe_div(trades_taken, len(df)),
        "trade_precision": safe_div(correct, trades_taken),
        "buy_precision": precision_for(predictions, actual, buy_trades),
        "sell_precision": precision_for(predictions, actual, sell_trades),
        "prediction_distribution": value_counts(predictions),
        "target_distribution_selected_trades": value_counts(actual[trades]),
    }


def grouped_metrics(df: pd.DataFrame, prediction_column: str, group_column: str) -> list[dict[str, Any]]:
    rows = []
    for value, group in df.groupby(group_column, dropna=False):
        metrics = evaluate_predictions(group, prediction_column)
        rows.append({
            "segment": "UNKNOWN" if pd.isna(value) else str(value),
            "rows_evaluated": metrics["rows_evaluated"],
            "trades_taken": metrics["trades_taken"],
            "coverage": metrics["coverage"],
            "trade_precision": metrics["trade_precision"],
            "buy_precision": metrics["buy_precision"],
            "sell_precision": metrics["sell_precision"],
        })
    return sorted(rows, key=lambda item: item["segment"])


def write_policy_trades(path: Path, df: pd.DataFrame, split: str) -> None:
    columns = [
        "split",
        "policy",
        "timestamp",
        "session",
        "month",
        "daily_range_position",
        "daily_range_bucket",
        "baltasar_signal",
        "gaspar_signal",
        "melchor_signal",
        TARGET,
        "prediction",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for policy_name in POLICIES:
            prediction_column = f"{policy_name}_prediction"
            trades = df[df[prediction_column].isin(["ENTER_BUY", "ENTER_SELL"])]
            for _, row in trades.iterrows():
                writer.writerow({
                    "split": split,
                    "policy": policy_name,
                    "timestamp": row["timestamp"].isoformat().replace("+00:00", "Z") if pd.notna(row["timestamp"]) else "",
                    "session": row.get("session"),
                    "month": row.get("month"),
                    "daily_range_position": row.get("daily_range_position"),
                    "daily_range_bucket": row.get("daily_range_bucket"),
                    "baltasar_signal": row.get("baltasar_signal"),
                    "gaspar_signal": row.get("gaspar_signal"),
                    "melchor_signal": row.get("melchor_signal"),
                    TARGET: row.get(TARGET),
                    "prediction": row.get(prediction_column),
                })


def stability(validation: dict[str, Any], test: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for policy_name in POLICIES:
        v = validation[policy_name]
        t = test[policy_name]
        result[policy_name] = {
            "validation_trade_precision": v["trade_precision"],
            "test_trade_precision": t["trade_precision"],
            "trade_precision_delta_test_minus_validation": delta(t["trade_precision"], v["trade_precision"]),
            "validation_coverage": v["coverage"],
            "test_coverage": t["coverage"],
            "coverage_delta_test_minus_validation": delta(t["coverage"], v["coverage"]),
            "validation_trades": v["trades_taken"],
            "test_trades": t["trades_taken"],
        }
    return result


def policy_descriptions() -> dict[str, str]:
    return {
        "threshold_070_pure": "Model threshold 0.70 with no additional context filters.",
        "conservative_core": "Threshold 0.70, sessions london/new_york/overlap, D1 position 0.15-0.65, Melchor APPROVE, Gaspar not POOR, Baltasar directional.",
        "conservative_extended": "Threshold 0.70, sessions london/new_york/overlap, D1 position 0.15-0.85, Melchor APPROVE, Gaspar not POOR, Baltasar directional.",
    }


def bucket_daily_range(value: Any) -> str:
    number = as_float(value)
    if number is None:
        return "UNKNOWN"
    if number <= 0.15:
        return "<=0.15"
    if number <= 0.35:
        return "0.15-0.35"
    if number <= 0.65:
        return "0.35-0.65"
    if number <= 0.85:
        return "0.65-0.85"
    if number <= 1.0:
        return "0.85-1.0"
    return ">1.0"


def precision_for(predictions: pd.Series, actual: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if not total:
        return None
    return round(float((predictions[mask] == actual[mask]).sum()) / total, 6)


def value_counts(series: pd.Series) -> dict[str, int]:
    return dict(sorted(Counter("UNKNOWN" if pd.isna(value) else str(value) for value in series).items()))


def safe_div(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 6)


def delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 6)


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def markdown_summary(metrics: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI v2 Policy Audit",
        "",
        f"- generated_at: {metrics['generated_at']}",
        f"- threshold: {metrics['threshold']}",
        "",
        "## Policy Metrics",
        "| Split | Policy | Trades | Coverage | Trade precision | BUY precision | SELL precision |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for split in ("validation", "test"):
        for policy_name in POLICIES:
            row = metrics[split][policy_name]
            lines.append(
                f"| {split} | {policy_name} | {row['trades_taken']} | {fmt_pct(row['coverage'])} | "
                f"{fmt_pct(row['trade_precision'])} | {fmt_pct(row['buy_precision'])} | {fmt_pct(row['sell_precision'])} |"
            )

    lines.extend(["", "## Stability", "| Policy | Validation precision | Test precision | Delta | Validation coverage | Test coverage | Delta |", "|---|---:|---:|---:|---:|---:|---:|"])
    for policy_name, row in metrics["stability"].items():
        lines.append(
            f"| {policy_name} | {fmt_pct(row['validation_trade_precision'])} | {fmt_pct(row['test_trade_precision'])} | "
            f"{fmt_pct(row['trade_precision_delta_test_minus_validation'])} | {fmt_pct(row['validation_coverage'])} | "
            f"{fmt_pct(row['test_coverage'])} | {fmt_pct(row['coverage_delta_test_minus_validation'])} |"
        )

    lines.extend(["", "## Policy Descriptions"])
    lines.extend(f"- `{name}`: {description}" for name, description in metrics["policies"].items())
    return "\n".join(lines) + "\n"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
