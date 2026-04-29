from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MageVote:
    schema_version: str
    snapshot_id: str
    agent: str
    agent_version: str
    vote: str | None
    direction: str | None
    quality: str | None
    confidence: float
    risk_flag: str
    context_tag: str
    features_used: list[str]
    reason: str


@dataclass(frozen=True)
class CeoDecision:
    schema_version: str
    snapshot_id: str
    decision_id: str
    ceo_version: str
    action: str
    direction: str | None
    decision_rule: str
    votes: dict[str, Any]
    reason: str
