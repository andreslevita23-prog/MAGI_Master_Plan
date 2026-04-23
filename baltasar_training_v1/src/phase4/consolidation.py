"""Official baseline consolidation for Baltasar v1.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils import ensure_dir, get_logger, write_json


LOGGER = get_logger("baltasar.phase4")


def _latest_phase3_summary(reports_dir: Path) -> Path:
    summaries = sorted(reports_dir.glob("*_phase3_summary.json"))
    if not summaries:
        raise FileNotFoundError("No phase 3 summary found. Execute run_phase3.py first.")
    return summaries[-1]


def _load_phase3_summary(reports_dir: Path, run_id: str | None) -> dict[str, Any]:
    if run_id:
        summary_path = reports_dir / f"{run_id}_phase3_summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"Phase 3 summary not found for run_id={run_id}.")
    else:
        summary_path = _latest_phase3_summary(reports_dir)
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _official_tradeoff_summary(baseline_row: pd.Series, challenger_row: pd.Series) -> str:
    return (
        f"Baseline chosen: {baseline_row['model_name']} with holdout F1 {_fmt(baseline_row['f1_macro'])}, "
        f"walk-forward mean {_fmt(baseline_row['walk_forward_f1_mean'])} and std {_fmt(baseline_row['walk_forward_f1_std'])}. "
        f"Challenger {challenger_row['model_name']} reaches higher point F1 {_fmt(challenger_row['f1_macro'])} and higher "
        f"walk-forward mean {_fmt(challenger_row['walk_forward_f1_mean'])}, but with materially higher dispersion "
        f"({_fmt(challenger_row['walk_forward_f1_std'])}), so it remains a challenger rather than the official baseline."
    )


def _fmt(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.4f}"


def build_official_report(
    config: dict[str, Any],
    run_id: str,
    benchmark_df: pd.DataFrame,
    baseline_class_df: pd.DataFrame,
    challenger_class_df: pd.DataFrame,
    compact_feature_importance_df: pd.DataFrame,
) -> str:
    """Create the official consolidation report."""
    official_cfg = config["official_baseline"]
    baseline_row = benchmark_df[benchmark_df["role"] == "official_baseline"].iloc[0]
    challenger_row = benchmark_df[benchmark_df["role"] == "challenger"].iloc[0]
    top_features = compact_feature_importance_df.head(8)["feature"].tolist()

    return f"""# Baltasar v1.1 Official Consolidation Report

## Official Status

- Version: `{official_cfg['version']}`
- Reference run: `{run_id}`
- Official target: `{official_cfg['target_name']}`
- Official feature variant: `{official_cfg['feature_variant']}`
- Official baseline model: `{official_cfg['baseline_model']}`
- Official challenger: `{official_cfg['challenger_model']}`

## Why v1.1 Was Promoted

- The target redesign improved balance and signal relative to the old `h12_t08` default.
- The compact feature variant reduced the working feature set while preserving informative relative-price structure.
- The official baseline was not chosen by best point F1 alone. Stability and explainability carried more weight.

## Official Benchmark

{benchmark_df.to_string(index=False)}

## Metrics by Class

Official baseline:

{baseline_class_df.to_string(index=False)}

Official challenger:

{challenger_class_df.to_string(index=False)}

## Trade-off Chosen

{_official_tradeoff_summary(baseline_row, challenger_row)}

## Compact Features Selected

- {", ".join(top_features)}

## Why Not the Highest F1 Point Model

- `random_forest` on compact features performed better on point metrics.
- It showed noticeably worse temporal stability.
- For Baltasar v1.1, the laboratory prioritizes a baseline that is easier to explain, easier to track and less sensitive across market tramos.

## Pending for Future Phases

