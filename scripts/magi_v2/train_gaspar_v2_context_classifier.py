from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_DATASET = Path("data/output/magi_v2/gaspar_v2_dataset/gaspar_v2_dataset.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/gaspar_v2_context_classifier")
DEFAULT_DOC = Path("docs/gaspar_v2_context_classifier.md")

TARGET = "context_quality_rr2"
LABELS = ["FAVORABLE", "NEUTRAL", "UNFAVORABLE"]
TRAIN_START = pd.Timestamp("2020-01-01 00:00:00", tz="UTC")
TRAIN_END = pd.Timestamp("2023-12-31 23:59:59", tz="UTC")
VALIDATION_START = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
VALIDATION_END = pd.Timestamp("2024-12-31 23:59:59", tz="UTC")
TEST_START = pd.Timestamp("2025-01-01 00:00:00", tz="UTC")
TEST_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")

DIAGNOSTIC_COLUMNS = {
    "timestamp",
    "symbol",
    "split",
    "year",
    "quarter",
    "month",
    "prediction",
    "realized_R",
    "abs_realized_R",
    "policy_threshold",
    "selected_at_050",
    "tradeable_direction_rr2_first_touch",
    "buy_R",
    "sell_R",
    "buy_first_touch",
    "sell_first_touch",
    "same_bar_ambiguous_flag",
    "session",
    "hour",
    "weekday",
    "rich_feature_match",
    "trade_key",
}

FORBIDDEN_FEATURES = DIAGNOSTIC_COLUMNS | {
    TARGET,
    "future_outcome_h12",
    "future_outcome_h48",
    "future_outcome_h96",
    "future_outcome_h288",
}


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.dataset)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    feature_columns = infer_feature_columns(df)
    train, validation, test = split_dataset(df)

    train.to_parquet(output_dir / "train.parquet", index=False)
    validation.to_parquet(output_dir / "validation.parquet", index=False)
    test.to_parquet(output_dir / "test.parquet", index=False)

    diagnostics = {
        "schema_version": "gaspar_v2_context_classifier_v0.1",
        "generated_at": utc_now(),
        "dataset": str(args.dataset),
        "output_dir": str(output_dir),
        "status": "blocked_no_train_rows" if train.empty else "ready_to_train",
        "target": TARGET,
        "labels": LABELS,
        "feature_columns": feature_columns,
        "feature_column_count": len(feature_columns),
        "forbidden_feature_intersection": sorted(set(feature_columns) & FORBIDDEN_FEATURES),
        "rows": int(len(df)),
        "temporal_range": {
            "min": df["timestamp"].min().isoformat() if not df.empty else None,
            "max": df["timestamp"].max().isoformat() if not df.empty else None,
        },
        "split_rows": {
            "train": int(len(train)),
            "validation": int(len(validation)),
            "test": int(len(test)),
        },
        "label_distribution": value_counts(df[TARGET]) if TARGET in df else {},
        "label_distribution_by_split": {
            "train": value_counts(train[TARGET]) if TARGET in train else {},
            "validation": value_counts(validation[TARGET]) if TARGET in validation else {},
            "test": value_counts(test[TARGET]) if TARGET in test else {},
        },
        "technical_decision": (
            "Training was blocked because the provided Gaspar v2 dataset starts in 2024 and contains no rows "
            "for the required 2020-2023 train window. Training on 2024 or test rows would violate the requested "
            "temporal contract and risk leakage."
        ),
        "next_required_action": (
            "Build Gaspar v2 training rows for 2020-2023 by applying the existing Baltasar v2 rich_policy_medium "
            "selection logic to the train-period rich feature dataset, then label those trades with RR 1:2 first-touch R."
        ),
    }

    if train.empty:
        (output_dir / "gaspar_v2_context_metrics.json").write_text(
            json.dumps(diagnostics, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        summary = blocked_summary(diagnostics)
        (output_dir / "gaspar_v2_context_summary.md").write_text(summary, encoding="utf-8")
        Path(args.doc).write_text(summary, encoding="utf-8")
        print("BLOCKED: no rows in required train window 2020-2023.")
        print(f"train={len(train)} validation={len(validation)} test={len(test)}")
        print(f"wrote diagnostics to {output_dir}")
        return 2

    raise NotImplementedError(
        "Training path is intentionally disabled until a non-empty 2020-2023 train split exists."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Gaspar v2 context classifier with strict temporal split.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def infer_feature_columns(df: pd.DataFrame) -> list[str]:
    columns = []
    for column in df.columns:
        if column in FORBIDDEN_FEATURES:
            continue
        if column.endswith("_R") or "future" in column.lower() or "outcome" in column.lower():
            continue
        columns.append(column)
    return columns


def split_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = df[df["timestamp"].between(TRAIN_START, TRAIN_END)].copy()
    validation = df[df["timestamp"].between(VALIDATION_START, VALIDATION_END)].copy()
    test = df[df["timestamp"].between(TEST_START, TEST_END)].copy()
    return train, validation, test


def value_counts(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.fillna("NULL").value_counts(dropna=False).to_dict().items()}


def blocked_summary(metrics: dict[str, Any]) -> str:
    split_rows = metrics["split_rows"]
    lines = [
        "# Gaspar v2 context classifier",
        "",
        "## Status",
        "",
        "`BLOCKED`: no model was trained.",
        "",
        "The provided dataset does not contain any rows in the required train window `2020-2023`.",
        "Training on 2024 validation rows or 2025-2026 test rows would break the temporal contract and contaminate evaluation.",
        "",
        "## Split audit",
        "",
        "| Split | Rows |",
        "| --- | ---: |",
        f"| Train 2020-2023 | {split_rows['train']:,} |",
        f"| Validation 2024 | {split_rows['validation']:,} |",
        f"| Test 2025-2026 | {split_rows['test']:,} |",
        "",
        "## Label distribution",
        "",
        "| Label | Rows |",
        "| --- | ---: |",
    ]
    for label, count in metrics["label_distribution"].items():
        lines.append(f"| {label} | {count:,} |")
    lines.extend(
        [
            "",
            "## Leakage check",
            "",
            f"- Feature columns inferred: `{metrics['feature_column_count']}`.",
            f"- Forbidden feature intersection: `{metrics['forbidden_feature_intersection']}`.",
            "- Diagnostic/result columns such as `realized_R`, `buy_R`, `sell_R`, `selected_at_050`, policy decisions, and target are excluded from features.",
            "",
            "## Required next action",
            "",
            "Generate Gaspar v2 train-period examples for `2020-2023` before training. The clean path is:",
            "",
            "1. Apply the already-trained Baltasar v2 rich model to `baltasar_v2_rich_features.parquet` rows from 2020-2023.",
            "2. Apply the existing `rich_policy_medium` selection rules at threshold `0.40`.",
            "3. Label selected train trades with the same RR 1:2 first-touch R logic.",
            "4. Rebuild `gaspar_v2_dataset.parquet` with train, validation, and test rows.",
            "5. Train Gaspar v2 only after `train.parquet` is non-empty.",
            "",
            "## Intended model once unblocked",
            "",
            "- Primary model: `HistGradientBoostingClassifier`.",
            "- Target: `context_quality_rr2`.",
            "- Operational use: block when `P(UNFAVORABLE)` exceeds `0.50`, `0.60`, or `0.70`, then compare filtered R/PF/DD against Baltasar v2 medium `0.40`.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
