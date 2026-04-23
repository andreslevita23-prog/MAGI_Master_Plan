"""Target creation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def prepare_target(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Return a dataset with the configured target column ready."""
    dataset_cfg = config["dataset"]
    target_column = dataset_cfg.get("target_column")

    if target_column and target_column in df.columns:
        return df.copy()

    derived_cfg = dataset_cfg["derived_target"]
    if not derived_cfg.get("enabled", False):
        raise ValueError("No target column found and derived target creation is disabled.")

    return build_derived_direction_target(df, config)


def build_derived_direction_target(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Create BUY/SELL/NEUTRAL labels from forward returns."""
    dataset_cfg = config["dataset"]
    derived_cfg = dataset_cfg["derived_target"]
    timestamp_column = dataset_cfg["timestamp_column"]
    price_column = derived_cfg["price_column"]
    label_name = derived_cfg["label_name"]
    horizon_steps = int(derived_cfg["horizon_steps"])
    buy_threshold = float(derived_cfg["buy_threshold"])
    sell_threshold = float(derived_cfg["sell_threshold"])

    labelled = df.copy()
    labelled[timestamp_column] = pd.to_datetime(labelled[timestamp_column], utc=True, errors="coerce")
    labelled = labelled.sort_values(timestamp_column).reset_index(drop=True)

    future_price = labelled[price_column].shift(-horizon_steps)
    labelled["forward_return"] = (future_price - labelled[price_column]) / labelled[price_column]
    labelled["future_price"] = future_price

    conditions = [
        labelled["forward_return"] >= buy_threshold,
        labelled["forward_return"] <= sell_threshold,
    ]
    choices = ["BUY", "SELL"]
    labelled[label_name] = np.select(conditions, choices, default="NEUTRAL")

    labelled = labelled.dropna(subset=["forward_return"]).reset_index(drop=True)
    return labelled
