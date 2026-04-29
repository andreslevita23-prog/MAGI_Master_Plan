from __future__ import annotations

from magi.contracts import MageVote
from simulator.schemas import Snapshot, as_float


class GasparRuleBased:
    def __init__(self, config: dict):
        self.config = config
        self.version = str(config.get("version", "rule_based_v0.1"))

    def evaluate(self, snapshot: Snapshot) -> MageVote:
        context = snapshot.gaspar_context
        features_used = ["gaspar_context.higher_timeframe_confluence", "gaspar_context.timing_quality", "gaspar_context.price_structure_position"]
        if not context:
            return self._vote(snapshot, "POOR", 0.85, "HIGH", "missing_context", features_used, "Gaspar context is missing.")

        alignment = str(context.get("higher_timeframe_confluence", {}).get("directional_alignment") or "").lower()
        timing = context.get("timing_quality", {})
        atr_consumed = as_float(timing.get("daily_atr_consumed_pct"), 0.0) or 0.0
        session = str(timing.get("active_session") or snapshot.active_session or "").lower()
        near_key_level = context.get("price_structure_position", {}).get("near_key_level")

        good_atr = float(self.config.get("max_daily_atr_consumed_good", 0.85))
        fair_atr = float(self.config.get("max_daily_atr_consumed_fair", 1.2))

        if alignment == "aligned" and atr_consumed <= good_atr and session not in {"inactive", ""}:
            return self._vote(snapshot, "GOOD", 0.78, "LOW", "aligned", features_used, "Opportunity quality is acceptable: aligned context with available daily range.")
        if alignment in {"aligned", "neutral", ""} and atr_consumed <= fair_atr:
            risk = "MEDIUM" if near_key_level else "LOW"
            return self._vote(snapshot, "FAIR", 0.65, risk, "mixed", features_used, "Opportunity quality is usable but not strong.")
        return self._vote(snapshot, "POOR", 0.8, "MEDIUM", "poor_range", features_used, "Opportunity quality is weak for v0.1.")

    def _vote(self, snapshot: Snapshot, quality: str, confidence: float, risk_flag: str, context_tag: str, features_used: list[str], reason: str) -> MageVote:
        return MageVote("mage_vote_v1", snapshot.snapshot_id, "GASPAR", self.version, None, None, quality, confidence, risk_flag, context_tag, features_used, reason)
