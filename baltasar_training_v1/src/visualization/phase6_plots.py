"""Plots for Baltasar v1.2 training outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_v11_v12_comparison(comparison_df: pd.DataFrame, output_path: Path) -> None:
    """Plot v1.1 versus v1.2 by model."""
    plot_df = comparison_df.copy()
    plot_df["label"] = plot_df["version"] + "\n" + plot_df["model_name"]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(plot_df["label"], plot_df["walk_forward_f1_mean"], color="#4c72b0", label="WF F1 mean")
    ax.errorbar(
        plot_df["label"],
        plot_df["walk_forward_f1_mean"],
        yerr=plot_df["walk_forward_f1_std"],
        fmt="none",
        ecolor="black",
        capsize=4,
    )
    ax.plot(plot_df["label"], plot_df["f1_macro"], color="#dd8452", marker="o", label="Holdout F1 macro")
    ax.set_title("Baltasar v1.1 vs v1.2")
    ax.set_ylabel("Score")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_walk_forward_plot(walk_df: pd.DataFrame, output_path: Path) -> None:
    """Plot walk-forward F1 by fold for v1.2 models."""
    valid = walk_df[walk_df["model_name"].isin(["baseline_tree", "random_forest"])].dropna(subset=["f1_macro"])
    fig, ax = plt.subplots(figsize=(10, 5))
    for model_name, group in valid.groupby("model_name"):
        ax.plot(group["fold"], group["f1_macro"], marker="o", label=model_name)
    ax.set_title("Baltasar v1.2 Walk-forward F1")
    ax.set_xlabel("Fold")
    ax.set_ylabel("F1 macro")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
