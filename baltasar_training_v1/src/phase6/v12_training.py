"""Baltasar v1.2 training over the extended dataset."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.io import load_dataset
from src.data.validation import validate_dataset
from src.diagnostics.temporal_validation import walk_forward_evaluation
from src.evaluation.metrics import class_metrics_table, compute_model_metrics
from src.features.engineering import build_feature_frame, normalize_dataframe
from src.features.targeting import prepare_target
from src.models.training import build_model_pipeline, temporal_split


COMMON_DATASET_ROOT = Path(
    r"C:\Users\Asus\AppData\Roaming\MetaQuotes\Terminal\Common\Files\MAGI\datasets\bot_a_sub1"
)


@dataclass
class DatasetSelection:
    path: str
    source_type: str
    run_name: str
    csv_files: int
    rows: int
    columns: int
    timestamp_min: str
    timestamp_max: str
    approx_months: float


def build_v12_config(config: dict[str, Any], dataset_path: str) -> dict[str, Any]:
    """Clone config with Baltasar v1.2 defaults and the selected dataset source."""
    cloned = deepcopy(config)
    cloned["dataset"]["source"]["type"] = "directory"
    cloned["dataset"]["source"]["path"] = dataset_path
    cloned["dataset"]["source"]["csv_glob"] = "*.csv"
    cloned["dataset"]["feature_variant"] = "compact"
    cloned["dataset"]["derived_target"]["horizon_steps"] = 12
    cloned["dataset"]["derived_target"]["buy_threshold"] = 0.0003
    cloned["dataset"]["derived_target"]["sell_threshold"] = -0.0003
    cloned["models"]["hist_gradient_boosting"]["enabled"] = False
    cloned["experiment"]["notes"] = "Baltasar v1.2 training on extended 24-month dataset with h12_t03."
    return cloned


def locate_extended_dataset(config: dict[str, Any]) -> DatasetSelection:
    """Locate the longest available Bot_A_sub1 dataset, preferring the 24-month run."""
    candidate_roots: list[Path] = []
    project_root = Path(config.get("_project_root", "."))
    for relative in [
        project_root / "data" / "extended",
        project_root / "data" / "processed",
        project_root / "data",
        project_root.parent / "dataset",
        project_root.parent / "datasets",
    ]:
        if relative.exists():
            candidate_roots.append(relative)
    if COMMON_DATASET_ROOT.exists():
        candidate_roots.append(COMMON_DATASET_ROOT)

    run_candidates: list[DatasetSelection] = []
    for root in candidate_roots:
        if root == COMMON_DATASET_ROOT:
            for run_dir in sorted([path for path in root.iterdir() if path.is_dir()]):
                csvs = sorted(run_dir.rglob("*.csv"))
                if not csvs:
                    continue
                try:
                    sample = _summarize_csv_collection(csvs)
                except Exception:
                    continue
                run_candidates.append(
                    DatasetSelection(
                        path=str(run_dir),
                        source_type="directory",
                        run_name=run_dir.name,
                        csv_files=len(csvs),
                        rows=sample["rows"],
                        columns=sample["columns"],
                        timestamp_min=sample["timestamp_min"],
                        timestamp_max=sample["timestamp_max"],
                        approx_months=sample["approx_months"],
                    )
                )
        else:
            for directory in sorted([path for path in root.rglob("*") if path.is_dir()]):
                csvs = sorted(directory.glob("*.csv"))
                if not csvs:
                    continue
                try:
                    sample = _summarize_csv_collection(csvs)
                except Exception:
                    continue
                run_candidates.append(
                    DatasetSelection(
                        path=str(directory),
                        source_type="directory",
                        run_name=directory.name,
                        csv_files=len(csvs),
                        rows=sample["rows"],
                        columns=sample["columns"],
                        timestamp_min=sample["timestamp_min"],
                        timestamp_max=sample["timestamp_max"],
                        approx_months=sample["approx_months"],
                    )
                )

    if not run_candidates:
        raise FileNotFoundError("No candidate Bot_A_sub1 dataset directories were found.")

    ranked = sorted(
        run_candidates,
        key=lambda item: (item.approx_months, item.csv_files, item.rows),
        reverse=True,
    )
    return ranked[0]


def _summarize_csv_collection(csv_paths: list[Path]) -> dict[str, Any]:
    schema_df = pd.read_csv(csv_paths[0], nrows=5)
    required = {"anchor_bar_timestamp", "snapshot_id", "current_price"}
    if not required.issubset(set(schema_df.columns)):
        raise ValueError("CSV collection does not match the Bot_A_sub1 training schema.")

    first_df = pd.read_csv(csv_paths[0], usecols=lambda column: column in {"anchor_bar_timestamp"})
    last_df = pd.read_csv(csv_paths[-1], usecols=lambda column: column in {"anchor_bar_timestamp"})
    row_count = 0
    for file_path in csv_paths:
        with file_path.open("r", encoding="utf-8") as handle:
            row_count += max(sum(1 for _ in handle) - 1, 0)
    ts_min = pd.to_datetime(first_df["anchor_bar_timestamp"], utc=True, errors="coerce").min()
    ts_max = pd.to_datetime(last_df["anchor_bar_timestamp"], utc=True, errors="coerce").max()
    approx_months = (ts_max - ts_min).days / 30.4375 if pd.notna(ts_min) and pd.notna(ts_max) else 0.0
    return {
        "rows": int(row_count),
        "columns": int(schema_df.shape[1]),
        "timestamp_min": str(ts_min),
        "timestamp_max": str(ts_max),
        "approx_months": float(approx_months),
    }


def quick_dataset_checks(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Run lightweight validation checks for the extended dataset."""
    timestamp_column = config["dataset"]["timestamp_column"]
    timestamps = pd.to_datetime(df[timestamp_column], utc=True, errors="coerce").sort_values()
    deltas = timestamps.diff().dropna()
    duplicate_rows = int(df.duplicated().sum())
    duplicate_snapshot_ids = int(df["snapshot_id"].duplicated().sum()) if "snapshot_id" in df.columns else None
    large_gaps = deltas[deltas > pd.Timedelta(hours=8)]
    schema_check = {
        "missing_required_columns": [
            column for column in config["dataset"]["required_columns"] if column not in df.columns
        ],
        "column_count": int(df.shape[1]),
    }
    return {
        "duplicate_rows": duplicate_rows,
        "duplicate_snapshot_ids": duplicate_snapshot_ids,
        "null_timestamp_rows": int(pd.to_datetime(df[timestamp_column], utc=True, errors="coerce").isna().sum()),
        "median_gap_minutes": float(deltas.median().total_seconds() / 60) if not deltas.empty else None,
        "p95_gap_minutes": float(deltas.quantile(0.95).total_seconds() / 60) if not deltas.empty else None,
        "gaps_over_8h": int(len(large_gaps)),
        "largest_gap_hours": float(large_gaps.max().total_seconds() / 3600) if not large_gaps.empty else 0.0,
        "schema_check": schema_check,
    }


