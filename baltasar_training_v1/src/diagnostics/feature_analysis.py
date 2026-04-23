"""Feature diagnostics for Baltasar."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_selection import f_classif
from sklearn.impute import SimpleImputer


def numeric_feature_summary(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """Return per-target descriptive stats for numeric features."""
    numeric = X.select_dtypes(include=["number"]).copy()
    grouped = numeric.assign(target=y.values).groupby("target").agg(["mean", "median", "std"])
    grouped.columns = ["__".join(column) for column in grouped.columns]
    return grouped.T.reset_index().rename(columns={"index": "feature_stat"})


def univariate_numeric_scores(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """Score numeric features with ANOVA F-statistics against the target."""
    numeric = X.select_dtypes(include=["number"]).copy()
    numeric = numeric.loc[:, numeric.notna().any()]
    if numeric.empty:
        return pd.DataFrame(columns=["feature", "f_score", "p_value"])

    imputed = SimpleImputer(strategy="median").fit_transform(numeric)
    scores, p_values = f_classif(imputed, y)
    scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
    p_values = np.nan_to_num(p_values, nan=1.0, posinf=1.0, neginf=1.0)
    result = pd.DataFrame(
        {"feature": numeric.columns, "f_score": scores, "p_value": p_values}
    ).sort_values(["f_score", "p_value"], ascending=[False, True])
    return result.reset_index(drop=True)


def correlated_feature_pairs(X: pd.DataFrame, threshold: float = 0.9) -> pd.DataFrame:
    """Return highly correlated numeric feature pairs."""
    numeric = X.select_dtypes(include=["number"]).copy()
    if numeric.shape[1] < 2:
        return pd.DataFrame(columns=["feature_a", "feature_b", "abs_correlation"])

    corr = numeric.corr().abs()
    records = []
    for i, feature_a in enumerate(corr.columns):
        for feature_b in corr.columns[i + 1 :]:
            value = corr.loc[feature_a, feature_b]
            if pd.notna(value) and value >= threshold:
                records.append(
                    {
                        "feature_a": feature_a,
                        "feature_b": feature_b,
                        "abs_correlation": float(value),
                    }
                )
    return pd.DataFrame(records).sort_values("abs_correlation", ascending=False).reset_index(drop=True)


def low_utility_features(
    importance_df: pd.DataFrame,
    univariate_df: pd.DataFrame,
    top_k: int = 8,
) -> pd.DataFrame:
    """Combine low feature importance and weak univariate score as a utility screen."""
    merged = importance_df.merge(univariate_df, on="feature", how="left")
    merged["importance_rank"] = merged["importance"].rank(method="dense", ascending=False)
    merged["univariate_rank"] = merged["f_score"].fillna(0.0).rank(method="dense", ascending=False)
    merged["combined_rank"] = merged["importance_rank"] + merged["univariate_rank"]
    merged = merged.sort_values("combined_rank", ascending=False).head(top_k)
    return merged.reset_index(drop=True)


def aggregate_feature_importance(importance_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transformed feature importance back to raw feature names."""
    grouped_features = []
    for feature in importance_df["feature"]:
        if feature.startswith("numeric__"):
            grouped_features.append(feature.replace("numeric__", "", 1))
            continue
        if feature.startswith("categorical__"):
            remainder = feature.replace("categorical__", "", 1)
            grouped_features.append(remainder.rsplit("_", 1)[0] if "_" in remainder else remainder)
            continue
        grouped_features.append(feature)

    aggregated = importance_df.copy()
    aggregated["raw_feature"] = grouped_features
    aggregated = (
        aggregated.groupby("raw_feature", as_index=False)["importance"]
        .sum()
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    return aggregated


def class_separation_snapshot(X: pd.DataFrame, y: pd.Series, features: list[str]) -> pd.DataFrame:
    """Produce per-class means for a small feature set."""
    available = [feature for feature in features if feature in X.columns]
    if not available:
        return pd.DataFrame()
    return X[available].assign(target=y.values).groupby("target").mean().reset_index()
