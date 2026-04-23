"""Temporal validation routines for diagnostics."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.evaluation.metrics import compute_model_metrics
from src.models.training import build_model_pipeline


def walk_forward_evaluation(
    X: pd.DataFrame,
    y: pd.Series,
    timestamps: pd.Series,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Run an expanding-window walk-forward validation across configured models."""
    n_folds = int(config["diagnostics"]["walk_forward"]["n_folds"])
    min_train_fraction = float(config["diagnostics"]["walk_forward"]["min_train_fraction"])
    start_train_end = int(len(X) * min_train_fraction)
    remaining = len(X) - start_train_end
    test_size = max(1, remaining // n_folds)
    label_order = config["dataset"]["label_order"]

    records: list[dict[str, Any]] = []
    for fold in range(n_folds):
        train_end = start_train_end + fold * test_size
        test_end = min(len(X), train_end + test_size)
        if test_end <= train_end:
            continue

        X_train = X.iloc[:train_end].copy()
        y_train = y.iloc[:train_end].copy()
        X_test = X.iloc[train_end:test_end].copy()
        y_test = y.iloc[train_end:test_end].copy()
        ts_test = timestamps.iloc[train_end:test_end]

        for model_name, model_cfg in config["models"].items():
            if not model_cfg.get("enabled", False):
                continue

            try:
                pipeline = build_model_pipeline(X_train, config, model_cfg)
                pipeline.fit(X_train, y_train)
                predictions = pipeline.predict(X_test)
                metrics = compute_model_metrics(y_test, predictions, label_order)
                records.append(
                    {
                        "fold": fold + 1,
                        "model_name": model_name,
                        "train_rows": int(len(X_train)),
                        "test_rows": int(len(X_test)),
                        "test_start": str(ts_test.min()),
                        "test_end": str(ts_test.max()),
                        "accuracy": float(metrics["accuracy"]),
                        "precision_macro": float(metrics["precision_macro"]),
                        "recall_macro": float(metrics["recall_macro"]),
                        "f1_macro": float(metrics["f1_macro"]),
                    }
                )
            except Exception as error:
                records.append(
                    {
                        "fold": fold + 1,
                        "model_name": model_name,
                        "train_rows": int(len(X_train)),
                        "test_rows": int(len(X_test)),
                        "test_start": str(ts_test.min()),
                        "test_end": str(ts_test.max()),
                        "accuracy": None,
                        "precision_macro": None,
                        "recall_macro": None,
                        "f1_macro": None,
                        "error": str(error),
                    }
                )

    return pd.DataFrame(records)
