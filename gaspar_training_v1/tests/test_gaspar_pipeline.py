from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gaspar.data import load_dataset
from src.gaspar.features import FEATURE_COLUMNS, build_feature_frame
from src.gaspar.schemas import build_gaspar_output
from src.gaspar.targeting import attach_heuristic_target, classify_opportunity, compute_score, daily_range_state


def strong_record() -> dict:
    return {
        "module": "GASPAR",
        "role": "opportunity_quality",
        "symbol": "EURUSD",
        "timestamp": "2026-04-27T12:00:00Z",
        "proposed_direction": "BUY",
        "h4_structure": "bullish",
        "d1_structure": "bullish",
        "directional_alignment": "aligned",
        "distance_to_d1_support": 0.001,
        "distance_to_d1_resistance": 0.006,
        "position_in_d1_range": 0.20,
        "near_key_level": True,
        "active_session": "london",
        "daily_atr_consumed_pct": 0.25,
        "available_range_to_next_level": 0.006,
        "h4_candle_pattern": "rejection",
        "day_of_week": "wednesday",
        "d1_volatility_vs_20d_avg": 1.0,
        "current_d1_range_vs_atr": 0.35,
    }


def weak_record() -> dict:
    record = strong_record()
    record.update(
        {
            "h4_structure": "bearish",
            "d1_structure": "bearish",
            "directional_alignment": "contradictory",
            "distance_to_d1_support": 0.006,
            "distance_to_d1_resistance": 0.001,
            "position_in_d1_range": 0.90,
            "near_key_level": False,
            "active_session": "inactive",
            "daily_atr_consumed_pct": 0.95,
            "available_range_to_next_level": 0.0004,
            "h4_candle_pattern": "none",
            "day_of_week": "friday",
            "d1_volatility_vs_20d_avg": 1.8,
            "current_d1_range_vs_atr": 0.95,
        }
    )
    return record


def test_feature_set_excludes_baltasar_indicators() -> None:
    forbidden = {"e" + "ma", "r" + "si", "momen" + "tum"}
    joined = " ".join(FEATURE_COLUMNS).lower()
    assert not any(token in joined for token in forbidden)

    bot_path = ROOT.parent / "servidor-prosperity" / "integrations" / "mt5" / "Bot_A_sub2.mq5"
    bot_source = bot_path.read_text(encoding="utf-8").lower()
    assert "i" + "ma(" not in bot_source
    assert "i" + "rsi(" not in bot_source
    assert "momen" + "tum" not in bot_source


def test_proxy_direction_from_structure(tmp_path: Path) -> None:
    path = tmp_path / "proxy.csv"
    pd.DataFrame([
        {"symbol": "EURUSD", "timestamp": "2026-04-27T12:00:00Z", "h4_structure": "bullish", "d1_structure": "bullish"},
        {"symbol": "EURUSD", "timestamp": "2026-04-27T12:05:00Z", "h4_structure": "bearish", "d1_structure": "bearish"},
        {"symbol": "EURUSD", "timestamp": "2026-04-27T12:10:00Z", "h4_structure": "bullish", "d1_structure": "range"},
        {"symbol": "EURUSD", "timestamp": "2026-04-27T12:15:00Z", "h4_structure": "range", "d1_structure": "bullish"},
        {"symbol": "EURUSD", "timestamp": "2026-04-27T12:20:00Z", "h4_structure": "range", "d1_structure": "bearish"},
        {"symbol": "EURUSD", "timestamp": "2026-04-27T12:25:00Z", "h4_structure": "bearish", "d1_structure": "bullish"},
        {"symbol": "EURUSD", "timestamp": "2026-04-27T12:30:00Z", "h4_structure": "bullish", "d1_structure": "bearish"},
    ]).to_csv(path, index=False)

    data = load_dataset(tmp_path)

    assert data["proposed_direction"].tolist() == ["BUY", "SELL", "NEUTRAL", "BUY", "SELL", "NEUTRAL", "NEUTRAL"]
    assert data["directional_alignment"].tolist() == ["aligned", "aligned", "neutral", "aligned", "aligned", "neutral", "neutral"]


def test_score_and_classification_thresholds() -> None:
    high_score = compute_score(strong_record())
    low_score = compute_score(weak_record())

    assert high_score >= 0.65
    assert classify_opportunity(high_score) == "GOOD"
    assert classify_opportunity(0.64) == "FAIR"
    assert classify_opportunity(0.39) == "POOR"
    assert classify_opportunity(low_score) == "POOR"


def test_target_v2_guardrails() -> None:
    neutral = strong_record()
    neutral["proposed_direction"] = "NEUTRAL"
    neutral["directional_alignment"] = "neutral"
    neutral_score = compute_score(neutral, target_version="v2")
    assert neutral_score <= 0.55
    assert classify_opportunity(neutral_score, target_version="v2", row=neutral) != "GOOD"

    no_range = strong_record()
    no_range["available_range_to_next_level"] = 0.0
    no_range_score = compute_score(no_range, target_version="v2")
    assert classify_opportunity(no_range_score, target_version="v2", row=no_range) == "POOR"

    exhausted = strong_record()
    exhausted["current_d1_range_vs_atr"] = 1.6
    exhausted_score = compute_score(exhausted, target_version="v2")
    assert exhausted_score < compute_score(strong_record(), target_version="v2")


