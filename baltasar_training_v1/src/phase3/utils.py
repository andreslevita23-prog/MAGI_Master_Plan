"""Utility helpers for phase 3 experiments."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def clone_config_with_target(
    config: dict[str, Any],
    horizon_steps: int,
    threshold: float,
    feature_variant: str | None = None,
) -> dict[str, Any]:
    """Clone config while overriding target and optional feature variant."""
    cloned = deepcopy(config)
    cloned["dataset"]["derived_target"]["horizon_steps"] = int(horizon_steps)
    cloned["dataset"]["derived_target"]["buy_threshold"] = float(threshold)
    cloned["dataset"]["derived_target"]["sell_threshold"] = -float(threshold)
    if feature_variant is not None:
        cloned["dataset"]["feature_variant"] = feature_variant
    return cloned


def current_target_signature(config: dict[str, Any]) -> tuple[int, float]:
    """Return the configured target horizon and positive threshold."""
    derived_cfg = config["dataset"]["derived_target"]
    return int(derived_cfg["horizon_steps"]), float(derived_cfg["buy_threshold"])
