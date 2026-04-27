from __future__ import annotations

import pandas as pd

FEATURE_COLUMNS = [
    "proposed_direction",
    "h4_structure",
    "d1_structure",
    "directional_alignment",
    "distance_to_d1_support",
    "distance_to_d1_resistance",
    "position_in_d1_range",
    "near_key_level",
    "active_session",
    "daily_atr_consumed_pct",
    "available_range_to_next_level",
    "h4_candle_pattern",
    "day_of_week",
    "d1_volatility_vs_20d_avg",
    "current_d1_range_vs_atr_capped",
]

CATEGORICAL_FEATURES = [
    "proposed_direction",
    "h4_structure",
    "d1_structure",
    "directional_alignment",
    "near_key_level",
    "active_session",
    "h4_candle_pattern",
    "day_of_week",
]

NUMERIC_FEATURES = [
    "distance_to_d1_support",
    "distance_to_d1_resistance",
    "position_in_d1_range",
    "daily_atr_consumed_pct",
    "available_range_to_next_level",
    "d1_volatility_vs_20d_avg",
    "current_d1_range_vs_atr_capped",
]


def build_feature_frame(data: pd.DataFrame) -> pd.DataFrame:
    features = data.copy()
    for column in FEATURE_COLUMNS:
        if column not in features.columns:
            features[column] = pd.NA

    if "current_d1_range_vs_atr" not in features.columns:
        features["current_d1_range_vs_atr"] = pd.NA
    raw_d1_range_vs_atr = pd.to_numeric(features["current_d1_range_vs_atr"], errors="coerce")
    if "current_d1_range_vs_atr_capped" not in features.columns:
        features["current_d1_range_vs_atr_capped"] = raw_d1_range_vs_atr.clip(lower=0.0, upper=3.0)
    else:
        features["current_d1_range_vs_atr_capped"] = pd.to_numeric(
            features["current_d1_range_vs_atr_capped"],
            errors="coerce",
        ).fillna(raw_d1_range_vs_atr.clip(lower=0.0, upper=3.0))

    for column in NUMERIC_FEATURES:
        features[column] = pd.to_numeric(features[column], errors="coerce")

    features["position_in_d1_range"] = features["position_in_d1_range"].clip(lower=0.0, upper=1.0)
    features["daily_atr_consumed_pct"] = features["daily_atr_consumed_pct"].clip(lower=0.0, upper=1.0)
    features["current_d1_range_vs_atr_capped"] = features["current_d1_range_vs_atr_capped"].clip(lower=0.0, upper=3.0)

    for column in CATEGORICAL_FEATURES:
        features[column] = features[column].astype("string").fillna("unknown")

    features["near_key_level"] = features["near_key_level"].astype("string").str.lower()
    features["near_key_level"] = features["near_key_level"].replace({"true": "yes", "1": "yes", "false": "no", "0": "no"})
    return features[FEATURE_COLUMNS]