def test_target_v3_guardrails_and_capped_feature() -> None:
    raw = pd.DataFrame([{**strong_record(), "current_d1_range_vs_atr": 3.7}])
    features = build_feature_frame(raw)
    assert "current_d1_range_vs_atr_capped" in features.columns
    assert "current_d1_range_vs_atr" not in features.columns
    assert features.loc[0, "current_d1_range_vs_atr_capped"] == 3.0

    neutral = strong_record()
    neutral["proposed_direction"] = "NEUTRAL"
    neutral_score = compute_score(neutral, target_version="v3")
    assert neutral_score <= 0.55
    assert classify_opportunity(neutral_score, target_version="v3", row=neutral) != "GOOD"

    no_range = strong_record()
    no_range["available_range_to_next_level"] = 0.0
    assert classify_opportunity(compute_score(no_range, target_version="v3"), target_version="v3", row=no_range) == "POOR"

    moderate = strong_record()
    moderate["current_d1_range_vs_atr"] = 1.3
    assert compute_score(moderate, target_version="v3") > compute_score(moderate, target_version="v2")


def test_target_v4_daily_range_state_and_guardrails() -> None:
    early = {**strong_record(), "current_d1_range_vs_atr": 0.59}
    mid = {**strong_record(), "current_d1_range_vs_atr": 0.90}
    late = {**strong_record(), "current_d1_range_vs_atr": 1.21}

    assert daily_range_state(early) == "early"
    assert daily_range_state(mid) == "mid"
    assert daily_range_state(late) == "late"

    features = build_feature_frame(pd.DataFrame([early, mid, late]), target_version="v4")
    assert features["daily_range_state"].tolist() == ["EARLY", "MID", "LATE"]
    assert "current_d1_range_vs_atr_capped" not in features.columns

    late_with_space = {**strong_record(), "current_d1_range_vs_atr": 1.6, "available_range_to_next_level": 0.006}
    assert compute_score(late_with_space, target_version="v4") >= compute_score(late_with_space, target_version="v2")

    late_no_range = {**strong_record(), "current_d1_range_vs_atr": 1.6, "available_range_to_next_level": 0.0}
    assert classify_opportunity(compute_score(late_no_range, target_version="v4"), target_version="v4", row=late_no_range) == "POOR"

    neutral = {**strong_record(), "proposed_direction": "NEUTRAL"}
    neutral_score = compute_score(neutral, target_version="v4")
    assert neutral_score <= 0.55
    assert classify_opportunity(neutral_score, target_version="v4", row=neutral) != "GOOD"


def test_output_schema() -> None:
    output = build_gaspar_output(strong_record())
    assert output["module"] == "GASPAR"
    assert output["role"] == "opportunity_quality"
    assert output["voto"] in {"GOOD", "FAIR", "POOR"}
    assert 0.0 <= output["score_oportunidad"] <= 1.0
    assert set(output["pillars"]) == {
        "higher_timeframe_confluence",
        "price_structure_position",
        "timing_quality",
        "day_context",
    }
    assert isinstance(output["reason"], str)


def test_jsonl_dataset_loading_and_target(tmp_path: Path) -> None:
    path = tmp_path / "gaspar.jsonl"
    row = {
        "module": "GASPAR",
        "role": "opportunity_quality",
        "symbol": "EURUSD",
        "timestamp": "2026-04-27T12:00:00Z",
        "proposed_direction": "BUY",
        "higher_timeframe_confluence": {
            "h4_structure": "bullish",
            "d1_structure": "bullish",
            "directional_alignment": "aligned",
        },
        "price_structure_position": {
            "distance_to_d1_support": 0.001,
            "distance_to_d1_resistance": 0.006,
            "position_in_d1_range": 0.2,
            "near_key_level": True,
        },
        "timing_quality": {
            "active_session": "london",
            "daily_atr_consumed_pct": 0.25,
            "available_range_to_next_level": 0.006,
            "h4_candle_pattern": "rejection",
        },
        "day_context": {
            "day_of_week": "wednesday",
            "d1_volatility_vs_20d_avg": 1.0,
            "current_d1_range_vs_atr": 0.35,
        },
    }
    path.write_text(json.dumps(row), encoding="utf-8")

    data = load_dataset(tmp_path)
    prepared = attach_heuristic_target(data)

    assert len(prepared) == 1
    assert prepared.loc[0, "voto"] == "GOOD"
    assert prepared.loc[0, "score_oportunidad"] >= 0.65


def test_csv_dataset_loading(tmp_path: Path) -> None:
    path = tmp_path / "gaspar.csv"
    pd.DataFrame([strong_record()]).to_csv(path, index=False)

    data = load_dataset(tmp_path)

    assert len(data) == 1
    assert data.loc[0, "symbol"] == "EURUSD"
    assert "source_file" in data.columns
