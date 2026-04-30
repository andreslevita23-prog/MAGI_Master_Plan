from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_INPUT = DEFAULT_RUN_DIR / "ceo_final_dataset.parquet"
DEFAULT_OUTPUT_DIR = DEFAULT_RUN_DIR / "baselines"

SPLITS = {
    "train": ("2020-01-15", "2023-12-31"),
    "validation": ("2024-01-01", "2024-12-31"),
    "test": ("2025-01-01", "2026-04-14"),
}

BASELINES = (
    "always_do_nothing",
    "baltasar_only",
    "gaspar_only",
    "baltasar_gaspar_aligned",
    "high_confidence_alignment",
)

ACTION_LABELS = ("ENTER_BUY", "ENTER_SELL", "DO_NOTHING")


def main() -> int:
    args = parse_args()
    setup_logging()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading final CEO dataset: %s", input_path)
    df = pd.read_parquet(input_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    logging.info("Rows loaded: %s", len(df))

    split_frames = make_splits(df)
    for split_name, split_df in split_frames.items():
        path = output_dir / f"{split_name}.parquet"
        split_df.to_parquet(path, index=False)
        logging.info("Wrote %s split: %s rows -> %s", split_name, len(split_df), path)

    metrics = build_metrics(split_frames)
    metrics_path = output_dir / "baseline_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    logging.info("Metrics written: %s", metrics_path)

    summary_path = output_dir / "baseline_summary.md"
    summary_path.write_text(markdown_summary(metrics), encoding="utf-8")
    logging.info("Summary written: %s", summary_path)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create temporal splits and no-ML CEO-MAGI baselines.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input ceo_final_dataset.parquet path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output baselines directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def make_splits(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    splits = {}
    for split_name, (start, end) in SPLITS.items():
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        mask = (df["timestamp"] >= start_ts) & (df["timestamp"] < end_ts)
        splits[split_name] = df.loc[mask].copy()
    return splits


def build_metrics(split_frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    split_metrics = {}
    for split_name, split_df in split_frames.items():
        split_metrics[split_name] = {
            "date_range": split_range(split_df),
            "rows": int(len(split_df)),
            "label_distribution": value_counts(split_df["ceo_label_h48"]),
            "year_distribution": value_counts(split_df["timestamp"].dt.year.astype("string")),
            "session_distribution": value_counts(split_df["session"]),
            "baselines": {
                baseline: baseline_metrics(split_df, baseline)
                for baseline in BASELINES
            },
        }
    return {
        "schema_version": "ceo_baseline_metrics_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input": str(DEFAULT_INPUT),
        "splits": {
            name: {"start": start, "end": end}
            for name, (start, end) in SPLITS.items()
        },
        "baseline_rules": baseline_rules(),
        "technical_decisions": technical_decisions(),
        "split_metrics": split_metrics,
    }


def baseline_metrics(df: pd.DataFrame, baseline: str) -> dict[str, Any]:
    predictions = predict(df, baseline)
    actual = df["ceo_label_h48"].map(normalize_label)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"

    trades_taken = int(trades.sum())
    correct_trades = int((predictions[trades] == actual[trades]).sum()) if trades_taken else 0

    return {
        "total_rows": int(len(df)),
        "trades_taken": trades_taken,
        "coverage": safe_div(trades_taken, len(df)),
        "label_precision_trades": safe_div(correct_trades, trades_taken),
        "precision_buy": precision_for(predictions, actual, buy_trades),
        "precision_sell": precision_for(predictions, actual, sell_trades),
        "prediction_distribution": value_counts(predictions),
        "comparison_against_ceo_label_h48": {
            "actual_label_distribution": value_counts(actual),
            "matches_all_rows": int((predictions == actual).sum()),
            "match_rate_all_rows": safe_div(int((predictions == actual).sum()), len(df)),
        },
        "confusion_matrix_simplified": confusion_matrix(predictions, actual),
        "trades_by_session": value_counts(df.loc[trades, "session"]),
        "trades_by_year": value_counts(df.loc[trades, "timestamp"].dt.year.astype("string")),
    }


def predict(df: pd.DataFrame, baseline: str) -> pd.Series:
    if baseline == "always_do_nothing":
        return pd.Series(["DO_NOTHING"] * len(df), index=df.index)

    baltasar = df["baltasar_signal"].map(normalize_direction)
    gaspar = df["gaspar_signal"].map(normalize_direction)
    alignment = df["baltasar_gaspar_alignment"].fillna("").astype(str).str.upper()
    baltasar_confidence = pd.to_numeric(df["baltasar_confidence"], errors="coerce").fillna(0.0)
    gaspar_confidence = pd.to_numeric(df["gaspar_confidence"], errors="coerce").fillna(0.0)

    prediction = pd.Series(["DO_NOTHING"] * len(df), index=df.index)

    if baseline == "baltasar_only":
        prediction.loc[baltasar == "BUY"] = "ENTER_BUY"
        prediction.loc[baltasar == "SELL"] = "ENTER_SELL"
        return prediction

    if baseline == "gaspar_only":
        prediction.loc[gaspar == "BUY"] = "ENTER_BUY"
        prediction.loc[gaspar == "SELL"] = "ENTER_SELL"
        return prediction

    if baseline == "baltasar_gaspar_aligned":
        aligned = alignment == "DIRECTION_MATCH"
        prediction.loc[aligned & (baltasar == "BUY")] = "ENTER_BUY"
        prediction.loc[aligned & (baltasar == "SELL")] = "ENTER_SELL"
        return prediction

    if baseline == "high_confidence_alignment":
        aligned = (
            (alignment == "DIRECTION_MATCH")
            & (baltasar_confidence >= 0.60)
            & (gaspar_confidence >= 0.60)
        )
        prediction.loc[aligned & (baltasar == "BUY")] = "ENTER_BUY"
        prediction.loc[aligned & (baltasar == "SELL")] = "ENTER_SELL"
        return prediction

    raise ValueError(f"Unsupported baseline: {baseline}")


def normalize_direction(value: Any) -> str:
    text = "" if value is None else str(value).strip().upper()
    if text in {"BUY", "LONG", "ENTER_BUY", "OPEN_LONG"}:
        return "BUY"
    if text in {"SELL", "SHORT", "ENTER_SELL", "OPEN_SHORT"}:
        return "SELL"
    if text in {"", "NONE", "NULL", "NAN", "HOLD", "NEUTRAL", "DO_NOTHING", "NO_TRADE", "SKIP_WARN"}:
        return "NONE"
    return "NONE"


def normalize_label(value: Any) -> str:
    direction = normalize_direction(value)
    if direction == "BUY":
        return "ENTER_BUY"
    if direction == "SELL":
        return "ENTER_SELL"
    return "DO_NOTHING"


def precision_for(predictions: pd.Series, actual: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if not total:
        return None
    return round(float((predictions[mask] == actual[mask]).sum()) / total, 6)


def confusion_matrix(predictions: pd.Series, actual: pd.Series) -> dict[str, dict[str, int]]:
    matrix = {predicted: {label: 0 for label in ACTION_LABELS} for predicted in ACTION_LABELS}
    for predicted, label in zip(predictions, actual, strict=False):
        predicted_label = normalize_label(predicted)
        actual_label = normalize_label(label)
        matrix[predicted_label][actual_label] += 1
    return matrix


def value_counts(series: pd.Series) -> dict[str, int]:
    counts = Counter("UNKNOWN" if pd.isna(value) else str(value) for value in series)
    return dict(sorted(counts.items()))


def safe_div(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 6)


def split_range(df: pd.DataFrame) -> dict[str, str | None]:
    if df.empty:
        return {"start": None, "end": None}
    return {
        "start": df["timestamp"].min().isoformat().replace("+00:00", "Z"),
        "end": df["timestamp"].max().isoformat().replace("+00:00", "Z"),
    }


def baseline_rules() -> dict[str, str]:
    return {
        "always_do_nothing": "Always predicts DO_NOTHING.",
        "baltasar_only": "ENTER_BUY/ENTER_SELL from normalized baltasar_signal when it is directional.",
        "gaspar_only": "ENTER_BUY/ENTER_SELL from normalized gaspar_signal when it is directional; current dataset uses GOOD/FAIR/POOR so this normally takes zero trades.",
        "baltasar_gaspar_aligned": "Trades Baltasar direction only when baltasar_gaspar_alignment == DIRECTION_MATCH.",
        "high_confidence_alignment": "Same as aligned baseline, with baltasar_confidence >= 0.60 and gaspar_confidence >= 0.60.",
    }


def technical_decisions() -> list[str]:
    return [
        "Splits are inclusive by calendar date and implemented as [start, end + 1 day).",
        "Signal normalization accepts BUY/buy/ENTER_BUY and SELL/sell/ENTER_SELL as directional; HOLD/NEUTRAL/none become no direction.",
        "gaspar_signal in the current final dataset is quality (GOOD/FAIR/POOR), not direction, so gaspar_only correctly produces zero trades unless future datasets include directional Gaspar signals.",
        "Directional agreement for Gaspar is taken from baltasar_gaspar_alignment == DIRECTION_MATCH because the final dataset does not retain gaspar proposed_direction as a separate column.",
        "Metrics compare baseline decisions to ceo_label_h48; future_outcome_h* columns are not used to create predictions.",
    ]


def markdown_summary(metrics: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI Baselines",
        "",
        f"- generated_at: {metrics['generated_at']}",
        f"- input: `{metrics['input']}`",
        "",
        "## Splits",
        "| Split | Rows | Start | End | Labels |",
        "|---|---:|---|---|---|",
    ]
    for split_name, split in metrics["split_metrics"].items():
        lines.append(
            f"| {split_name} | {split['rows']} | {split['date_range']['start']} | "
            f"{split['date_range']['end']} | {json.dumps(split['label_distribution'], sort_keys=True)} |"
        )

    lines.extend(["", "## Baseline Metrics", "| Split | Baseline | Trades | Coverage | Precision trades | BUY precision | SELL precision |", "|---|---|---:|---:|---:|---:|---:|"])
    for split_name, split in metrics["split_metrics"].items():
        for baseline, row in split["baselines"].items():
            lines.append(
                f"| {split_name} | {baseline} | {row['trades_taken']} | {fmt_pct(row['coverage'])} | "
                f"{fmt_pct(row['label_precision_trades'])} | {fmt_pct(row['precision_buy'])} | {fmt_pct(row['precision_sell'])} |"
            )

    lines.extend(["", "## Technical Decisions"])
    lines.extend(f"- {item}" for item in metrics["technical_decisions"])
    return "\n".join(lines) + "\n"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
