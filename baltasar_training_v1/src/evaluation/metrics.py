"""Metric calculation helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def compute_model_metrics(
    y_true,
    y_pred,
    label_order: list[str],
) -> dict[str, Any]:
    """Compute the required global and per-class metrics."""
    report = classification_report(
        y_true,
        y_pred,
        labels=label_order,
        output_dict=True,
        zero_division=0,
    )

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_by_class": {
            label: float(report.get(label, {}).get("f1-score", 0.0)) for label in label_order
        },
        "support_by_class": {
            label: int(report.get(label, {}).get("support", 0)) for label in label_order
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=label_order).tolist(),
    }


def class_metrics_table(y_true, y_pred, label_order: list[str]) -> pd.DataFrame:
    """Return per-class precision, recall, f1 and support."""
    report = classification_report(
        y_true,
        y_pred,
        labels=label_order,
        output_dict=True,
        zero_division=0,
    )
    rows = []
    for label in label_order:
        rows.append(
            {
                "label": label,
                "precision": float(report.get(label, {}).get("precision", 0.0)),
                "recall": float(report.get(label, {}).get("recall", 0.0)),
                "f1": float(report.get(label, {}).get("f1-score", 0.0)),
                "support": int(report.get(label, {}).get("support", 0)),
            }
        )
    return pd.DataFrame(rows)


def metrics_table(model_metrics: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Build a flat comparison table from the nested metrics dictionary."""
    records = []
    for model_name, metrics in model_metrics.items():
        records.append(
            {
                "model_name": model_name,
                "accuracy": metrics["accuracy"],
                "precision_macro": metrics["precision_macro"],
                "recall_macro": metrics["recall_macro"],
                "f1_macro": metrics["f1_macro"],
            }
        )
    return pd.DataFrame(records).sort_values("f1_macro", ascending=False).reset_index(drop=True)
