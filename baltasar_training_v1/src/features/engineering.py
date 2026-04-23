"""Feature preparation utilities."""

from __future__ import annotations

from typing import Tuple

import pandas as pd

from src.features.variants import apply_feature_variant


def normalize_dataframe(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Normalize dtypes that matter for training."""
    dataset_cfg = config["dataset"]
    timestamp_column = dataset_cfg["timestamp_column"]
    normalized = df.copy()

    if timestamp_column in normalized.columns:
        normalized[timestamp_column] = pd.to_datetime(
            normalized[timestamp_column], utc=True, errors="coerce"
        )

    for column in dataset_cfg.get("boolean_columns", []):
        if column in normalized.columns:
            normalized[column] = (
                normalized[column]
                .astype(str)
                .str.lower()
                .map({"true": True, "false": False})
            )

    return normalized


def build_feature_frame(df: pd.DataFrame, config: dict) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Split the labelled dataset into X, y and timestamps."""
    dataset_cfg = config["dataset"]
    derived_cfg = dataset_cfg["derived_target"]
    target_column = dataset_cfg.get("target_column") or derived_cfg["label_name"]
    timestamp_column = dataset_cfg["timestamp_column"]
    variant_df = apply_feature_variant(df, config)

    excluded = set(dataset_cfg.get("feature_drop_columns", []))
    excluded.update({target_column})
    excluded.update({"forward_return", "future_price"})

    feature_columns = [column for column in variant_df.columns if column not in excluded]
    X = variant_df[feature_columns].copy()
    y = variant_df[target_column].copy()
    timestamps = variant_df[timestamp_column].copy()
    return X, y, timestamps
