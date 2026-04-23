"""Feature-set variants for Baltasar experiments."""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_feature_variant(df: pd.DataFrame, config: dict, variant_name: str | None = None) -> pd.DataFrame:
    """Return the requested feature variant without altering target semantics."""
    dataset_cfg = config["dataset"]
    variant = variant_name or dataset_cfg.get("feature_variant", "current")

    if variant == "current":
        return df.copy()
    if variant == "compact":
        return build_compact_feature_set(df)

    raise ValueError(f"Unknown feature variant: {variant}")


def build_compact_feature_set(df: pd.DataFrame) -> pd.DataFrame:
    """Build a smaller, more expressive feature set from snapshot features."""
    compact = df.copy()
    price_ref = compact["current_price"].replace(0, np.nan)

    compact["candle_body_ratio"] = (compact["anchor_close"] - compact["anchor_open"]) / price_ref
    compact["candle_range_ratio"] = (compact["anchor_high"] - compact["anchor_low"]) / price_ref
    compact["upper_wick_ratio"] = (compact["anchor_high"] - compact[["anchor_open", "anchor_close"]].max(axis=1)) / price_ref
    compact["lower_wick_ratio"] = (compact[["anchor_open", "anchor_close"]].min(axis=1) - compact["anchor_low"]) / price_ref
    compact["price_vs_ema20"] = (compact["current_price"] - compact["ema_20"]) / price_ref
    compact["price_vs_ema50"] = (compact["current_price"] - compact["ema_50"]) / price_ref
    compact["price_vs_ema200"] = (compact["current_price"] - compact["ema_200"]) / price_ref
    compact["ema_gap_20_50"] = (compact["ema_20"] - compact["ema_50"]) / price_ref
    compact["ema_gap_50_200"] = (compact["ema_50"] - compact["ema_200"]) / price_ref
    compact["ema_gap_20_200"] = (compact["ema_20"] - compact["ema_200"]) / price_ref
    compact["normalized_recent_range"] = compact["recent_range"] / price_ref

    keep_columns = [
        "market_structure",
        "structure_direction",
        "momentum",
        "rsi_14",
        "has_open_position",
        "candle_body_ratio",
        "candle_range_ratio",
        "upper_wick_ratio",
        "lower_wick_ratio",
        "price_vs_ema20",
        "price_vs_ema50",
        "price_vs_ema200",
        "ema_gap_20_50",
        "ema_gap_50_200",
        "ema_gap_20_200",
        "normalized_recent_range",
    ]

    passthrough_columns = [
        column
        for column in compact.columns
        if column not in {
            "anchor_open",
            "anchor_high",
            "anchor_low",
            "anchor_close",
            "current_price",
            "ema_20",
            "ema_50",
            "ema_200",
            "recent_range",
            "open_positions_count",
            "position_type",
            "entry_price",
            "sl",
            "tp",
            "floating_pnl",
            "validation_is_valid",
        }
    ]

    selected = [column for column in passthrough_columns if column not in keep_columns] + keep_columns
    selected = [column for column in selected if column in compact.columns]
    return compact[selected].copy()
