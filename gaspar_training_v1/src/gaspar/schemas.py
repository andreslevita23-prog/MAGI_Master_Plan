from __future__ import annotations

from .targeting import classify_opportunity, compute_pillar_scores, compute_score


def build_gaspar_output(record: dict, reason: str | None = None) -> dict:
    pillars = compute_pillar_scores(record)
    score = compute_score(record)
    vote = classify_opportunity(score)
    return {
        "module": "GASPAR",
        "role": "opportunity_quality",
        "voto": vote,
        "score_oportunidad": score,
        "pillars": {key: round(value, 4) for key, value in pillars.items()},
        "reason": reason or _default_reason(vote, pillars),
    }


def _default_reason(vote: str, pillars: dict[str, float]) -> str:
    strongest = max(pillars, key=pillars.get)
    weakest = min(pillars, key=pillars.get)
    return f"{vote}: strongest pillar={strongest}; weakest pillar={weakest}."
