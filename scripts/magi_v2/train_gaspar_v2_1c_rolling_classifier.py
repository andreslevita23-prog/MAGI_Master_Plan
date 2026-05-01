from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import joblib
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.utils.class_weight import compute_sample_weight


DEFAULT_DATASET = Path("data/output/magi_v2/gaspar_v2_1c_rolling_dataset/gaspar_v2_1c_rolling_dataset.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/gaspar_v2_1c_rolling_classifier")
DEFAULT_DOC = Path("docs/gaspar_v2_1c_rolling_classifier.md")

TARGET = "regime_deteriorating_rr2"
SECONDARY_TARGET = "sell_risk_next_window"
LABELS = ["DETERIORATING", "NEUTRAL", "STABLE"]
BLOCK_THRESHOLDS = [0.50, 0.60, 0.70]
Q2_START = pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
Q2_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")

FORBIDDEN_FEATURES = {
    "timestamp",
    "symbol",
    "split",
    "year",
    "quarter",
    "month",
    "realized_R",
    "context_quality_rr2",
    TARGET,
    SECONDARY_TARGET,
    "regime_deteriorating_rr2_20",
    "regime_deteriorating_rr2_50",
    "regime_deteriorating_rr2_100",
    "sell_risk_next_window_20",
    "sell_risk_next_window_50",
    "sell_risk_next_window_100",
    "future_outcome_h12",
    "future_outcome_h48",
    "future_outcome_h96",
    "future_outcome_h288",
}

