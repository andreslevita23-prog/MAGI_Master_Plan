"""Phase 3 orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.io import load_dataset
from src.features.engineering import normalize_dataframe
from src.phase3.comparison import run_comparison_scenarios
from src.phase3.reporting import (
    build_phase3_report,
    choose_recommended_configuration,
    write_phase3_report,
)
from src.phase3.target_search import evaluate_target_grid, select_target_candidates
from src.utils import ensure_dir, get_logger, write_json
from src.visualization.phase3_plots import (
    save_candidate_comparison,
    save_feature_count_comparison,
    save_target_grid_heatmap,
    save_walk_forward_scenario_plot,
)


LOGGER = get_logger("baltasar.phase3")


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


def run_phase3(config: dict[str, Any], project_root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Run the phase 3 redesign experiments and recommend Baltasar v1.1."""
    artifacts_cfg = config["artifacts"]
    metrics_dir = ensure_dir(project_root / artifacts_cfg["metrics_dir"])
    figures_dir = ensure_dir(project_root / artifacts_cfg["figures_dir"])
    reports_dir = ensure_dir(project_root / artifacts_cfg["reports_dir"])
    models_dir = ensure_dir(project_root / artifacts_cfg["models_dir"])

    summary = _load_summary(metrics_dir, run_id)
    run_id = summary["run_id"]
    LOGGER.info("Running phase 3 experiments for %s", run_id)

    raw_df = load_dataset(config, project_root)
    normalized_raw_df = normalize_dataframe(raw_df, config)

    target_grid_df = evaluate_target_grid(normalized_raw_df, config)
    target_grid_path = metrics_dir / f"{run_id}_phase3_target_grid.csv"
    target_grid_df.to_csv(target_grid_path, index=False)

    candidates_df = select_target_candidates(target_grid_df, config)
    candidates_path = metrics_dir / f"{run_id}_phase3_target_candidates.csv"
    candidates_df.to_csv(candidates_path, index=False)
    best_candidate = candidates_df.iloc[0]

    comparison_df, class_tables, feature_tables, walk_tables = run_comparison_scenarios(
        normalized_raw_df,
        config,
        best_candidate,
        models_dir=models_dir,
        metrics_dir=metrics_dir,
    )
    comparison_path = metrics_dir / f"{run_id}_phase3_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False)

    recommended_row = choose_recommended_configuration(comparison_df)
    report_markdown = build_phase3_report(
        run_id=run_id,
        target_grid_df=target_grid_df,
        candidate_targets_df=candidates_df,
        comparison_df=comparison_df,
        recommended_row=recommended_row,
    )
    report_path = reports_dir / f"{run_id}_phase3_report.md"
    write_phase3_report(report_markdown, report_path)

    save_target_grid_heatmap(target_grid_df, "f1_macro", figures_dir / f"{run_id}_phase3_target_grid_f1.png")
    save_target_grid_heatmap(
        target_grid_df,
        "walk_forward_f1_mean",
        figures_dir / f"{run_id}_phase3_target_grid_walk_mean.png",
    )
    save_target_grid_heatmap(
        target_grid_df,
        "imbalance_ratio",
        figures_dir / f"{run_id}_phase3_target_grid_imbalance.png",
    )
    save_candidate_comparison(comparison_df, figures_dir / f"{run_id}_phase3_scenario_comparison.png")
    save_feature_count_comparison(comparison_df, figures_dir / f"{run_id}_phase3_feature_counts.png")
    for scenario_name, walk_df in walk_tables.items():
        save_walk_forward_scenario_plot(
            walk_df,
            scenario_name,
            figures_dir / f"{run_id}_{scenario_name}_walk_forward.png",
        )

    phase3_summary = {
        "run_id": run_id,
        "target_grid_path": str(target_grid_path),
        "target_candidates_path": str(candidates_path),
        "comparison_path": str(comparison_path),
        "report_path": str(report_path),
        "recommended_configuration": recommended_row.to_dict(),
        "candidate_targets": candidates_df.to_dict(orient="records"),
        "class_metric_keys": list(class_tables.keys()),
        "feature_table_keys": list(feature_tables.keys()),
    }
    write_json(phase3_summary, reports_dir / f"{run_id}_phase3_summary.json")
    LOGGER.info("Phase 3 completed for %s. Recommended base: %s", run_id, recommended_row["scenario_name"])
    return phase3_summary
