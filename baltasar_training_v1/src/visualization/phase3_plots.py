"""Visualization helpers for phase 3."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_target_grid_heatmap(target_grid_df: pd.DataFrame, value_column: str, output_path: Path) -> None:
    pivot = target_grid_df.pivot(index="horizon_steps", columns="threshold", values=value_column)
    fig, ax = plt.subplots(figsize=(8, 5))
    image = ax.imshow(pivot.values, cmap="viridis")
    ax.set_title(f"Target Grid Heatmap - {value_column}")
    ax.set_xticks(range(len(pivot.columns)), [f"{col:.4f}" for col in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), pivot.index.astype(str))
    ax.set_xlabel("Threshold")
    ax.set_ylabel("Horizon")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, f"{pivot.iloc[i, j]:.3f}", ha="center", va="center", color="white")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_candidate_comparison(comparison_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = comparison_df.copy()
    plot_df["label"] = plot_df["scenario_name"] + "\n" + plot_df["model_name"]
    fig, ax = plt.subplots(figsize=(11, 6))
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
    ax.set_title("Scenario Comparison: Signal and Stability")
    ax.set_ylabel("Score")
    ax.set_xlabel("Scenario / Model")
    ax.legend()
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_feature_count_comparison(comparison_df: pd.DataFrame, output_path: Path) -> None:
    plot_df = comparison_df.copy()
    plot_df["label"] = plot_df["scenario_name"] + "\n" + plot_df["model_name"]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(plot_df["label"], plot_df["feature_count"], color="#55a868")
    ax.set_title("Feature Count by Scenario")
    ax.set_ylabel("Feature count")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_walk_forward_scenario_plot(walk_df: pd.DataFrame, scenario_name: str, output_path: Path) -> None:
    valid = walk_df.dropna(subset=["f1_macro"])
    if valid.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    for model_name, group in valid.groupby("model_name"):
        ax.plot(group["fold"], group["f1_macro"], marker="o", label=model_name)
    ax.set_title(f"Walk-forward F1 by Fold - {scenario_name}")
    ax.set_xlabel("Fold")
    ax.set_ylabel("F1 macro")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