1. Re-run full training flows using v1.1 defaults as the normal path.
2. Decide whether challenger promotion should require a minimum stability threshold.
3. Evaluate calibration, cost-sensitive learning and label redesign refinements in later phases.
4. Prepare executive-facing storytelling and visuals without altering the technical baseline.
"""


def run_phase4_consolidation(config: dict[str, Any], project_root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Create the official benchmark and consolidation report for Baltasar v1.1."""
    artifacts_cfg = config["artifacts"]
    metrics_dir = ensure_dir(project_root / artifacts_cfg["metrics_dir"])
    reports_dir = ensure_dir(project_root / artifacts_cfg["reports_dir"])
    official_cfg = config["official_baseline"]

    phase3_summary = _load_phase3_summary(reports_dir, run_id)
    run_id = phase3_summary["run_id"]
    LOGGER.info("Consolidating official baseline for %s", run_id)

    comparison_df = pd.read_csv(metrics_dir / f"{run_id}_phase3_comparison.csv")
    baseline_row = comparison_df[
        (comparison_df["scenario_name"] == "candidate_target_compact_features")
        & (comparison_df["model_name"] == official_cfg["baseline_model"])
    ].iloc[0]
    challenger_row = comparison_df[
        (comparison_df["scenario_name"] == "candidate_target_compact_features")
        & (comparison_df["model_name"] == official_cfg["challenger_model"])
    ].iloc[0]

    baseline_class_df = pd.read_csv(
        metrics_dir / f"candidate_target_compact_features__{official_cfg['baseline_model']}_class_metrics.csv"
    )
    challenger_class_df = pd.read_csv(
        metrics_dir / f"candidate_target_compact_features__{official_cfg['challenger_model']}_class_metrics.csv"
    )
    compact_feature_importance_df = pd.read_csv(
        metrics_dir / f"candidate_target_compact_features__{official_cfg['baseline_model']}_feature_importance.csv"
    )

    benchmark_records = [
        {
            "role": "official_baseline",
            "version": official_cfg["version"],
            "scenario_name": baseline_row["scenario_name"],
            "target_name": baseline_row["target_name"],
            "feature_variant": baseline_row["feature_variant"],
            "model_name": baseline_row["model_name"],
            "feature_count": int(baseline_row["feature_count"]),
            "accuracy": float(baseline_row["accuracy"]),
            "f1_macro": float(baseline_row["f1_macro"]),
            "walk_forward_f1_mean": float(baseline_row["walk_forward_f1_mean"]),
            "walk_forward_f1_std": float(baseline_row["walk_forward_f1_std"]),
            "trade_off": "Chosen for higher temporal stability and clearer interpretability.",
        },
        {
            "role": "challenger",
            "version": official_cfg["version"],
            "scenario_name": challenger_row["scenario_name"],
            "target_name": challenger_row["target_name"],
            "feature_variant": challenger_row["feature_variant"],
            "model_name": challenger_row["model_name"],
            "feature_count": int(challenger_row["feature_count"]),
            "accuracy": float(challenger_row["accuracy"]),
            "f1_macro": float(challenger_row["f1_macro"]),
            "walk_forward_f1_mean": float(challenger_row["walk_forward_f1_mean"]),
            "walk_forward_f1_std": float(challenger_row["walk_forward_f1_std"]),
            "trade_off": "Kept as challenger due to stronger point metrics but weaker stability.",
        },
    ]
    benchmark_df = pd.DataFrame(benchmark_records)
    benchmark_path = metrics_dir / f"{run_id}_official_v11_benchmark.csv"
    benchmark_df.to_csv(benchmark_path, index=False)

    report_markdown = build_official_report(
        config=config,
        run_id=run_id,
        benchmark_df=benchmark_df,
        baseline_class_df=baseline_class_df,
        challenger_class_df=challenger_class_df,
        compact_feature_importance_df=compact_feature_importance_df,
    )
    report_path = reports_dir / f"{run_id}_official_v11_consolidation.md"
    report_path.write_text(report_markdown, encoding="utf-8")

    summary = {
        "run_id": run_id,
        "version": official_cfg["version"],
        "benchmark_path": str(benchmark_path),
        "report_path": str(report_path),
        "official_baseline": benchmark_records[0],
        "challenger": benchmark_records[1],
        "compact_feature_importance_path": str(
            metrics_dir / f"candidate_target_compact_features__{official_cfg['baseline_model']}_feature_importance.csv"
        ),
        "baseline_class_metrics_path": str(
            metrics_dir / f"candidate_target_compact_features__{official_cfg['baseline_model']}_class_metrics.csv"
        ),
        "challenger_class_metrics_path": str(
            metrics_dir / f"candidate_target_compact_features__{official_cfg['challenger_model']}_class_metrics.csv"
        ),
    }
    write_json(summary, reports_dir / f"{run_id}_official_v11_summary.json")
    LOGGER.info("Official Baltasar v1.1 baseline consolidated.")
    return summary
