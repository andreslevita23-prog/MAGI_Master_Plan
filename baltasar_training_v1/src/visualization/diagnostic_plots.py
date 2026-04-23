"""Diagnostic plotting helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def save_target_sensitivity_plot(target_audit_df: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(target_audit_df["name"], target_audit_df["f1_macro"], marker="o", label="F1 macro")
    ax.plot(target_audit_df["name"], target_audit_df["neutral_share"], marker="s", label="Neutral share")
    ax.set_title("Target Sensitivity Across Scenarios")
    ax.set_ylabel("Value")
    ax.set_xlabel("Scenario")
    ax.legend()
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_class_distribution_comparison(target_audit_df: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    plot_df = target_audit_df.set_index("name")[["sell_share", "neutral_share", "buy_share"]]
    plot_df.plot(kind="bar", stacked=True, ax=ax, color=["#c44e52", "#8172b2", "#55a868"])
    ax.set_title("Class Distribution by Target Scenario")
    ax.set_ylabel("Share")
    ax.set_xlabel("Scenario")
    ax.legend(["SELL", "NEUTRAL", "BUY"], loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_normalized_confusion_matrix(matrix, labels: list[str], title: str, output_path: Path) -> None:
    matrix_np = np.array(matrix)
    fig, ax = plt.subplots(figsize=(5, 4))
    image = ax.imshow(matrix_np, cmap="Oranges", vmin=0, vmax=1)
    ax.set_title(title)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    for i in range(matrix_np.shape[0]):
        for j in range(matrix_np.shape[1]):
            ax.text(j, i, f"{matrix_np[i, j]:.2f}", ha="center", va="center", color="black")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_feature_boxplots(df: pd.DataFrame, target_column: str, features: list[str], output_path: Path) -> None:
    available = [feature for feature in features if feature in df.columns]
    if not available:
        return
    fig, axes = plt.subplots(len(available), 1, figsize=(10, max(4, 3 * len(available))))
    if len(available) == 1:
        axes = [axes]
    for ax, feature in zip(axes, available):
        df.boxplot(column=feature, by=target_column, ax=ax)
        ax.set_title(feature)
        ax.set_xlabel("")
    fig.suptitle("Top Numeric Feature Distributions by Target")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_feature_scatter(df: pd.DataFrame, target_column: str, features: list[str], output_path: Path) -> None:
    if len(features) < 2:
        return
    available = [feature for feature in features if feature in df.columns]
    if len(available) < 2:
        return
    sample = df[[available[0], available[1], target_column]].dropna().sample(
        n=min(3000, len(df)),
        random_state=42,
    )
    colors = {"SELL": "#c44e52", "NEUTRAL": "#8172b2", "BUY": "#55a868"}
    fig, ax = plt.subplots(figsize=(8, 6))
    for label, group in sample.groupby(target_column):
        ax.scatter(
            group[available[0]],
            group[available[1]],
            label=label,
            alpha=0.4,
            s=16,
            color=colors.get(label, "#4c72b0"),
        )
    ax.set_title("Bivariate View of Top Numeric Features")
    ax.set_xlabel(available[0])
    ax.set_ylabel(available[1])
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_correlation_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    if df.empty:
        return
    corr = df.corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    image = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=90)
    ax.set_yticks(range(len(corr.columns)))
    ax.set_yticklabels(corr.columns)
    ax.set_title("Numeric Feature Correlation Heatmap")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_metric_by_fold(walk_forward_df: pd.DataFrame, metric: str, output_path: Path) -> None:
    if walk_forward_df.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    for model_name, group in walk_forward_df.groupby("model_name"):
        ax.plot(group["fold"], group[metric], marker="o", label=model_name)
    ax.set_title(f"Walk-forward {metric} by fold")
    ax.set_xlabel("Fold")
    ax.set_ylabel(metric)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
