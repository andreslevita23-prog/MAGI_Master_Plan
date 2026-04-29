from __future__ import annotations

from typing import Any

from magi.contracts import MageVote
from simulator.schemas import Snapshot, as_float


class BaltasarRuleBased:
    def __init__(self, config: dict):
        self.config = config
        self.version = str(config.get("version", "rule_based_v0.1"))

    def evaluate(self, snapshot: Snapshot) -> MageVote:
        buy_min = float(self.config.get("rsi_buy_min", 52.0))
        sell_max = float(self.config.get("rsi_sell_max", 48.0))
        features_used = ["features", "rsi_14", "ema_20", "ema_50", "momentum", "structure_direction"]
        features = snapshot.features or snapshot.raw

        rsi = as_float(_find(features, "rsi_14") or snapshot.raw.get("rsi_14"))
        momentum = str(_find(features, "momentum") or snapshot.raw.get("momentum") or "").lower()
        structure = str(_find(features, "structure_direction") or snapshot.raw.get("structure_direction") or "").lower()
        ema20 = as_float(_find(features, "ema_20") or snapshot.raw.get("ema_20"))
        ema50 = as_float(_find(features, "ema_50") or snapshot.raw.get("ema_50"))

        bullish_score = 0
        bearish_score = 0
        if rsi is not None and rsi >= buy_min:
            bullish_score += 1
        if rsi is not None and rsi <= sell_max:
            bearish_score += 1
        if momentum == "bullish":
            bullish_score += 1
        if momentum == "bearish":
            bearish_score += 1
        if structure == "bullish":
            bullish_score += 1
        if structure == "bearish":
            bearish_score += 1
        if ema20 is not None and ema50 is not None and ema20 > ema50:
            bullish_score += 1
        if ema20 is not None and ema50 is not None and ema20 < ema50:
            bearish_score += 1

        if bullish_score >= 2 and bullish_score > bearish_score:
            direction = "BUY"
            confidence = min(0.9, 0.55 + bullish_score * 0.1)
            reason = "Rule-based technical context favors BUY."
        elif bearish_score >= 2 and bearish_score > bullish_score:
            direction = "SELL"
            confidence = min(0.9, 0.55 + bearish_score * 0.1)
            reason = "Rule-based technical context favors SELL."
        else:
            direction = "NEUTRAL"
            confidence = 0.55
            reason = "Technical context is not directional enough for v0.1."

        return MageVote("mage_vote_v1", snapshot.snapshot_id, "BALTASAR", self.version, None, direction, None, confidence, "LOW", direction.lower(), features_used, reason)


def _find(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for nested in value.values():
            found = _find(nested, key)
            if found is not None:
                return found
    return None
