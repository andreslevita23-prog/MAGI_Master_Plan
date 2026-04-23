"""Dataset validation utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class ValidationReport:
    rows: int
    columns: int
    missing_required_columns: list[str]
    duplicate_snapshot_ids: int
    invalid_validation_rows: int
    missing_ratio_top_10: dict[str, float]
    timestamp_min: str | None
    timestamp_max: str | None
    passed: bool
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def validate_dataset(df: pd.DataFrame, config: dict) -> ValidationReport:
    """Validate the incoming dataset without mutating business semantics."""
    dataset_cfg = config["dataset"]
    validation_cfg = config["validation"]
    timestamp_column = dataset_cfg["timestamp_column"]
    warnings: list[str] = []

    missing_required_columns = [
        column for column in dataset_cfg["required_columns"] if column not in df.columns
    ]
    duplicate_snapshot_ids = 0
    if validation_cfg.get("enforce_unique_snapshot_id", True) and "snapshot_id" in df.columns:
        duplicate_snapshot_ids = int(df["snapshot_id"].duplicated().sum())

    invalid_validation_rows = 0
    if "validation_is_valid" in df.columns:
        normalized = df["validation_is_valid"].astype(str).str.lower()
        invalid_validation_rows = int((normalized != "true").sum())

    missing_ratio = df.isna().mean().sort_values(ascending=False)
    missing_ratio_top_10 = {
        column: round(float(value), 4) for column, value in missing_ratio.head(10).items()
    }

    timestamp_min = None
    timestamp_max = None
    if timestamp_column in df.columns:
        timestamps = pd.to_datetime(df[timestamp_column], errors="coerce", utc=True)
        if timestamps.isna().all():
            warnings.append(f"Timestamp column {timestamp_column} could not be parsed.")
        else:
            timestamp_min = str(timestamps.min())
            timestamp_max = str(timestamps.max())

    if len(df) < validation_cfg["min_rows"]:
        warnings.append(f"Dataset has fewer than {validation_cfg['min_rows']} rows.")

    high_missing = missing_ratio[missing_ratio > validation_cfg["max_missing_ratio"]].index.tolist()
    if high_missing:
        warnings.append(
            "Columns above missing threshold: " + ", ".join(high_missing[:10])
        )

    passed = not missing_required_columns and duplicate_snapshot_ids == 0 and len(df) >= validation_cfg["min_rows"]

    return ValidationReport(
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        missing_required_columns=missing_required_columns,
        duplicate_snapshot_ids=duplicate_snapshot_ids,
        invalid_validation_rows=invalid_validation_rows,
        missing_ratio_top_10=missing_ratio_top_10,
        timestamp_min=timestamp_min,
        timestamp_max=timestamp_max,
        passed=passed,
        warnings=warnings,
    )
