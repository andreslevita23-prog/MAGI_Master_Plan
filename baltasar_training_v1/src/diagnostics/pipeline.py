"""Orchestrate Baltasar diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import confusion_matrix

from src.data.io import load_dataset
from src.evaluation.metrics import class_metrics_table
from src.features.engineering import build_feature_frame, normalize_dataframe
from src.features.targeting import prepare_target
from src.models.training import temporal_split
from src.utils import ensure_dir, get_logger, write_json
from src.visualization.diagnostic_plots import (
    save_class_distribution_comparison,
    save_correlation_heatmap,
    save_feature_boxplots,
    save_feature_scatter,
    save_metric_by_fold,
    save_normalized_confusion_matrix,
    save_target_sensitivity_plot,
)
from src.diagnostics.feature_analysis import (
    aggregate_feature_importance,
    class_separation_snapshot,
    correlated_feature_pairs,
    low_utility_features,
    numeric_feature_summary,
    univariate_numeric_scores,
)
from src.diagnostics.reporting import build_markdown_report, write_report
from src.diagnostics.target_audit import evaluate_target_scenarios
from src.diagnostics.temporal_validation import walk_forward_evaluation


LOGGER = get_logger("baltasar.diagnostics")


def _latest_summary_path(metrics_dir: Path) -> Path:
    summaries = sorted(metrics_dir.glob("*_run_summary.json"))
    if not summaries:
        raise FileNotFoundError("No run summaries found. Execute run_experiment.py first.")
    return summaries[-1]


def _load_summary(metrics_dir: Path, run_id: str | None) -> dict[str, Any]:
    if run_id:
        summary_path = metrics_dir / f"{run_id}_run_summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"Run summary not found for run_id={run_id}.")
    else:
        summary_path = _latest_summary_path(metrics_dir)
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _load_successful_model_paths(summary: dict[str, Any], project_root: Path) -> dict[str, Path]:
    run_id = summary["run_id"]
    models_dir = project_root / summary["config_snapshot"]["artifacts"]["models_dir"]
    paths = {}
    for model_name in summary["models"].keys():
        path = models_dir / f"{run_id}_{model_name}.joblib"
        if path.exists():
            paths[model_name] = path
    return paths


def _prediction_distribution(y_pred: pd.Series) -> dict[str, float]:
    distribution = y_pred.value_counts(normalize=True)
    return {label: float(value) for label, value in distribution.items()}


def run_diagnostics(config: dict[str, Any], project_root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Run the full diagnostic phase for one training run."""
    artifacts_cfg = config["artifacts"]
    metrics_dir = ensure_dir(project_root / artifacts_cfg["metrics_dir"])
    figures_dir = ensure_dir(project_root / artifacts_cfg["figures_dir"])
    reports_dir = ensure_dir(project_root / artifacts_cfg["reports_dir"])

    summary = _load_summary(metrics_dir, run_id)
    run_id = summary["run_id"]
    label_order = config["dataset"]["label_order"]
    LOGGER.info("Running diagnostics for %s", run_id)

    raw_df = load_dataset(config, project_root)
    normalized_raw_df = normalize_dataframe(raw_df, config)
    target_audit_df = evaluate_target_scenarios(normalized_raw_df, config)
    target_audit_df.to_csv(metrics_dir / f"{run_id}_target_audit.csv", index=False)
    save_target_sensitivity_plot(target_audit_df, figures_dir / f"{run_id}_target_sensitivity.png")
    save_class_distribution_comparison(
        target_audit_df,
        figures_dir / f"{run_id}_target_distribution_comparison.png",
    )

    processed_path = Path(summary["processed_dataset_path"])
    labelled_df = pd.read_csv(processed_path)
    labelled_df = normalize_dataframe(labelled_df, config)
    X, y, timestamps = build_feature_frame(labelled_df, config)
    split = temporal_split(X, y, timestamps, test_size=float(config["split"]["test_size"]))

    model_paths = _load_successful_model_paths(summary, project_root)
    class_tables: dict[str, pd.DataFrame] = {}
    prediction_summaries: list[dict[str, Any]] = []
    for model_name, path in model_paths.items():
        pipeline = joblib.load(path)
        predictions = pd.Series(pipeline.predict(split.X_test), index=split.y_test.index)
        class_table = class_metrics_table(split.y_test, predictions, label_order)
        class_tables[model_name] = class_table
        class_table.to_csv(metrics_dir / f"{run_id}_{model_name}_class_metrics.csv", index=False)

        normalized_matrix = confusion_matrix(
            split.y_test,
            predictions,
            labels=label_order,
            normalize="true",
        )
        save_normalized_confusion_matrix(
            normalized_matrix,
            label_order,
            f"Normalized Confusion Matrix - {model_name}",
            figures_dir / f"{run_id}_{model_name}_normalized_confusion_matrix.png",
        )

        prediction_summaries.append(
            {
                "model_name": model_name,
                "prediction_distribution": _prediction_distribution(predictions),
            }
        )

    feature_importance_path = metrics_dir / f"{run_id}_{summary['best_model_name']}_feature_importance.csv"
    feature_importance_df = pd.read_csv(feature_importance_path)
    aggregated_importance_df = aggregate_feature_importance(feature_importance_df)
    aggregated_importance_df.to_csv(
        metrics_dir / f"{run_id}_{summary['best_model_name']}_feature_importance_aggregated.csv",
        index=False,
    )
    univariate_df = univariate_numeric_scores(split.X_train, split.y_train)
    univariate_df.to_csv(metrics_dir / f"{run_id}_univariate_numeric_scores.csv", index=False)

    numeric_summary_df = numeric_feature_summary(split.X_train, split.y_train)
    numeric_summary_df.to_csv(metrics_dir / f"{run_id}_numeric_feature_summary.csv", index=False)

    redundancy_df = correlated_feature_pairs(split.X_train, threshold=0.9)
    redundancy_df.to_csv(metrics_dir / f"{run_id}_redundant_feature_pairs.csv", index=False)

    low_utility_df = low_utility_features(
        aggregated_importance_df.rename(columns={"raw_feature": "feature"}),
        univariate_df,
    )
    low_utility_df.to_csv(metrics_dir / f"{run_id}_low_utility_features.csv", index=False)

    top_features = univariate_df.head(int(config["diagnostics"]["top_features"]))["feature"].tolist()
    save_feature_boxplots(
        labelled_df,
        config["dataset"]["derived_target"]["label_name"],
        top_features[:6],
        figures_dir / f"{run_id}_top_numeric_boxplots.png",
    )
    save_feature_scatter(
        labelled_df,
        config["dataset"]["derived_target"]["label_name"],
        top_features[:2],
        figures_dir / f"{run_id}_top_feature_scatter.png",
    )
    save_correlation_heatmap(
        split.X_train.select_dtypes(include=["number"]),
        figures_dir / f"{run_id}_numeric_correlation_heatmap.png",
    )

    class_separation_df = class_separation_snapshot(split.X_train, split.y_train, top_features[:5])
    class_separation_df.to_csv(metrics_dir / f"{run_id}_class_separation_snapshot.csv", index=False)

    walk_forward_df = walk_forward_evaluation(X, y, timestamps, config)
    walk_forward_df.to_csv(metrics_dir / f"{run_id}_walk_forward_metrics.csv", index=False)
    save_metric_by_fold(
        walk_forward_df.dropna(subset=["f1_macro"]),
        "f1_macro",
        figures_dir / f"{run_id}_walk_forward_f1_macro.png",
    )

    best_class_diag_df = class_tables[summary["best_model_name"]]
    markdown = build_markdown_report(
        run_id=run_id,
        summary=summary,
        target_audit_df=target_audit_df,
        best_class_diag_df=best_class_diag_df,
        feature_importance_df=aggregated_importance_df.rename(columns={"raw_feature": "feature"}),
        univariate_df=univariate_df,
        redundancy_df=redundancy_df,
        walk_forward_df=walk_forward_df,
    )
    report_path = reports_dir / f"{run_id}_diagnostic_report.md"
    write_report(markdown, report_path)

    diagnostics_summary = {
        "run_id": run_id,
        "report_path": str(report_path),
        "target_audit_path": str(metrics_dir / f"{run_id}_target_audit.csv"),
        "walk_forward_path": str(metrics_dir / f"{run_id}_walk_forward_metrics.csv"),
        "class_metric_paths": {
            model_name: str(metrics_dir / f"{run_id}_{model_name}_class_metrics.csv")
            for model_name in class_tables.keys()
        },
        "prediction_summaries": prediction_summaries,
        "best_model_name": summary["best_model_name"],
        "failed_models": summary.get("failed_models", {}),
    }
    write_json(diagnostics_summary, reports_dir / f"{run_id}_diagnostic_summary.json")
    LOGGER.info("Diagnostics completed for %s", run_id)
    return diagnostics_summary
