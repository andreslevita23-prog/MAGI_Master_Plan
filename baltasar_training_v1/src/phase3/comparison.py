"""Scenario comparison for Baltasar v1.1."""

from __future__ import annotations

from typing import Any

import joblib
import pandas as pd

from src.evaluation.metrics import class_metrics_table, compute_model_metrics
from src.features.engineering import build_feature_frame, normalize_dataframe
from src.features.targeting import prepare_target
from src.models.training import build_model_pipeline, extract_feature_importance, temporal_split
from src.phase3.utils import clone_config_with_target, current_target_signature
from src.diagnostics.temporal_validation import walk_forward_evaluation


def run_comparison_scenarios(
    raw_df: pd.DataFrame,
    config: dict[str, Any],
    candidate_row: pd.Series,
    models_dir,
    metrics_dir,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """Compare the required scenarios across baseline and random forest."""
    current_horizon, current_threshold = current_target_signature(config)
    comparison_rows: list[dict[str, Any]] = []
    class_tables: dict[str, pd.DataFrame] = {}
    feature_tables: dict[str, pd.DataFrame] = {}
    walk_tables: dict[str, pd.DataFrame] = {}

    for scenario in config["phase3"]["comparison"]["scenarios"]:
        if scenario["target_source"] == "current":
            scenario_config = clone_config_with_target(
                config,
                horizon_steps=current_horizon,
                threshold=current_threshold,
                feature_variant=scenario["feature_variant"],
            )
            target_name = f"h{current_horizon}_t{int(round(current_threshold * 10000)):02d}"
        else:
            scenario_config = clone_config_with_target(
                config,
                horizon_steps=int(candidate_row["horizon_steps"]),
                threshold=float(candidate_row["threshold"]),
                feature_variant=scenario["feature_variant"],
            )
            target_name = str(candidate_row["target_name"])

        normalized = normalize_dataframe(raw_df, scenario_config)
        labelled = prepare_target(normalized, scenario_config)
        X, y, timestamps = build_feature_frame(labelled, scenario_config)
        split = temporal_split(X, y, timestamps, test_size=float(scenario_config["split"]["test_size"]))
        walk_forward_df = walk_forward_evaluation(X, y, timestamps, scenario_config)
        walk_tables[scenario["name"]] = walk_forward_df

        for model_name in ["baseline_tree", "random_forest"]:
            model_cfg = scenario_config["models"][model_name]
            pipeline = build_model_pipeline(split.X_train, scenario_config, model_cfg)
            pipeline.fit(split.X_train, split.y_train)
            predictions = pipeline.predict(split.X_test)
            metrics = compute_model_metrics(split.y_test, predictions, scenario_config["dataset"]["label_order"])
            class_df = class_metrics_table(split.y_test, predictions, scenario_config["dataset"]["label_order"])
            class_tables[f"{scenario['name']}__{model_name}"] = class_df
            class_df.to_csv(
                metrics_dir / f"{scenario['name']}__{model_name}_class_metrics.csv",
                index=False,
            )

            feature_df = extract_feature_importance(
                pipeline,
                split.X_test,
                split.y_test,
                int(config["experiment"]["seed"]),
            )
            feature_tables[f"{scenario['name']}__{model_name}"] = feature_df
            feature_df.to_csv(
                metrics_dir / f"{scenario['name']}__{model_name}_feature_importance.csv",
                index=False,
            )
            joblib.dump(pipeline, models_dir / f"{scenario['name']}__{model_name}.joblib")

            valid_walk = walk_forward_df[
                (walk_forward_df["model_name"] == model_name) & walk_forward_df["f1_macro"].notna()
            ]
            comparison_rows.append(
                {
                    "scenario_name": scenario["name"],
                    "target_name": target_name,
                    "feature_variant": scenario["feature_variant"],
                    "model_name": model_name,
                    "rows": int(len(labelled)),
                    "feature_count": int(split.X_train.shape[1]),
                    "accuracy": float(metrics["accuracy"]),
                    "precision_macro": float(metrics["precision_macro"]),
                    "recall_macro": float(metrics["recall_macro"]),
                    "f1_macro": float(metrics["f1_macro"]),
                    "walk_forward_f1_mean": float(valid_walk["f1_macro"].mean()) if not valid_walk.empty else None,
                    "walk_forward_f1_std": float(valid_walk["f1_macro"].std(ddof=0)) if not valid_walk.empty else None,
                    "walk_forward_accuracy_mean": float(valid_walk["accuracy"].mean()) if not valid_walk.empty else None,
                }
            )

    comparison_df = pd.DataFrame(comparison_rows).sort_values(
        ["walk_forward_f1_mean", "f1_macro"], ascending=False
    ).reset_index(drop=True)
    return comparison_df, class_tables, feature_tables, walk_tables