TECHNICAL_FEATURES = [
    "regime",
    "market_structure",
    "h4_market_structure",
    "d1_market_structure",
    "daily_range_position",
    "atr",
]


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = read_dataset(Path(args.dataset))
    train = df[df["split"].eq("train")].copy()
    validation = df[df["split"].eq("validation")].copy()
    test = df[df["split"].eq("test")].copy()
    features = infer_features(df)
    verify_no_leakage(features)

    pipeline = build_pipeline(train, features)
    sample_weight = compute_sample_weight(class_weight="balanced", y=train[TARGET])
    pipeline.fit(train[features], train[TARGET], model__sample_weight=sample_weight)

    validation_pred = pipeline.predict(validation[features])
    test_pred = pipeline.predict(test[features])
    validation_proba = probability_frame(pipeline, validation[features])
    test_proba = probability_frame(pipeline, test[features])

    metrics = {
        "schema_version": "gaspar_v2_1c_rolling_classifier_v0.1",
        "generated_at": utc_now(),
        "model_type": "HistGradientBoostingClassifier",
        "dataset": str(args.dataset),
        "target": TARGET,
        "secondary_target": SECONDARY_TARGET,
        "labels": LABELS,
        "rows": {
            "train": int(len(train)),
            "validation": int(len(validation)),
            "test": int(len(test)),
        },
        "feature_columns": features,
        "feature_column_count": len(features),
        "forbidden_feature_intersection": sorted(set(features) & FORBIDDEN_FEATURES),
        "classification": {
            "validation": classification_metrics(validation[TARGET], validation_pred),
            "test": classification_metrics(test[TARGET], test_pred),
        },
        "secondary_target_distribution": {
            "train": value_counts(train[SECONDARY_TARGET]),
            "validation": value_counts(validation[SECONDARY_TARGET]),
            "test": value_counts(test[SECONDARY_TARGET]),
        },
        "filter_simulation": {
            "validation": filter_metrics(validation, validation_proba),
            "test": filter_metrics(test, test_proba),
        },
        "baseline_original": {
            "validation": trade_metrics(validation),
            "test": trade_metrics(test),
        },
        "q2_2026": q2_metrics(test, test_proba),
        "technical_decisions": [
            "The model predicts regime deterioration, not trade direction.",
            "Features include only past rolling state and current technical context.",
            "Target labels use future windows and are excluded from features.",
            "No date, month, quarter, realized_R or future outcome columns are used as features.",
            "Blocking simulation removes trades when P(DETERIORATING) crosses a threshold.",
        ],
    }

    importance = feature_importance(pipeline, validation, features)
    importance.to_csv(output_dir / "gaspar_v2_1c_feature_importance.csv", index=False)

    joblib.dump(
        {
            "schema_version": metrics["schema_version"],
            "trained_at": metrics["generated_at"],
            "model_type": metrics["model_type"],
            "target": TARGET,
            "secondary_target": SECONDARY_TARGET,
            "labels": LABELS,
            "features": features,
            "categorical_features": categorical_columns(train, features),
            "numeric_features": numeric_columns(train, features),
            "pipeline": pipeline,
        },
        output_dir / "gaspar_v2_1c_model.joblib",
    )
    (output_dir / "gaspar_v2_1c_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = markdown_summary(metrics, importance)
    (output_dir / "gaspar_v2_1c_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")

    print("model=HistGradientBoostingClassifier")
    print(f"validation_macro_f1={metrics['classification']['validation']['macro_f1']}")
    print(f"test_macro_f1={metrics['classification']['test']['macro_f1']}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Gaspar v2.1c rolling causal classifier.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)


def infer_features(df: pd.DataFrame) -> list[str]:
    rolling = [
        column
        for column in df.columns
        if column.startswith("rolling_") or column.startswith("recent_")
    ]
    technical = [column for column in TECHNICAL_FEATURES if column in df.columns]
    features = []
    for column in rolling + technical:
        lower = column.lower()
        if column in FORBIDDEN_FEATURES:
            continue
        if "future" in lower or "outcome" in lower or "target" in lower:
            continue
        features.append(column)
    return list(dict.fromkeys(features))


def verify_no_leakage(features: list[str]) -> None:
    leaked = sorted(set(features) & FORBIDDEN_FEATURES)
    if leaked:
        raise ValueError(f"Forbidden features found: {leaked}")


def build_pipeline(train: pd.DataFrame, features: list[str]) -> Pipeline:
    categoricals = categorical_columns(train, features)
    numerics = numeric_columns(train, features)
    try:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), numerics),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", encoder),
                    ]
                ),
                categoricals,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    model = HistGradientBoostingClassifier(
        max_iter=220,
        learning_rate=0.045,
        max_leaf_nodes=31,
        l2_regularization=0.05,
        random_state=42,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def categorical_columns(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [column for column in features if not is_numeric_dtype(df[column])]


def numeric_columns(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [column for column in features if is_numeric_dtype(df[column])]


def probability_frame(pipeline: Pipeline, x: pd.DataFrame) -> pd.DataFrame:
    proba = pipeline.predict_proba(x)
    classes = list(pipeline.named_steps["model"].classes_)
    return pd.DataFrame(proba, columns=[f"p_{label}" for label in classes], index=x.index)


def classification_metrics(y_true: pd.Series, y_pred: Any) -> dict[str, Any]:
    report = classification_report(y_true, y_pred, labels=LABELS, output_dict=True, zero_division=0)
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)
    return {
        "accuracy": round_float(accuracy_score(y_true, y_pred)),
        "macro_f1": round_float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "per_class": {
            label: {
                "precision": round_float(report[label]["precision"]),
                "recall": round_float(report[label]["recall"]),
                "f1": round_float(report[label]["f1-score"]),
                "support": int(report[label]["support"]),
            }
            for label in LABELS
        },
        "confusion_matrix": {"labels": LABELS, "matrix": matrix.astype(int).tolist()},
        "prediction_distribution": value_counts(pd.Series(y_pred)),
        "target_distribution": value_counts(y_true),
    }


def filter_metrics(df: pd.DataFrame, proba: pd.DataFrame) -> dict[str, Any]:
    p_deteriorating = proba["p_DETERIORATING"]
    original = trade_metrics(df)
    results = {}
    for threshold in [f"{value:.2f}" for value in BLOCK_THRESHOLDS]:
        threshold_value = float(threshold)
        blocked = p_deteriorating >= threshold_value
        remaining = df.loc[~blocked].copy()
        blocked_df = df.loc[blocked].copy()
        results[threshold] = {
            "original": original,
            "trades_original": int(len(df)),
            "trades_blocked": int(blocked.sum()),
            "blocked_share": round_float(float(blocked.mean()) if len(df) else 0.0),
            "trades_remaining": int(len(remaining)),
            "filtered": trade_metrics(remaining),
            "blocked": trade_metrics(blocked_df),
            "impact_buy": direction_impact(df, remaining, "ENTER_BUY"),
            "impact_sell": direction_impact(df, remaining, "ENTER_SELL"),
        }
    return results


def q2_metrics(test: pd.DataFrame, proba: pd.DataFrame) -> dict[str, Any]:
    mask = test["timestamp"].between(Q2_START, Q2_END)
    q2 = test.loc[mask].copy()
    q2_proba = proba.loc[q2.index]
    return {"original": trade_metrics(q2), "filters": filter_metrics(q2, q2_proba)}


def direction_impact(original: pd.DataFrame, remaining: pd.DataFrame, direction: str) -> dict[str, Any]:
    original_part = original[original["prediction"].eq(direction)]
    remaining_part = remaining[remaining["prediction"].eq(direction)]
    return {
        "original": trade_metrics(original_part),
        "filtered": trade_metrics(remaining_part),
        "blocked": int(len(original_part) - len(remaining_part)),
    }


def trade_metrics(df: pd.DataFrame) -> dict[str, Any]:
    r = pd.to_numeric(df.get("realized_R", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    trades = int(len(r))
    wins = r[r > 0]
    losses = r[r < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (math.inf if gross_profit > 0 else 0.0)
    return {
        "trades": trades,
        "avg_r": round_float(float(r.mean()) if trades else 0.0),
        "total_r": round_float(float(r.sum())),
        "profit_factor": round_float(pf),
        "max_drawdown_r": round_float(max_drawdown(r)),
        "win_rate": round_float(float((r > 0).mean()) if trades else 0.0),
    }


def max_drawdown(r: pd.Series) -> float:
    if r.empty:
        return 0.0
    equity = r.cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return float((peak - equity).max())


def feature_importance(pipeline: Pipeline, validation: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    sample = validation.sample(n=min(5000, len(validation)), random_state=42)
    result = permutation_importance(
        pipeline,
        sample[features],
        sample[TARGET],
        scoring="f1_macro",
        n_repeats=5,
        random_state=42,
        n_jobs=1,
    )
    return (
        pd.DataFrame(
            {
                "feature": features,
                "importance_mean": result.importances_mean,
                "importance_std": result.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )


def markdown_summary(metrics: dict[str, Any], importance: pd.DataFrame) -> str:
    lines = [
        "# Gaspar v2.1c Rolling Classifier",
        "",
        "## Scope",
        "",
        "- Target: `regime_deteriorating_rr2`.",
        "- Secondary diagnostic target: `sell_risk_next_window`.",
        "- Gaspar detects regime deterioration; it does not predict direction.",
        "",
        "## Model",
        "",
        f"- Model: `{metrics['model_type']}`",
        f"- Train rows: `{metrics['rows']['train']:,}`",
        f"- Validation rows: `{metrics['rows']['validation']:,}`",
        f"- Test rows: `{metrics['rows']['test']:,}`",
        f"- Feature columns: `{metrics['feature_column_count']}`",
        "",
        "## Classification Metrics",
        "",
        classification_table(metrics),
        "",
        "## Filter Simulation",
        "",
        filter_table(metrics),
        "",
        "## 2026Q2 Impact",
        "",
        q2_table(metrics),
        "",
        "## Top Feature Importance",
        "",
        importance_table(importance.head(20)),
        "",
        "## Interpretation",
        "",
        interpretation(metrics),
    ]
    return "\n".join(lines) + "\n"


def classification_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Split | Accuracy | Macro F1 | P(DETERIORATING) | R(DETERIORATING) | P(STABLE) | R(STABLE) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ["validation", "test"]:
        item = metrics["classification"][split]
        det = item["per_class"]["DETERIORATING"]
        stable = item["per_class"]["STABLE"]
        rows.append(
            f"| {split} | {item['accuracy']:.4f} | {item['macro_f1']:.4f} | "
            f"{det['precision']:.4f} | {det['recall']:.4f} | {stable['precision']:.4f} | {stable['recall']:.4f} |"
        )
    return "\n".join(rows)


def filter_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Split | Threshold | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | DD original | DD filtered |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ["validation", "test"]:
        for threshold, item in metrics["filter_simulation"][split].items():
            original = item["original"]
            filtered = item["filtered"]
            rows.append(
                f"| {split} | {threshold} | {item['trades_blocked']:,} | {item['trades_remaining']:,} | "
                f"{original['avg_r']:.4f} | {filtered['avg_r']:.4f} | "
                f"{original['profit_factor']:.4f} | {filtered['profit_factor']:.4f} | "
                f"{original['max_drawdown_r']:.2f} | {filtered['max_drawdown_r']:.2f} |"
            )
    return "\n".join(rows)


def q2_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Threshold | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | DD original | DD filtered |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for threshold, item in metrics["q2_2026"]["filters"].items():
        original = item["original"]
        filtered = item["filtered"]
        rows.append(
            f"| {threshold} | {item['trades_blocked']:,} | {item['trades_remaining']:,} | "
            f"{original['avg_r']:.4f} | {filtered['avg_r']:.4f} | "
            f"{original['profit_factor']:.4f} | {filtered['profit_factor']:.4f} | "
            f"{original['max_drawdown_r']:.2f} | {filtered['max_drawdown_r']:.2f} |"
        )
    return "\n".join(rows)


def importance_table(importance: pd.DataFrame) -> str:
    rows = ["| Feature | Importance mean | Importance std |", "| --- | ---: | ---: |"]
    for _, row in importance.iterrows():
        rows.append(
            f"| `{row['feature']}` | {float(row['importance_mean']):.6f} | {float(row['importance_std']):.6f} |"
        )
    return "\n".join(rows)


def interpretation(metrics: dict[str, Any]) -> str:
    test = metrics["classification"]["test"]
    filters = metrics["filter_simulation"]["test"]
    best = max(filters.items(), key=lambda kv: (kv[1]["filtered"]["avg_r"], kv[1]["filtered"]["profit_factor"]))
    threshold, item = best
    original = item["original"]
    filtered = item["filtered"]
    effect = "improves" if filtered["avg_r"] > original["avg_r"] and filtered["profit_factor"] > original["profit_factor"] else "does not improve"
    return (
        f"On test, macro F1 is `{test['macro_f1']:.4f}` and DETERIORATING recall is "
        f"`{test['per_class']['DETERIORATING']['recall']:.4f}`. Best threshold by filtered avg R/PF is "
        f"`{threshold}`, which {effect} Baltasar from avg R `{original['avg_r']:.4f}` / PF "
        f"`{original['profit_factor']:.4f}` to avg R `{filtered['avg_r']:.4f}` / PF "
        f"`{filtered['profit_factor']:.4f}`."
    )


def value_counts(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.fillna("NULL").value_counts(dropna=False).to_dict().items()}


def round_float(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