def run_v12_training(config: dict[str, Any]) -> dict[str, Any]:
    """Train Baltasar v1.2 and compare it against the official v1.1 benchmark."""
    dataset_selection = locate_extended_dataset(config)
    v12_config = build_v12_config(config, dataset_selection.path)

    raw_df = load_dataset(v12_config, Path(v12_config["_project_root"]))
    normalized_df = normalize_dataframe(raw_df, v12_config)
    validation_report = validate_dataset(normalized_df, v12_config)
    quick_checks = quick_dataset_checks(normalized_df, v12_config)

    labelled_df = prepare_target(normalized_df, v12_config)
    X, y, timestamps = build_feature_frame(labelled_df, v12_config)
    split = temporal_split(X, y, timestamps, test_size=float(v12_config["split"]["test_size"]))
    target_distribution = y.value_counts(normalize=True).to_dict()
    walk_forward_df = walk_forward_evaluation(X, y, timestamps, v12_config)

    rows: list[dict[str, Any]] = []
    class_tables: dict[str, pd.DataFrame] = {}
    confusion_matrices: dict[str, list[list[int]]] = {}
    predictions_by_model: dict[str, pd.Series] = {}

    for model_name in ["baseline_tree", "random_forest"]:
        model_cfg = v12_config["models"][model_name]
        pipeline = build_model_pipeline(split.X_train, v12_config, model_cfg)
        pipeline.fit(split.X_train, split.y_train)
        predictions = pipeline.predict(split.X_test)
        predictions_by_model[model_name] = pd.Series(predictions)
        metrics = compute_model_metrics(split.y_test, predictions, v12_config["dataset"]["label_order"])
        class_df = class_metrics_table(split.y_test, predictions, v12_config["dataset"]["label_order"])
        class_tables[model_name] = class_df
        confusion_matrices[model_name] = metrics["confusion_matrix"]
        valid_walk = walk_forward_df[
            (walk_forward_df["model_name"] == model_name) & walk_forward_df["f1_macro"].notna()
        ]
        rows.append(
            {
                "version": "Baltasar v1.2",
                "target_name": "h12_t03",
                "feature_variant": "compact",
                "model_name": model_name,
                "dataset_path": dataset_selection.path,
                "dataset_rows": int(len(labelled_df)),
                "feature_count": int(split.X_train.shape[1]),
                "accuracy": float(metrics["accuracy"]),
                "precision_macro": float(metrics["precision_macro"]),
                "recall_macro": float(metrics["recall_macro"]),
                "f1_macro": float(metrics["f1_macro"]),
                "walk_forward_f1_mean": float(valid_walk["f1_macro"].mean()) if not valid_walk.empty else None,
                "walk_forward_f1_std": float(valid_walk["f1_macro"].std(ddof=0)) if not valid_walk.empty else None,
            }
        )

    metrics_df = pd.DataFrame(rows)
    return {
        "dataset_selection": asdict(dataset_selection),
        "validation_report": validation_report.to_dict(),
        "quick_checks": quick_checks,
        "labelled_rows": int(len(labelled_df)),
        "target_distribution": target_distribution,
        "metrics_df": metrics_df,
        "class_tables": class_tables,
        "confusion_matrices": confusion_matrices,
        "walk_forward_df": walk_forward_df,
        "split_test_labels": split.y_test.copy(),
    }
