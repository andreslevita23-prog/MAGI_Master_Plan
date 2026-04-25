"""Local dashboard for Baltasar training runs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "experiment.yaml"


@st.cache_data
def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


@st.cache_data
def list_run_summaries() -> list[Path]:
    metrics_dir = PROJECT_ROOT / "artifacts" / "metrics"
    return sorted(metrics_dir.glob("*_run_summary.json"), reverse=True)


@st.cache_data
def load_summary(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data
def load_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data
def load_optional_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


@st.cache_data
def load_optional_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def render_figure_if_exists(path: Path, caption: str) -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"Figure not found: {path.name}")


def main() -> None:
    config = load_config()
    st.set_page_config(page_title="Baltasar Training Lab", layout="wide")
    st.title(config["dashboard"]["title"])
    st.caption("Laboratorio local de entrenamiento, validacion y revision de Baltasar.")

    summaries = list_run_summaries()
    if not summaries:
        st.warning("No runs found yet. Execute run_experiment.py first.")
        return

    selected_path = st.sidebar.selectbox(
        "Run summary",
        summaries,
        format_func=lambda path: path.stem.replace("_run_summary", ""),
    )
    summary = load_summary(selected_path)
    run_id = summary["run_id"]
    figures_dir = PROJECT_ROOT / "artifacts" / "figures"
    metrics_dir = PROJECT_ROOT / "artifacts" / "metrics"
    reports_dir = PROJECT_ROOT / "artifacts" / "reports"
    diagnostic_summary = load_optional_json(reports_dir / f"{run_id}_diagnostic_summary.json")
    diagnostic_report = load_optional_text(reports_dir / f"{run_id}_diagnostic_report.md")
    phase3_summary = load_optional_json(reports_dir / f"{run_id}_phase3_summary.json")
    phase3_report = load_optional_text(reports_dir / f"{run_id}_phase3_report.md")
    official_summary = load_optional_json(reports_dir / "baltasar_v12_consolidation_summary.json")
    official_report = load_optional_text(reports_dir / "baltasar_v12_consolidation.md")
    v12_training_summary = load_optional_json(reports_dir / "baltasar_v12_training_summary.json")
    v12_training_report = load_optional_text(reports_dir / "baltasar_v12_training_report.md")

    st.sidebar.markdown("### Run info")
    st.sidebar.write(f"Run ID: `{run_id}`")
    st.sidebar.write(f"Best model: `{summary['best_model_name']}`")
    st.sidebar.write(f"Diagnostics: `{'available' if diagnostic_summary else 'missing'}`")
    st.sidebar.write(f"Phase 3: `{'available' if phase3_summary else 'missing'}`")
    st.sidebar.write(f"Official v1.2: `{'available' if official_summary else 'missing'}`")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", summary["dataset_summary"]["rows"])
    col2.metric("Features", summary["dataset_summary"]["feature_count"])
    col3.metric("Train Rows", summary["split_summary"]["train_rows"])
    col4.metric("Test Rows", summary["split_summary"]["test_rows"])

    st.subheader("Dataset Summary")
    dataset_summary = summary["dataset_summary"]
    split_summary = summary["split_summary"]

    left, right = st.columns(2)
    with left:
        st.json(
            {
                "timestamp_min": dataset_summary["timestamp_min"],
                "timestamp_max": dataset_summary["timestamp_max"],
                "target_distribution": dataset_summary["target_distribution"],
            }
        )
    with right:
        st.json(
            {
                "split_method": split_summary["method"],
                "train_window": [split_summary["train_start"], split_summary["train_end"]],
                "test_window": [split_summary["test_start"], split_summary["test_end"]],
            }
        )

    st.subheader("Features Used")
    st.dataframe(pd.DataFrame({"feature": dataset_summary["feature_columns"]}), use_container_width=True)

    st.subheader("Baltasar v1.2 Official Baseline")
    if not official_summary:
        st.info(
            "Run `python run_baltasar_v12.py --config config/experiment.yaml` and "
            "`python run_phase6_consolidation.py --config config/experiment.yaml` to consolidate the official baseline."
        )
    else:
        if official_report:
            st.markdown(official_report)

        official_baseline_cfg = config.get("official_baseline", {})
        cols = st.columns(4)
        cols[0].metric("Version", official_baseline_cfg.get("version", "n/a"))
        cols[1].metric("Target", official_baseline_cfg.get("target_name", "n/a"))
        cols[2].metric("Features", official_baseline_cfg.get("feature_variant", "n/a"))
        cols[3].metric("Baseline Model", official_baseline_cfg.get("baseline_model", "n/a"))

        benchmark_df = load_optional_csv(metrics_dir / "official_v12_benchmark.csv")
        if benchmark_df is not None:
            st.write("Official benchmark")
            st.dataframe(benchmark_df, use_container_width=True)

        baseline_class_df = load_optional_csv(metrics_dir / "baltasar_v12_random_forest_class_metrics.csv")
        challenger_class_df = load_optional_csv(metrics_dir / "baltasar_v12_baseline_tree_class_metrics.csv")
        left, right = st.columns(2)
        with left:
            st.write("Official baseline metrics by class")
            if baseline_class_df is not None:
                st.dataframe(baseline_class_df, use_container_width=True)
        with right:
            st.write("Explanatory reference metrics by class")
            if challenger_class_df is not None:
                st.dataframe(challenger_class_df, use_container_width=True)

        v12_metrics_df = load_optional_csv(metrics_dir / "baltasar_v12_metrics.csv")
        if v12_metrics_df is not None:
            st.write("Official v1.2 model metrics")
            st.dataframe(v12_metrics_df, use_container_width=True)

        if v12_training_summary:
            st.write("Target distribution on the extended dataset")
            st.json(v12_training_summary.get("target_distribution", {}))

        rationale = official_baseline_cfg.get("rationale", [])
        if rationale:
            st.write("Trade-off summary")
            for item in rationale:
                st.write(f"- {item}")

        left, right = st.columns(2)
        with left:
            render_figure_if_exists(figures_dir / "baltasar_v12_vs_v11.png", "Baltasar v1.1 vs v1.2")
        with right:
            render_figure_if_exists(figures_dir / "baltasar_v12_walk_forward.png", "Baltasar v1.2 walk-forward")

        left, right = st.columns(2)
        with left:
            render_figure_if_exists(
                figures_dir / "baltasar_v12_random_forest_confusion_matrix.png",
                "Official baseline confusion matrix",
            )
        with right:
            render_figure_if_exists(
                figures_dir / "baltasar_v12_baseline_tree_confusion_matrix.png",
                "Explanatory reference confusion matrix",
            )

        render_figure_if_exists(
            figures_dir / "baltasar_v12_target_distribution.png",
            "Baltasar v1.2 target distribution",
        )

        if v12_training_report:
            with st.expander("Baltasar v1.2 training report"):
                st.markdown(v12_training_report)

    st.subheader("Run Parameters")
    st.json(summary["config_snapshot"])

    st.subheader("Model Comparison")
    comparison_df = pd.DataFrame(summary["comparison"])
    st.dataframe(comparison_df, use_container_width=True)
    render_figure_if_exists(figures_dir / f"{run_id}_model_comparison.png", "Model comparison")

    failed_models = summary.get("failed_models", {})
    if failed_models:
        st.subheader("Failed Models")
        st.dataframe(
            pd.DataFrame(
                [{"model_name": model_name, "error": error} for model_name, error in failed_models.items()]
            ),
            use_container_width=True,
        )

    st.subheader("Per-model Review")
    model_names = list(summary["models"].keys())
    default_model = config.get("dashboard", {}).get("default_model")
    default_index = model_names.index(default_model) if default_model in model_names else 0
    model_name = st.selectbox("Model", model_names, index=default_index)
    model_metrics = summary["models"][model_name]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Accuracy", f"{model_metrics['accuracy']:.4f}")
    metric_cols[1].metric("Precision Macro", f"{model_metrics['precision_macro']:.4f}")
    metric_cols[2].metric("Recall Macro", f"{model_metrics['recall_macro']:.4f}")
    metric_cols[3].metric("F1 Macro", f"{model_metrics['f1_macro']:.4f}")

    st.write("F1 by class")
    st.dataframe(
        pd.DataFrame(
            {
                "label": list(model_metrics["f1_by_class"].keys()),
                "f1": list(model_metrics["f1_by_class"].values()),
                "support": [model_metrics["support_by_class"][key] for key in model_metrics["f1_by_class"].keys()],
            }
        ),
        use_container_width=True,
    )
    class_metrics_path = metrics_dir / f"{run_id}_{model_name}_class_metrics.csv"
    class_metrics_df = load_optional_csv(class_metrics_path)
    if class_metrics_df is not None:
        st.write("Detailed metrics by class")
        st.dataframe(class_metrics_df, use_container_width=True)

    confusion_path = figures_dir / f"{run_id}_{model_name}_confusion_matrix.png"
    normalized_confusion_path = figures_dir / f"{run_id}_{model_name}_normalized_confusion_matrix.png"
    importance_path = figures_dir / f"{run_id}_{model_name}_feature_importance.png"
    importance_csv = metrics_dir / f"{run_id}_{model_name}_feature_importance.csv"

    left, middle, right = st.columns(3)
    with left:
        render_figure_if_exists(confusion_path, f"Confusion matrix - {model_name}")
    with middle:
        render_figure_if_exists(normalized_confusion_path, f"Normalized confusion - {model_name}")
    with right:
        render_figure_if_exists(importance_path, f"Feature importance - {model_name}")

    if importance_csv.exists():
        st.write("Feature importance table")
        st.dataframe(pd.read_csv(importance_csv).head(25), use_container_width=True)

    st.subheader("Validation Report")
    st.json(summary["validation"])

    history_file = PROJECT_ROOT / "artifacts" / "metrics" / "run_history.csv"
    st.subheader("Best Historical Run")
    if history_file.exists():
        history = pd.read_csv(history_file)
        best_history = history.sort_values("f1_macro", ascending=False).head(1)
        st.dataframe(best_history, use_container_width=True)
    else:
        st.info("No run history found yet.")

    st.subheader("General Figures")
    left, right = st.columns(2)
    with left:
        render_figure_if_exists(figures_dir / f"{run_id}_target_distribution.png", "Target distribution")
    with right:
        render_figure_if_exists(figures_dir / f"{run_id}_missing_ratio.png", "Missing ratio")

    st.subheader("Diagnostic Phase")
    if not diagnostic_summary:
        st.info("Run `python run_diagnostics.py --config config/experiment.yaml` to populate diagnostic outputs.")
    else:
        if diagnostic_report:
            st.markdown(diagnostic_report)

        target_audit_df = load_optional_csv(metrics_dir / f"{run_id}_target_audit.csv")
        if target_audit_df is not None:
            st.write("Target audit")
            st.dataframe(target_audit_df, use_container_width=True)
            left, right = st.columns(2)
            with left:
                render_figure_if_exists(
                    figures_dir / f"{run_id}_target_sensitivity.png",
                    "Target sensitivity",
                )
            with right:
                render_figure_if_exists(
                    figures_dir / f"{run_id}_target_distribution_comparison.png",
                    "Target distribution comparison",
                )

        walk_forward_df = load_optional_csv(metrics_dir / f"{run_id}_walk_forward_metrics.csv")
        if walk_forward_df is not None:
            st.write("Walk-forward validation")
            st.dataframe(walk_forward_df, use_container_width=True)
            render_figure_if_exists(
                figures_dir / f"{run_id}_walk_forward_f1_macro.png",
                "Walk-forward F1 macro",
            )

        left, right = st.columns(2)
        with left:
            render_figure_if_exists(
                figures_dir / f"{run_id}_top_numeric_boxplots.png",
                "Top numeric feature boxplots",
            )
        with right:
            render_figure_if_exists(
                figures_dir / f"{run_id}_top_feature_scatter.png",
                "Top feature scatter",
            )

        render_figure_if_exists(
            figures_dir / f"{run_id}_numeric_correlation_heatmap.png",
            "Numeric feature correlation heatmap",
        )

        univariate_df = load_optional_csv(metrics_dir / f"{run_id}_univariate_numeric_scores.csv")
        if univariate_df is not None:
            st.write("Univariate numeric scores")
            st.dataframe(univariate_df.head(20), use_container_width=True)

        aggregated_importance_df = load_optional_csv(
            metrics_dir / f"{run_id}_{summary['best_model_name']}_feature_importance_aggregated.csv"
        )
        if aggregated_importance_df is not None:
            st.write("Aggregated feature importance")
            st.dataframe(aggregated_importance_df.head(20), use_container_width=True)

        low_utility_df = load_optional_csv(metrics_dir / f"{run_id}_low_utility_features.csv")
        if low_utility_df is not None:
            st.write("Potentially low-utility features")
            st.dataframe(low_utility_df, use_container_width=True)

        redundancy_df = load_optional_csv(metrics_dir / f"{run_id}_redundant_feature_pairs.csv")
        if redundancy_df is not None and not redundancy_df.empty:
            st.write("Highly correlated feature pairs")
            st.dataframe(redundancy_df.head(20), use_container_width=True)

        if diagnostic_summary.get("prediction_summaries"):
            st.write("Prediction distribution by model")
            prediction_rows = []
            for item in diagnostic_summary["prediction_summaries"]:
                row = {"model_name": item["model_name"]}
                row.update(item["prediction_distribution"])
                prediction_rows.append(row)
            st.dataframe(pd.DataFrame(prediction_rows), use_container_width=True)

    st.subheader("Phase 3 Redesign")
    if not phase3_summary:
        st.info("Run `python run_phase3.py --config config/experiment.yaml` to generate Baltasar v1.1 recommendations.")
    else:
        if phase3_report:
            st.markdown(phase3_report)

        recommended = phase3_summary.get("recommended_configuration", {})
        if recommended:
            cols = st.columns(4)
            cols[0].metric("Recommended Scenario", recommended.get("scenario_name", "n/a"))
            cols[1].metric("Target", recommended.get("target_name", "n/a"))
            cols[2].metric("Feature Variant", recommended.get("feature_variant", "n/a"))
            cols[3].metric("WF F1 Mean", f"{recommended.get('walk_forward_f1_mean', 0):.4f}")

        target_grid_df = load_optional_csv(metrics_dir / f"{run_id}_phase3_target_grid.csv")
        if target_grid_df is not None:
            st.write("Systematic target grid")
            st.dataframe(target_grid_df, use_container_width=True)
            left, middle, right = st.columns(3)
            with left:
                render_figure_if_exists(
                    figures_dir / f"{run_id}_phase3_target_grid_f1.png",
                    "Target grid F1",
                )
            with middle:
                render_figure_if_exists(
                    figures_dir / f"{run_id}_phase3_target_grid_walk_mean.png",
                    "Target grid walk-forward mean",
                )
            with right:
                render_figure_if_exists(
                    figures_dir / f"{run_id}_phase3_target_grid_imbalance.png",
                    "Target grid imbalance",
                )

        candidates_df = load_optional_csv(metrics_dir / f"{run_id}_phase3_target_candidates.csv")
        if candidates_df is not None:
            st.write("Target candidates")
            st.dataframe(candidates_df, use_container_width=True)

        comparison_df = load_optional_csv(metrics_dir / f"{run_id}_phase3_comparison.csv")
        if comparison_df is not None:
            st.write("Scenario comparison")
            st.dataframe(comparison_df, use_container_width=True)
            left, right = st.columns(2)
            with left:
                render_figure_if_exists(
                    figures_dir / f"{run_id}_phase3_scenario_comparison.png",
                    "Scenario comparison",
                )
            with right:
                render_figure_if_exists(
                    figures_dir / f"{run_id}_phase3_feature_counts.png",
                    "Feature counts",
                )

            selected_phase3_scenario = st.selectbox(
                "Phase 3 walk-forward scenario",
                comparison_df["scenario_name"].drop_duplicates().tolist(),
            )
            render_figure_if_exists(
                figures_dir / f"{run_id}_{selected_phase3_scenario}_walk_forward.png",
                f"Walk-forward - {selected_phase3_scenario}",
            )


if __name__ == "__main__":
    main()
