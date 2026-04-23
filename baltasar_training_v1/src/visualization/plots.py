"""Matplotlib plotting helpers for reports and dashboard."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def save_target_distribution(y: pd.Series, output_path: Path) -> None:
    counts = y.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(8, 4))
    counts.plot(kind="bar", ax=ax, color=["#c44e52", "#8172b2", "#55a868"])
    ax.set_title("Target Distribution")
    ax.set_xlabel("Label")
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_missing_ratio(missing_ratio: pd.Series, output_path: Path) -> None:
    top_missing = missing_ratio.sort_values(ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(10, 5))
    top_missing.plot(kind="bar", ax=ax, color="#4c72b0")
    ax.set_title("Top Missing Ratios")
    ax.set_ylabel("Missing Ratio")
    ax.set_xlabel("Column")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_model_comparison(metrics_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = metrics_df.set_index("model_name")[["accuracy", "precision_macro", "recall_macro", "f1_macro"]]
    fig, ax = plt.subplots(figsize=(10, 5))
    plot_df.plot(kind="bar", ax=ax)
    ax.set_title("Model Comparison")
    ax.set_ylabel("Score")
    ax.set_xlabel("Model")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_confusion_matrix(matrix: list[list[int]], labels: list[str], title: str, output_path: Path) -> None:
    matrix_np = np.array(matrix)
    fig, ax = plt.subplots(figsize=(5, 4))
    image = ax.imshow(matrix_np, cmap="Blues")
    ax.set_title(title)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")

    for i in range(matrix_np.shape[0]):
        for j in range(matrix_np.shape[1]):
            ax.text(j, i, str(matrix_np[i, j]), ha="center", va="center", color="black")

    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_feature_importance(feature_importance: pd.DataFrame, title: str, output_path: Path) -> None:
    top = feature_importance.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top["feature"], top["importance"], color="#dd8452")
    ax.set_title(title)
    ax.set_xlabel("Importance")
    ax.set_ylabel("Feature")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
