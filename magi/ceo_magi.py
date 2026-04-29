from __future__ import annotations

from uuid import uuid5, NAMESPACE_URL

from magi.contracts import CeoDecision, MageVote
from simulator.schemas import Snapshot


class CeoMagiRuleBased:
    def __init__(self, config: dict):
        self.config = config
        self.version = str(config.get("version", "rule_based_v0.1"))
        self.strict_warn = bool(config.get("strict_warn", True))

    def decide(self, snapshot: Snapshot, melchor: MageVote, baltasar: MageVote, gaspar: MageVote) -> CeoDecision:
        decision_id = str(uuid5(NAMESPACE_URL, f"{snapshot.snapshot_id}:{self.version}"))
        votes = {
            "melchor": melchor.vote,
            "baltasar": baltasar.direction,
            "gaspar": gaspar.quality,
        }

        if melchor.vote == "BLOCK":
            return self._decision(snapshot, decision_id, "NO_TRADE", None, "melchor_block", votes, "Melchor blocked the snapshot.")
        if baltasar.direction == "NEUTRAL":
            return self._decision(snapshot, decision_id, "NO_TRADE", None, "baltasar_neutral", votes, "Baltasar did not provide a directional signal.")
        if gaspar.quality == "POOR":
            return self._decision(snapshot, decision_id, "NO_TRADE", None, "gaspar_poor", votes, "Gaspar rated opportunity quality as poor.")
        if melchor.vote == "WARN" and self.strict_warn:
            return self._decision(snapshot, decision_id, "SKIP_WARN", None, "melchor_warn_strict", votes, "Melchor warned and CEO-MAGI strict mode is enabled.")
        if melchor.vote in {"APPROVE", "WARN"} and baltasar.direction == "BUY" and gaspar.quality in {"GOOD", "FAIR"}:
            return self._decision(snapshot, decision_id, "OPEN_LONG", "LONG", "melchor_approve_baltasar_buy_gaspar_good_or_fair", votes, "MAGI v0.1 rules allow a long setup.")
        if melchor.vote in {"APPROVE", "WARN"} and baltasar.direction == "SELL" and gaspar.quality in {"GOOD", "FAIR"}:
            return self._decision(snapshot, decision_id, "OPEN_SHORT", "SHORT", "melchor_approve_baltasar_sell_gaspar_good_or_fair", votes, "MAGI v0.1 rules allow a short setup.")

        return self._decision(snapshot, decision_id, "NO_TRADE", None, "fallback_no_trade", votes, "No v0.1 CEO-MAGI rule allowed a trade.")

    def _decision(self, snapshot: Snapshot, decision_id: str, action: str, direction: str | None, rule: str, votes: dict, reason: str) -> CeoDecision:
        return CeoDecision("ceo_decision_v1", snapshot.snapshot_id, decision_id, self.version, action, direction, rule, votes, reason)
