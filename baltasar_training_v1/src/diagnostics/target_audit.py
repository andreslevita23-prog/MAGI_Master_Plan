"""Target audit and sensitivity analysis."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.evaluation.metrics import compute_model_metrics
from src.features.engineering import build_feature_frame, normalize_dataframe
from src.features.targeting import prepare_target
from src.models.training import build_model_pipeline, temporal_split


@dataclass
class TargetScenarioResult:
    name: str
    horizon_steps: int
    buy_threshold: float
    sell_threshold: float
    rows: int
    neutral_share: float
    buy_share: float
    sell_share: float
    imbalance_ratio: float
    accuracy: float
    f1_macro: float


def evaluate_target_scenarios(
    raw_df: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Compare target construction scenarios and resulting baseline performance."""
    results: list[dict[str, Any]] = []
    label_order = config["dataset"]["label_order"]
    baseline_cfg = config["models"]["baseline_tree"]

    for scenario in config["diagnostics"]["target_scenarios"]:
        scenario_config = deepcopy(config)
        scenario_config["dataset"]["derived_target"]["horizon_steps"] = scenario["horizon_steps"]
        scenario_config["dataset"]["derived_target"]["buy_threshold"] = scenario["buy_threshold"]
        scenario_config["dataset"]["derived_target"]["sell_threshold"] = scenario["sell_threshold"]

        normalized = normalize_dataframe(raw_df, scenario_config)
        labelled = prepare_target(normalized, scenario_config)
        X, y, timestamps = build_feature_frame(labelled, scenario_config)
        split = temporal_split(X, y, timestamps, test_size=float(scenario_config["split"]["test_size"]))

        pipeline = build_model_pipeline(split.X_train, scenario_config, baseline_cfg)
        pipeline.fit(split.X_train, split.y_train)
        predictions = pipeline.predict(split.X_test)
        metrics = compute_model_metrics(split.y_test, predictions, label_order)

        distribution = y.value_counts(normalize=True)
        min_share = max(float(distribution.min()), 1e-9)
        max_share = float(distribution.max())

        results.append(
            TargetScenarioResult(
                name=scenario["name"],
                horizon_steps=int(scenario["horizon_steps"]),
                buy_threshold=float(scenario["buy_threshold"]),
                sell_threshold=float(scenario["sell_threshold"]),
                rows=int(len(labelled)),
                neutral_share=float(distribution.get("NEUTRAL", 0.0)),
                buy_share=float(distribution.get("BUY", 0.0)),
                sell_share=float(distribution.get("SELL", 0.0)),
                imbalance_ratio=max_share / min_share,
                accuracy=float(metrics["accuracy"]),
                f1_macro=float(metrics["f1_macro"]),
            ).__dict__
        )

    return pd.DataFrame(results).sort_values("f1_macro", ascending=False).reset_index(drop=True)
