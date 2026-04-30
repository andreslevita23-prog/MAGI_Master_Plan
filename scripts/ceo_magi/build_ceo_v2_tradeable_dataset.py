from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ceo_magi.audit_ceo_labels import candidate_labels


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_FINAL_DATASET = RUN_DIR / "ceo_final_dataset.parquet"
DEFAULT_RAW_JSONL = RUN_DIR / "ceo_training_records.jsonl"
DEFAULT_OUTPUT_DIR = RUN_DIR / "ceo_v2_tradeable"

TARGET = "ceo_label_h48_tradeable"
SPLITS = {
    "train": ("2020-01-15", "2023-12-31"),
    "validation": ("2024-01-01", "2024-12-31"),
    "test": ("2025-01-01", "2026-04-14"),
}


def main() -> int:
    args = parse_args()
    setup_logging()

    final_dataset_path = Path(args.final_dataset)
    raw_jsonl_path = Path(args.raw_jsonl)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading CEO v1 final dataset: %s", final_dataset_path)
    df = pd.read_parquet(final_dataset_path)
    logging.info("Rows loaded: %s", len(df))

    logging.info("Building %s from raw H48 outcomes", TARGET)
    labels = build_tradeable_labels(df, raw_jsonl_path)
    df[TARGET] = labels
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    dataset_parquet = output_dir / "ceo_v2_tradeable_dataset.parquet"
    dataset_csv = output_dir / "ceo_v2_tradeable_dataset.csv"
    summary_json = output_dir / "ceo_v2_tradeable_summary.json"

    df.to_parquet(dataset_parquet, index=False)
    df.to_csv(dataset_csv, index=False, encoding="utf-8")
    logging.info("Dataset written: %s", dataset_parquet)
    logging.info("CSV written: %s", dataset_csv)

    split_frames = make_splits(df)
    for split_name, split_df in split_frames.items():
        split_path = output_dir / f"{split_name}.parquet"
        split_df.to_parquet(split_path, index=False)
        logging.info("Split %s rows=%s -> %s", split_name, len(split_df), split_path)

    summary = build_summary(df, split_frames)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    logging.info("Summary written: %s", summary_json)
    logging.info("Target distribution: %s", summary["target_distribution"])
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build CEO-MAGI v2 tradeable target dataset.")
    parser.add_argument("--final-dataset", default=str(DEFAULT_FINAL_DATASET), help="Input ceo_final_dataset.parquet path.")
    parser.add_argument("--raw-jsonl", default=str(DEFAULT_RAW_JSONL), help="Raw ceo_training_records.jsonl path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="CEO v2 output directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_tradeable_labels(df: pd.DataFrame, raw_jsonl_path: Path) -> list[str]:
    if not raw_jsonl_path.exists():
        raise FileNotFoundError(f"Missing raw JSONL: {raw_jsonl_path}")

    labels: list[str] = []
    with raw_jsonl_path.open("r", encoding="utf-8-sig") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            if index >= len(df):
                break
            record = json.loads(line)
            outcomes = record.get("future_outcomes") if isinstance(record.get("future_outcomes"), dict) else {}
            h48 = outcomes.get("48") if isinstance(outcomes.get("48"), dict) else {}
            label = candidate_labels(df.iloc[index], h48)[TARGET]
            labels.append(label)
            if len(labels) % 50000 == 0:
                logging.info("Labeled %s rows", len(labels))

    if len(labels) != len(df):
        raise ValueError(f"Label count mismatch: labels={len(labels)} rows={len(df)}")
    return labels


def make_splits(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    splits = {}
    for split_name, (start, end) in SPLITS.items():
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        splits[split_name] = df.loc[(df["timestamp"] >= start_ts) & (df["timestamp"] < end_ts)].copy()
    return splits


def build_summary(df: pd.DataFrame, split_frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    return {
        "schema_version": "ceo_v2_tradeable_dataset_summary_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "target": TARGET,
        "target_distribution": value_counts(df[TARGET]),
        "old_target_distribution": value_counts(df["ceo_label_h48"]) if "ceo_label_h48" in df.columns else {},
        "temporal_range": {
            "start": df["timestamp"].min().isoformat().replace("+00:00", "Z"),
            "end": df["timestamp"].max().isoformat().replace("+00:00", "Z"),
        },
        "splits": {
            name: {
                "rows": int(len(split_df)),
                "date_range": {
                    "start": split_df["timestamp"].min().isoformat().replace("+00:00", "Z") if not split_df.empty else None,
                    "end": split_df["timestamp"].max().isoformat().replace("+00:00", "Z") if not split_df.empty else None,
                },
                "target_distribution": value_counts(split_df[TARGET]),
            }
            for name, split_df in split_frames.items()
        },
        "target_rule": {
            "source": "scripts.ceo_magi.audit_ceo_labels.candidate_labels -> ceo_label_h48_tradeable",
            "summary": "Melchor APPROVE, Gaspar not POOR, tradeable session, spread <= 2, ATR <= 1.2, D1 range position 0.15-0.85, no Gaspar mismatch/rejection, spread-adjusted H48 directional movement >= 7 pips, MFE >= 8 pips, abs(MAE) <= 10 pips.",
        },
        "technical_decisions": [
            "The v1 final dataset is copied into a v2 artifact and augmented with ceo_label_h48_tradeable; the original dataset is not modified.",
            "Raw future_outcomes are read only to build the target; future fields are not added as model features.",
            "Temporal splits use the same calendar ranges as CEO v1.",
        ],
    }


def value_counts(series: pd.Series) -> dict[str, int]:
    return dict(sorted(Counter("UNKNOWN" if pd.isna(value) else str(value) for value in series).items()))


if __name__ == "__main__":
    raise SystemExit(main())
