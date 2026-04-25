"""Training pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from pandas.api.types import is_bool_dtype, is_object_dtype, is_string_dtype
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.data.io import load_dataset
from src.data.validation import validate_dataset
from src.evaluation.metrics import compute_model_metrics, metrics_table
from src.features.engineering import build_feature_frame, normalize_dataframe
from src.features.targeting import prepare_target
from src.models.registry import build_model
from src.utils import ensure_dir, get_logger, utc_run_id, write_json
from src.visualization.plots import (
    save_confusion_matrix,
    save_feature_importance,
    save_missing_ratio,
    save_model_comparison,
    save_target_distribution,
)


LOGGER = get_logger("baltasar.training")


@dataclass
class SplitData:
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    timestamps_train: pd.Series
    timestamps_test: pd.Series


def build_preprocessor(X: pd.DataFrame, config: dict[str, Any]) -> ColumnTransformer:
    """Build a preprocessing step safe for tree-based estimators."""
    configured_categorical = set(config["dataset"].get("categorical_columns", []))
    detected_categorical = set(
        X.select_dtypes(include=["object", "category", "bool", "string"]).columns.tolist()
    )
    categorical_columns = []
    for column in X.columns:
        series = X[column]
        if (
            column in configured_categorical
            or column in detected_categorical
            or is_object_dtype(series)
            or is_string_dtype(series)
            or is_bool_dtype(series)
        ):
            categorical_columns.append(column)

    numeric_columns = [column for column in X.columns if column not in categorical_columns]

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="constant",
                                fill_value=0.0,
                                keep_empty_features=True,
                            ),
                        )
                    ]
                ),
                numeric_columns,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical_columns,
            ),
        ]
    )


def temporal_split(
    X: pd.DataFrame,
    y: pd.Series,
    timestamps: pd.Series,
    test_size: float,
) -> SplitData:
    """Split without breaking temporal order."""
    split_index = int(len(X) * (1 - test_size))
    return SplitData(
        X_train=X.iloc[:split_index].copy(),
        X_test=X.iloc[split_index:].copy(),
        y_train=y.iloc[:split_index].copy(),
        y_test=y.iloc[split_index:].copy(),
        timestamps_train=timestamps.iloc[:split_index].copy(),
        timestamps_test=timestamps.iloc[split_index:].copy(),
    )


def get_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    """Extract transformed feature names from the preprocessor."""
    return preprocessor.get_feature_names_out().tolist()


def build_model_pipeline(
    X_train: pd.DataFrame,
    config: dict[str, Any],
    model_cfg: dict[str, Any],
) -> Pipeline:
    """Create a reusable training pipeline for one configured model."""
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(X_train, config)),
            ("model", build_model(model_cfg["class_name"], model_cfg["params"])),
        ]
    )


def extract_feature_importance(
    fitted_pipeline: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    random_state: int,
) -> pd.DataFrame:
    """Return a standard feature-importance table across model types."""
    preprocessor = fitted_pipeline.named_steps["preprocessor"]
    model = fitted_pipeline.named_steps["model"]
    feature_names = get_feature_names(preprocessor)

    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    else:
        transformed_X = preprocessor.transform(X_test)
        importance = permutation_importance(
            model,
            transformed_X,
            y_test,
            n_repeats=5,
            random_state=random_state,
            scoring="f1_macro",
        )
        values = importance.importances_mean

    feature_importance = pd.DataFrame(
        {"feature": feature_names, "importance": values}
    ).sort_values("importance", ascending=False)
    return feature_importance.reset_index(drop=True)


def append_history(history_file: Path, comparison_df: pd.DataFrame, run_id: str) -> None:
    """Append the current run to the cumulative history table."""
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_row = comparison_df.copy()
    history_row.insert(0, "run_id", run_id)

    if history_file.exists():
        previous = pd.read_csv(history_file)
        combined = pd.concat([previous, history_row], ignore_index=True)
    else:
        combined = history_row

    combined.to_csv(history_file, index=False)


def run_training_experiment(config: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Execute the complete reproducible training experiment."""
    run_id = utc_run_id()
    seed = int(config["experiment"]["seed"])
    label_order = config["dataset"]["label_order"]
    artifacts_cfg = config["artifacts"]

    metrics_dir = ensure_dir(project_root / artifacts_cfg["metrics_dir"])
    models_dir = ensure_dir(project_root / artifacts_cfg["models_dir"])
    figures_dir = ensure_dir(project_root / artifacts_cfg["figures_dir"])
    processed_dir = ensure_dir(project_root / artifacts_cfg["processed_dir"])
    reports_dir = ensure_dir(project_root / artifacts_cfg["data_reports_dir"])
    history_file = project_root / artifacts_cfg["history_file"]

    LOGGER.info("Loading dataset.")
    raw_df = load_dataset(config, project_root)
    normalized_df = normalize_dataframe(raw_df, config)

    LOGGER.info("Validating dataset.")
    validation_report = validate_dataset(normalized_df, config)
    write_json(validation_report.to_dict(), reports_dir / f"{run_id}_validation_report.json")

    LOGGER.info("Preparing target and feature frame.")
    labelled_df = prepare_target(normalized_df, config)
    processed_path = processed_dir / f"{run_id}_labelled_dataset.csv"
    labelled_df.to_csv(processed_path, index=False)

    X, y, timestamps = build_feature_frame(labelled_df, config)
    split = temporal_split(X, y, timestamps, test_size=float(config["split"]["test_size"]))

    missing_ratio = labelled_df.isna().mean()
    save_target_distribution(y, figures_dir / f"{run_id}_target_distribution.png")
    save_missing_ratio(missing_ratio, figures_dir / f"{run_id}_missing_ratio.png")

    LOGGER.info("Training models.")
    fitted_models: dict[str, Pipeline] = {}
    model_metrics: dict[str, dict[str, Any]] = {}
    failed_models: dict[str, str] = {}

    for model_name, model_cfg in config["models"].items():
        if not model_cfg.get("enabled", False):
            continue

        LOGGER.info("Training %s", model_name)
        try:
            pipeline = build_model_pipeline(split.X_train, config, model_cfg)

            pipeline.fit(split.X_train, split.y_train)
            predictions = pipeline.predict(split.X_test)
            metrics = compute_model_metrics(split.y_test, predictions, label_order)

            fitted_models[model_name] = pipeline
            model_metrics[model_name] = metrics

            model_file = models_dir / f"{run_id}_{model_name}.joblib"
            joblib.dump(pipeline, model_file)

            matrix_file = figures_dir / f"{run_id}_{model_name}_confusion_matrix.png"
            save_confusion_matrix(
                metrics["confusion_matrix"],
                label_order,
                f"Confusion Matrix - {model_name}",
                matrix_file,
            )

            feature_importance = extract_feature_importance(pipeline, split.X_test, split.y_test, seed)
            feature_importance.to_csv(
                metrics_dir / f"{run_id}_{model_name}_feature_importance.csv", index=False
            )
            save_feature_importance(
                feature_importance,
                f"Feature Importance - {model_name}",
                figures_dir / f"{run_id}_{model_name}_feature_importance.png",
            )
        except Exception as error:  # pragma: no cover - resilience path
            LOGGER.exception("Model %s failed during training.", model_name)
            failed_models[model_name] = str(error)

    comparison_df = metrics_table(model_metrics)
    if comparison_df.empty:
        raise RuntimeError("No model completed training successfully.")
    comparison_df.to_csv(metrics_dir / f"{run_id}_model_comparison.csv", index=False)
    save_model_comparison(comparison_df, figures_dir / f"{run_id}_model_comparison.png")
    append_history(history_file, comparison_df, run_id)

    best_model_name = comparison_df.iloc[0]["model_name"]
    summary = {
        "run_id": run_id,
        "experiment_name": config["experiment"]["name"],
        "notes": config["experiment"].get("notes"),
        "seed": seed,
        "project_root": str(project_root),
        "processed_dataset_path": str(processed_path),
        "validation": validation_report.to_dict(),
        "dataset_summary": {
            "rows": int(labelled_df.shape[0]),
            "columns": int(labelled_df.shape[1]),
            "timestamp_min": str(timestamps.min()),
            "timestamp_max": str(timestamps.max()),
            "feature_count": int(split.X_train.shape[1]),
            "feature_columns": split.X_train.columns.tolist(),
            "target_distribution": y.value_counts().to_dict(),
        },
        "split_summary": {
            "method": config["split"]["method"],
            "train_rows": int(split.X_train.shape[0]),
            "test_rows": int(split.X_test.shape[0]),
            "train_start": str(split.timestamps_train.min()),
            "train_end": str(split.timestamps_train.max()),
            "test_start": str(split.timestamps_test.min()),
            "test_end": str(split.timestamps_test.max()),
        },
        "models": model_metrics,
        "failed_models": failed_models,
        "comparison": comparison_df.to_dict(orient="records"),
        "best_model_name": best_model_name,
        "config_snapshot": config,
    }
    write_json(summary, metrics_dir / f"{run_id}_run_summary.json")
    write_json(model_metrics, metrics_dir / f"{run_id}_metrics.json")
    LOGGER.info("Experiment completed. Best model: %s", best_model_name)
    return summary
