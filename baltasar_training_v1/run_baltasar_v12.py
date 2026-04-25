"""Train and evaluate Baltasar v1.2 on the extended dataset."""

from pathlib import Path

import pandas as pd

from src.config import load_config
from src.phase6.reporting import build_v12_report, write_report
from src.phase6.v12_training import build_v12_config, run_v12_training
from src.utils import ensure_dir, write_json
from src.visualization.phase6_plots import save_v11_v12_comparison, save_walk_forward_plot
from src.visualization.plots import save_confusion_matrix, save_target_distribution


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run Baltasar v1.2 on the extended dataset.")
    parser.add_argument(
        "--config",
        type=str,
        default="config/experiment.yaml",
        help="Path to experiment YAML config.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    project_root = config_path.resolve().parent.parent
    config = load_config(config_path)
    config["_project_root"] = str(project_root)

    artifacts_cfg = config["artifacts"]
    metrics_dir = ensure_dir(project_root / artifacts_cfg["metrics_dir"])
    figures_dir = ensure_dir(project_root / artifacts_cfg["figures_dir"])
    reports_dir = ensure_dir(project_root / artifacts_cfg["reports_dir"])

    results = run_v12_training(config)
    metrics_df = results["metrics_df"].copy()

    v11_benchmark = pd.read_csv(metrics_dir / "20260422T235032Z_official_v11_benchmark.csv")
    v11_metrics = v11_benchmark[["version", "model_name", "accuracy", "f1_macro", "walk_forward_f1_mean", "walk_forward_f1_std"]]
    comparison_df = pd.concat(
        [
            v11_metrics,
            metrics_df[["version", "model_name", "accuracy", "f1_macro", "walk_forward_f1_mean", "walk_forward_f1_std"]],
        ],
        ignore_index=True,
    )

    baltasar_v12_metrics = metrics_df.copy()
    baltasar_v12_metrics.to_csv(metrics_dir / "baltasar_v12_metrics.csv", index=False)
    comparison_df.to_csv(metrics_dir / "baltasar_v12_vs_v11.csv", index=False)

    for model_name, class_df in results["class_tables"].items():
        class_df.to_csv(metrics_dir / f"baltasar_v12_{model_name}_class_metrics.csv", index=False)
    results["walk_forward_df"].to_csv(metrics_dir / "baltasar_v12_walk_forward.csv", index=False)

    report = build_v12_report(
        dataset_summary=results["dataset_selection"],
        quick_checks=results["quick_checks"],
        validation_report=results["validation_report"],
        metrics_df=metrics_df,
        class_tables=results["class_tables"],
        comparison_df=comparison_df,
    )
    write_report(report, reports_dir / "baltasar_v12_training_report.md")

    target_distribution = pd.Series(results["target_distribution"])
    save_target_distribution(target_distribution, figures_dir / "baltasar_v12_target_distribution.png")
    for model_name, matrix in results["confusion_matrices"].items():
        save_confusion_matrix(
            matrix,
            config["dataset"]["label_order"],
            f"Baltasar v1.2 Confusion Matrix - {model_name}",
            figures_dir / f"baltasar_v12_{model_name}_confusion_matrix.png",
        )
    save_walk_forward_plot(results["walk_forward_df"], figures_dir / "baltasar_v12_walk_forward.png")
    save_v11_v12_comparison(comparison_df, figures_dir / "baltasar_v12_vs_v11.png")

    write_json(
        {
            "dataset_selection": results["dataset_selection"],
            "validation_report": results["validation_report"],
            "quick_checks": results["quick_checks"],
            "target_distribution": results["target_distribution"],
            "metrics": metrics_df.to_dict(orient="records"),
            "comparison": comparison_df.to_dict(orient="records"),
        },
        reports_dir / "baltasar_v12_training_summary.json",
    )


if __name__ == "__main__":
    main()
