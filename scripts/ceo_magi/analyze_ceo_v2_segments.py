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
DEFAULT_TEST = DEFAULT_V2_DIR / "test.parquet"
DEFAULT_MODEL = DEFAULT_V2_DIR / "ceo_v2_tradeable_model.joblib"
DEFAULT_OUTPUT_DIR = DEFAULT_V2_DIR / "segments"

TARGET = "ceo_label_h48_tradeable"
THRESHOLDS = [0.60, 0.70]
LOW_SAMPLE_TRADES = 100
SEGMENTS = {
    "session": "segment_by_session.csv",
    "hour": "segment_by_hour.csv",
    "weekday": "segment_by_weekday.csv",
    "regime": "segment_by_regime.csv",
    "gaspar_signal": "segment_by_gaspar_signal.csv",
    "melchor_signal": "segment_by_melchor_signal.csv",
    "baltasar_signal": "segment_by_baltasar_signal.csv",
    "daily_range_bucket": "segment_by_daily_range_bucket.csv",
    "atr_bucket": "segment_by_atr_bucket.csv",
}


def main() -> int:
    args = parse_args()
    setup_logging()

    test_path = Path(args.test)
    model_path = Path(args.model)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading test split: %s", test_path)
    df = pd.read_parquet(test_path)
    payload = joblib.load(model_path)
    pipeline = payload["pipeline"] if isinstance(payload, dict) else payload
    features = payload.get("features") if isinstance(payload, dict) else infer_features(df)

    df = add_predictions(df, pipeline, features)
    df["daily_range_bucket"] = df["daily_range_position"].map(bucket_daily_range)
    df["atr_bucket"] = df["atr"].map(bucket_atr)

    metrics = {
        "schema_version": "ceo_v2_segment_metrics_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "test_rows": int(len(df)),
        "thresholds": THRESHOLDS,
        "low_sample_trades_threshold": LOW_SAMPLE_TRADES,
        "segments": {},
        "best_segments": {},
        "worst_segments": {},
        "block_candidates": {},
    }

    all_rows: list[dict[str, Any]] = []
    for segment, filename in SEGMENTS.items():
        rows = analyze_segment(df, segment)
        metrics["segments"][segment] = rows
        metrics["best_segments"][segment] = best_segments(rows)
        metrics["worst_segments"][segment] = worst_segments(rows)
        metrics["block_candidates"][segment] = block_candidates(rows)
        write_rows(output_dir / filename, rows)
        all_rows.extend(rows)
        logging.info("Wrote %s rows for segment %s", len(rows), segment)

    metrics["global_best"] = best_segments(all_rows, limit=20)
    metrics["global_worst"] = worst_segments(all_rows, limit=20)
    metrics["global_block_candidates"] = block_candidates(all_rows, limit=20)

    (output_dir / "ceo_v2_segments_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "ceo_v2_segments_summary.md").write_text(markdown_summary(metrics), encoding="utf-8")
    logging.info("Segment analysis written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze CEO v2 tradeable model segments on test split.")
    parser.add_argument("--test", default=str(DEFAULT_TEST), help="CEO v2 test parquet path.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="CEO v2 model joblib path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output segment analysis directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def infer_features(df: pd.DataFrame) -> list[str]:
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


def add_predictions(df: pd.DataFrame, pipeline: Any, features: list[str]) -> pd.DataFrame:
    result = df.copy()
    probabilities = pipeline.predict_proba(result[features])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    for threshold in THRESHOLDS:
        result[f"prediction_t{threshold:.2f}"] = threshold_predictions(probabilities, buy_idx, sell_idx, threshold)
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


def analyze_segment(df: pd.DataFrame, segment: str) -> list[dict[str, Any]]:
    rows = []
    for value, group in df.groupby(segment, dropna=False):
        for threshold in THRESHOLDS:
            prediction_column = f"prediction_t{threshold:.2f}"
            row = metric_row(group, prediction_column)
            row.update({
                "segment": segment,
                "segment_value": "UNKNOWN" if pd.isna(value) else str(value),
                "threshold": f"{threshold:.2f}",
            })
            rows.append(row)
    rows.sort(key=lambda item: (item["threshold"], item["segment"], item["segment_value"]))
    return rows


def metric_row(df: pd.DataFrame, prediction_column: str) -> dict[str, Any]:
    predictions = df[prediction_column].astype(str)
    actual = df[TARGET].astype(str)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    trades_taken = int(trades.sum())
    correct = int((predictions[trades] == actual[trades]).sum()) if trades_taken else 0
    return {
        "rows": int(len(df)),
        "trades_taken": trades_taken,
        "coverage": safe_div(trades_taken, len(df)),
        "trade_precision": safe_div(correct, trades_taken),
        "buy_precision": precision_for(predictions, actual, buy_trades),
        "sell_precision": precision_for(predictions, actual, sell_trades),
        "prediction_do_nothing": int((predictions == "DO_NOTHING").sum()),
        "prediction_enter_buy": int((predictions == "ENTER_BUY").sum()),
        "prediction_enter_sell": int((predictions == "ENTER_SELL").sum()),
        "low_sample": trades_taken < LOW_SAMPLE_TRADES,
    }


def best_segments(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    eligible = [row for row in rows if not row["low_sample"] and row["trade_precision"] is not None]
    return sorted(eligible, key=lambda item: (item["trade_precision"], item["trades_taken"]), reverse=True)[:limit]


def worst_segments(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    eligible = [row for row in rows if not row["low_sample"] and row["trade_precision"] is not None]
    return sorted(eligible, key=lambda item: (item["trade_precision"], -item["trades_taken"]))[:limit]


def block_candidates(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    eligible = [
        row for row in rows
        if not row["low_sample"]
        and row["trade_precision"] is not None
        and row["trade_precision"] < 0.20
        and row["coverage"] is not None
        and row["coverage"] >= 0.05
    ]
    return sorted(eligible, key=lambda item: (item["trade_precision"], -item["trades_taken"]))[:limit]


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "segment",
        "segment_value",
        "threshold",
        "rows",
        "trades_taken",
        "coverage",
        "trade_precision",
        "buy_precision",
        "sell_precision",
        "prediction_do_nothing",
        "prediction_enter_buy",
        "prediction_enter_sell",
        "low_sample",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def bucket_atr(value: Any) -> str:
    number = as_float(value)
    if number is None:
        return "UNKNOWN"
    if number <= 0.50:
        return "<=0.50"
    if number <= 0.85:
        return "0.50-0.85"
    if number <= 1.20:
        return "0.85-1.20"
    if number <= 1.50:
        return "1.20-1.50"
    return ">1.50"


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def precision_for(predictions: pd.Series, actual: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if not total:
        return None
    return round(float((predictions[mask] == actual[mask]).sum()) / total, 6)


def safe_div(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 6)


def markdown_summary(metrics: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI v2 Segment Analysis",
        "",
        f"- generated_at: {metrics['generated_at']}",
        f"- test_rows: {metrics['test_rows']}",
        f"- thresholds: {metrics['thresholds']}",
        f"- low_sample_trades_threshold: {metrics['low_sample_trades_threshold']}",
        "",
        "## Global Best Segments",
        segment_table(metrics["global_best"]),
        "",
        "## Global Worst Segments",
        segment_table(metrics["global_worst"]),
        "",
        "## Block Candidates",
        segment_table(metrics["global_block_candidates"]),
        "",
        "## Best By Segment",
    ]
    for segment, rows in metrics["best_segments"].items():
        lines.extend(["", f"### {segment}", segment_table(rows[:5])])
    return "\n".join(lines) + "\n"


def segment_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No eligible segments._"
    lines = [
        "| Segment | Value | Threshold | Rows | Trades | Coverage | Trade precision | BUY precision | SELL precision | Low sample |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['segment']} | {row['segment_value']} | {row['threshold']} | {row['rows']} | "
            f"{row['trades_taken']} | {fmt_pct(row['coverage'])} | {fmt_pct(row['trade_precision'])} | "
            f"{fmt_pct(row['buy_precision'])} | {fmt_pct(row['sell_precision'])} | {row['low_sample']} |"
        )
    return "\n".join(lines)


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
