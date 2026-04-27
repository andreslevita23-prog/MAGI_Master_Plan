from __future__ import annotations

from typing import Mapping

import pandas as pd

PILLAR_WEIGHTS = {
    "higher_timeframe_confluence": 0.40,
    "price_structure_position": 0.30,
    "timing_quality": 0.20,
    "day_context": 0.10,
}


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _num(row: Mapping[str, object], key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(row: Mapping[str, object], key: str, default: str = "unknown") -> str:
    value = row.get(key, default)
    if pd.isna(value):
        return default
    return str(value).strip().lower()


def score_higher_timeframe_confluence(row: Mapping[str, object]) -> float:
    alignment = _text(row, "directional_alignment")
    h4 = _text(row, "h4_structure")
    d1 = _text(row, "d1_structure")

    score = 0.0
    if alignment == "aligned":
        score += 0.55
    elif alignment == "neutral":
        score += 0.25

    if h4 == d1 and h4 in {"bullish", "bearish"}:
        score += 0.35
    elif "range" in {h4, d1}:
        score += 0.10

    if h4 in {"bullish", "bearish", "range"} and d1 in {"bullish", "bearish", "range"}:
        score += 0.10

    return _clip(score)


def score_price_structure_position(row: Mapping[str, object]) -> float:
    support = abs(_num(row, "distance_to_d1_support", 0.0))
    resistance = abs(_num(row, "distance_to_d1_resistance", 0.0))
    range_position = _clip(_num(row, "position_in_d1_range", 0.5))
    near_key_level = _text(row, "near_key_level") in {"true", "yes", "1"}
    direction = _text(row, "proposed_direction")

    if direction == "buy":
        directional_space = resistance / (support + resistance + 1e-9)
        location = 1.0 - range_position
    elif direction == "sell":
        directional_space = support / (support + resistance + 1e-9)
        location = range_position
    else:
        directional_space = 0.35
        location = 0.35

    key_level_bonus = 0.15 if near_key_level else 0.0
    return _clip((directional_space * 0.55) + (location * 0.30) + key_level_bonus)


def score_timing_quality(row: Mapping[str, object]) -> float:
    session = _text(row, "active_session")
    atr_consumed = _clip(_num(row, "daily_atr_consumed_pct", 1.0))
    available_range = max(0.0, _num(row, "available_range_to_next_level", 0.0))
    pattern = _text(row, "h4_candle_pattern")

    session_score = {
        "london": 1.0,
        "new_york": 0.9,
        "overlap": 1.0,
        "asia": 0.55,
        "inactive": 0.15,
    }.get(session, 0.35)
    range_score = _clip(available_range / 0.005)
    atr_score = 1.0 - atr_consumed
    pattern_score = {"rejection": 0.9, "engulfing": 0.85, "inside": 0.55, "none": 0.35}.get(pattern, 0.35)

    return _clip((session_score * 0.30) + (range_score * 0.30) + (atr_score * 0.25) + (pattern_score * 0.15))


def score_day_context(row: Mapping[str, object]) -> float:
    day = _text(row, "day_of_week")
    volatility_ratio = _num(row, "d1_volatility_vs_20d_avg", 1.0)
    d1_range_vs_atr = _clip(_num(row, "current_d1_range_vs_atr", 1.0))

    day_score = {
        "monday": 0.55,
        "tuesday": 0.85,
        "wednesday": 0.90,
        "thursday": 0.85,
        "friday": 0.60,
    }.get(day, 0.50)
    volatility_score = _clip(1.0 - abs(volatility_ratio - 1.0))
    range_score = 1.0 - d1_range_vs_atr
    return _clip((day_score * 0.35) + (volatility_score * 0.35) + (range_score * 0.30))


def compute_pillar_scores(row: Mapping[str, object]) -> dict[str, float]:
    return {
        "higher_timeframe_confluence": score_higher_timeframe_confluence(row),
        "price_structure_position": score_price_structure_position(row),
        "timing_quality": score_timing_quality(row),
        "day_context": score_day_context(row),
    }


def compute_score_v1(row: Mapping[str, object]) -> float:
    pillars = compute_pillar_scores(row)
    score = sum(pillars[name] * weight for name, weight in PILLAR_WEIGHTS.items())
    return round(_clip(score), 4)


def compute_score_v2(row: Mapping[str, object]) -> float:
    score = compute_score_v1(row)
    direction = _text(row, "proposed_direction")
    available_range = _num(row, "available_range_to_next_level", 0.0)
    d1_range_vs_atr = _num(row, "current_d1_range_vs_atr", 1.0)

    if available_range <= 0.0:
        if direction in {"buy", "sell"}:
            score = min(score, 0.30)
        else:
            score = min(score, 0.44)

    if d1_range_vs_atr > 1.5:
        score -= 0.25
    elif d1_range_vs_atr > 1.2:
        score -= 0.12

    if direction == "neutral":
        score = min(score, 0.55)

    return round(_clip(score), 4)


def compute_score_v3(row: Mapping[str, object]) -> float:
    score = compute_score_v1(row)
    direction = _text(row, "proposed_direction")
    available_range = _num(row, "available_range_to_next_level", 0.0)
    d1_range_vs_atr = _num(row, "current_d1_range_vs_atr", 1.0)

    if available_range <= 0.0:
        if direction in {"buy", "sell"}:
            score = min(score, 0.30)
        else:
            score = min(score, 0.44)

    if d1_range_vs_atr > 1.5:
        score -= 0.20
    elif d1_range_vs_atr > 1.2:
        score -= 0.06

    if direction == "neutral":
        score = min(score, 0.55)

    return round(_clip(score), 4)


def compute_score(row: Mapping[str, object], target_version: str = "v1") -> float:
    if target_version == "v3":
        return compute_score_v3(row)
    if target_version == "v2":
        return compute_score_v2(row)
    return compute_score_v1(row)


def classify_opportunity_v1(score: float) -> str:
    if score >= 0.65:
        return "GOOD"
    if score >= 0.40:
        return "FAIR"
    return "POOR"


def classify_opportunity_v2(score: float, row: Mapping[str, object] | None = None) -> str:
    if row is not None:
        direction = _text(row, "proposed_direction")
        available_range = _num(row, "available_range_to_next_level", 0.0)
        d1_range_vs_atr = _num(row, "current_d1_range_vs_atr", 1.0)
        if direction not in {"buy", "sell"} and score >= 0.60:
            return "FAIR"
        if available_range <= 0.0 and direction in {"buy", "sell"}:
            return "POOR"
        if d1_range_vs_atr > 1.5 and score >= 0.60:
            return "FAIR"

    if score >= 0.60:
        return "GOOD"
    if score >= 0.45:
        return "FAIR"
    return "POOR"


def classify_opportunity_v3(score: float, row: Mapping[str, object] | None = None) -> str:
    if row is not None:
        direction = _text(row, "proposed_direction")
        available_range = _num(row, "available_range_to_next_level", 0.0)
        d1_range_vs_atr = _num(row, "current_d1_range_vs_atr", 1.0)
        if direction not in {"buy", "sell"} and score >= 0.60:
            return "FAIR"
        if available_range <= 0.0 and direction in {"buy", "sell"}:
            return "POOR"
        if d1_range_vs_atr > 1.5 and score >= 0.60:
            return "FAIR"

    if score >= 0.60:
        return "GOOD"
    if score >= 0.45:
        return "FAIR"
    return "POOR"


def classify_opportunity(score: float, target_version: str = "v1", row: Mapping[str, object] | None = None) -> str:
    if target_version == "v3":
        return classify_opportunity_v3(score, row)
    if target_version == "v2":
        return classify_opportunity_v2(score, row)
    return classify_opportunity_v1(score)


def attach_heuristic_target(data: pd.DataFrame, target_version: str = "v1", overwrite: bool = False) -> pd.DataFrame:
    prepared = data.copy()
    row_dicts = prepared.apply(lambda row: row.to_dict(), axis=1)
    scores = row_dicts.map(lambda row: compute_score(row, target_version=target_version))
    existing_score = prepared.get("score_oportunidad")
    prepared["score_oportunidad"] = pd.to_numeric(existing_score, errors="coerce") if existing_score is not None else pd.NA
    if overwrite:
        prepared["score_oportunidad"] = scores
    else:
        prepared["score_oportunidad"] = prepared["score_oportunidad"].fillna(scores)
    prepared["score_oportunidad"] = prepared["score_oportunidad"].fillna(scores)

    if "voto" not in prepared.columns:
        prepared["voto"] = pd.NA
    prepared["voto"] = prepared["voto"].astype("string")
    if overwrite:
        prepared["voto"] = [
            classify_opportunity(score, target_version=target_version, row=row)
            for score, row in zip(prepared["score_oportunidad"], row_dicts)
        ]
    else:
        generated_votes = [
            classify_opportunity(score, target_version=target_version, row=row)
            for score, row in zip(prepared["score_oportunidad"], row_dicts)
        ]
        prepared["voto"] = prepared["voto"].fillna(pd.Series(generated_votes, index=prepared.index))
    prepared["voto"] = prepared["voto"].str.upper()
    prepared["target_version"] = target_version
    return prepared
