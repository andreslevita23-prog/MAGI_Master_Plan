"""Systematic target exploration for phase 3."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.evaluation.metrics import class_metrics_table, compute_model_metrics
from src.features.engineering import build_feature_frame, normalize_dataframe
from src.features.targeting import prepare_target
from src.models.training import build_model_pipeline, temporal_split
from src.phase3.utils import clone_config_with_target
from src.diagnostics.temporal_validation import walk_forward_evaluation


def evaluate_target_grid(raw_df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Evaluate a target grid using the baseline tree as a controlled scorer."""
    baseline_cfg = config["models"]["baseline_tree"]
    label_order = config["dataset"]["label_order"]
    rows: list[dict[str, Any]] = []

    for horizon in config["phase3"]["target_grid"]["horizons"]:
        for threshold in config["phase3"]["target_grid"]["thresholds"]:
            scenario_config = clone_config_with_target(config, horizon_steps=horizon, threshold=threshold)
            normalized = normalize_dataframe(raw_df, scenario_config)
            labelled = prepare_target(normalized, scenario_config)
            X, y, timestamps = build_feature_frame(labelled, scenario_config)
            split = temporal_split(X, y, timestamps, test_size=float(scenario_config["split"]["test_size"]))

            pipeline = build_model_pipeline(split.X_train, scenario_config, baseline_cfg)
            pipeline.fit(split.X_train, split.y_train)
            predictions = pipeline.predict(split.X_test)
            metrics = compute_model_metrics(split.y_test, predictions, label_order)
            class_df = class_metrics_table(split.y_test, predictions, label_order)

            walk_forward_df = walk_forward_evaluation(X, y, timestamps, scenario_config)
            valid_walk = walk_forward_df[
                (walk_forward_df["model_name"] == "baseline_tree") & walk_forward_df["f1_macro"].notna()
            ]

            distribution = y.value_counts(normalize=True)
            max_share = float(distribution.max())
            min_share = max(float(distribution.min()), 1e-9)

            row = {
                "target_name": f"h{int(horizon)}_t{int(round(threshold * 10000)):02d}",
                "horizon_steps": int(horizon),
                "threshold": float(threshold),
                "rows": int(len(labelled)),
                "sell_share": float(distribution.get("SELL", 0.0)),
                "neutral_share": float(distribution.get("NEUTRAL", 0.0)),
                "buy_share": float(distribution.get("BUY", 0.0)),
                "imbalance_ratio": max_share / min_share,
                "accuracy": float(metrics["accuracy"]),
                "f1_macro": float(metrics["f1_macro"]),
                "precision_macro": float(metrics["precision_macro"]),
                "recall_macro": float(metrics["recall_macro"]),
                "walk_forward_f1_mean": float(valid_walk["f1_macro"].mean()) if not valid_walk.empty else None,
                "walk_forward_f1_std": float(valid_walk["f1_macro"].std(ddof=0)) if not valid_walk.empty else None,
                "walk_forward_accuracy_mean": float(valid_walk["accuracy"].mean()) if not valid_walk.empty else None,
            }
            for _, class_row in class_df.iterrows():
                label = class_row["label"].lower()
                row[f"{label}_precision"] = float(class_row["precision"])
                row[f"{label}_recall"] = float(class_row["recall"])
                row[f"{label}_f1"] = float(class_row["f1"])

            rows.append(row)

    result = pd.DataFrame(rows)
    result["balance_score"] = 1 / result["imbalance_ratio"]
    result["stability_score"] = 1 / (1 + result["walk_forward_f1_std"].fillna(result["walk_forward_f1_std"].max()))
    return result.sort_values(["f1_macro", "walk_forward_f1_mean"], ascending=False).reset_index(drop=True)


def select_target_candidates(target_grid_df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Score targets by signal, balance and stability instead of only point F1."""
    weights = config["phase3"]["target_selection"]["score_weights"]
    scored = target_grid_df.copy()

    for column in ["f1_macro", "balance_score", "stability_score", "walk_forward_f1_mean"]:
        min_value = float(scored[column].min())
        max_value = float(scored[column].max())
        if max_value - min_value < 1e-9:
            scored[f"{column}_norm"] = 1.0
        else:
            scored[f"{column}_norm"] = (scored[column] - min_value) / (max_value - min_value)

    scored["candidate_score"] = (
        scored["f1_macro_norm"] * float(weights["f1_macro"])
        + scored["balance_score_norm"] * float(weights["balance"])
        + scored["stability_score_norm"] * float(weights["stability"])
    )
    scored = scored.sort_values(
        ["candidate_score", "walk_forward_f1_mean", "f1_macro"],
        ascending=False,
    ).reset_index(drop=True)
    return scored.head(int(config["phase3"]["target_selection"]["max_candidates"]))
