from __future__ import annotations

from magi.contracts import MageVote
from simulator.schemas import Snapshot


class MelchorRuleBased:
    def __init__(self, config: dict):
        self.config = config
        self.version = str(config.get("version", "rule_based_v0.1"))

    def evaluate(self, snapshot: Snapshot) -> MageVote:
        max_spread = float(self.config.get("max_spread_pips", 2.0))
        allowed_sessions = {str(item).lower() for item in self.config.get("allowed_sessions", [])}
        block_dd = float(self.config.get("daily_drawdown_block_percent", 1.0))
        features_used = ["spread_pips", "active_session", "validation", "account.daily_drawdown_percent"]

        if snapshot.validation.get("is_valid") is False:
            return self._vote(snapshot, "BLOCK", 0.95, "HIGH", "unclear", features_used, "Bot A marked the snapshot as invalid.")

        if snapshot.spread_pips is None or snapshot.spread_pips > max_spread:
            return self._vote(snapshot, "BLOCK", 0.9, "HIGH", "volatile", features_used, "Spread exceeds Melchor risk limits.")

        drawdown = snapshot.account.get("daily_drawdown_percent")
        if drawdown is not None and float(drawdown) >= block_dd:
            return self._vote(snapshot, "BLOCK", 0.95, "HIGH", "risk", features_used, "Daily drawdown block threshold reached.")

        session = (snapshot.active_session or "").lower()
        if allowed_sessions and session and session not in allowed_sessions:
            return self._vote(snapshot, "WARN", 0.7, "MEDIUM", "session", features_used, "Session is outside preferred Melchor windows.")

        return self._vote(snapshot, "APPROVE", 0.75, "LOW", "risk_ok", features_used, "Risk filters are acceptable for v0.1.")

    def _vote(self, snapshot: Snapshot, vote: str, confidence: float, risk_flag: str, context_tag: str, features_used: list[str], reason: str) -> MageVote:
        return MageVote("mage_vote_v1", snapshot.snapshot_id, "MELCHOR", self.version, vote, None, None, confidence, risk_flag, context_tag, features_used, reason)
