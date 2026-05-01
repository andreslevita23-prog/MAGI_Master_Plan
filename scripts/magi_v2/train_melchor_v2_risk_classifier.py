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


DEFAULT_DATASET = Path("data/output/magi_v2/melchor_v2_risk_dataset/melchor_v2_risk_dataset.parquet")
DEFAULT_SUMMARY = Path("data/output/magi_v2/melchor_v2_risk_dataset/melchor_v2_risk_dataset_summary.json")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/melchor_v2_risk_classifier")
DEFAULT_DOC = Path("docs/melchor_v2_risk_classifier.md")

TARGET = "risk_block_rr2"
STRICT_TARGET = "risk_block_rr2_strict"
LABELS = ["APPROVE", "CAUTION", "BLOCK"]
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
    "future_sample_size_50",
    "future_avg_R_50",
    "future_pf_50",
    "future_drawdown_50",
    "future_sell_sample_size_50",
    "future_sell_avg_R_50",
    "future_sell_pf_50",
    "future_sell_drawdown_50",
    "risk_block_rr2",
    "risk_block_rr2_strict",
    "risk_block_rr2_soft",
    "is_2026q2",
}


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = read_dataset(Path(args.dataset))
    summary = read_summary(Path(args.summary))
    features = infer_features(df, summary)
    verify_no_leakage(features)

    train = df[df["split"].eq("train")].copy()
    validation = df[df["split"].eq("validation")].copy()
    test = df[df["split"].eq("test")].copy()

    pipeline = build_pipeline(train, features)
    sample_weight = compute_sample_weight(class_weight="balanced", y=train[TARGET])
    pipeline.fit(train[features], train[TARGET], model__sample_weight=sample_weight)

    validation_pred = pipeline.predict(validation[features])
    test_pred = pipeline.predict(test[features])

    metrics = {
        "schema_version": "melchor_v2_risk_classifier_v0.1",
        "generated_at": utc_now(),
        "model_type": "HistGradientBoostingClassifier",
        "dataset": str(args.dataset),
        "target": TARGET,
        "diagnostic_target": STRICT_TARGET,
        "labels": LABELS,
        "rows": {
            "train": int(len(train)),
            "validation": int(len(validation)),
            "test": int(len(test)),
        },
        "feature_columns": features,
        "feature_column_count": len(features),
        "forbidden_feature_intersection": sorted(set(features) & FORBIDDEN_FEATURES),
        "target_distribution": {
            "train": value_counts(train[TARGET]),
            "validation": value_counts(validation[TARGET]),
            "test": value_counts(test[TARGET]),
        },
        "strict_target_distribution": {
            "train": value_counts(train[STRICT_TARGET]),
            "validation": value_counts(validation[STRICT_TARGET]),
            "test": value_counts(test[STRICT_TARGET]),
        },
        "classification": {
            "validation": classification_metrics(validation[TARGET], validation_pred),
            "test": classification_metrics(test[TARGET], test_pred),
        },
        "strict_target_alignment": {
            "validation": classification_metrics(validation[STRICT_TARGET], validation_pred),
            "test": classification_metrics(test[STRICT_TARGET], test_pred),
        },
        "filter_simulation": {
            "validation": filter_metrics(validation, validation_pred),
            "test": filter_metrics(test, test_pred),
        },
        "baseline_original": {
            "validation": trade_metrics(validation),
            "test": trade_metrics(test),
        },
        "q2_2026": q2_metrics(test, test_pred),
        "technical_decisions": [
            "Melchor v2 predicts accumulated risk state, not direction or technical context.",
            "Only feature columns declared by the Melchor risk dataset summary are used.",
            "Realized R, future R/PF/DD diagnostics, labels, split/date flags and 2026Q2 flags are excluded from features.",
            "Operational filtering is evaluated in two modes: block only predicted BLOCK, and block predicted BLOCK plus CAUTION.",
            "The model is experimental and does not replace Melchor v1.",
        ],
    }

    importance = feature_importance(pipeline, validation, features)
    importance.to_csv(output_dir / "melchor_v2_feature_importance.csv", index=False)

    joblib.dump(
        {
            "schema_version": metrics["schema_version"],
            "trained_at": metrics["generated_at"],
            "model_type": metrics["model_type"],
            "target": TARGET,
            "diagnostic_target": STRICT_TARGET,
            "labels": LABELS,
            "features": features,
            "categorical_features": categorical_columns(train, features),
            "numeric_features": numeric_columns(train, features),
            "pipeline": pipeline,
        },
        output_dir / "melchor_v2_risk_model.joblib",
    )
    (output_dir / "melchor_v2_risk_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary_md = markdown_summary(metrics, importance)
    (output_dir / "melchor_v2_risk_summary.md").write_text(summary_md, encoding="utf-8")
    Path(args.doc).write_text(summary_md, encoding="utf-8")

    print("model=HistGradientBoostingClassifier")
    print(f"validation_macro_f1={metrics['classification']['validation']['macro_f1']}")
    print(f"test_macro_f1={metrics['classification']['test']['macro_f1']}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Melchor v2 accumulated risk classifier.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
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


def read_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def infer_features(df: pd.DataFrame, summary: dict[str, Any]) -> list[str]:
    features = [column for column in summary.get("feature_columns", []) if column in df.columns]
    filtered: list[str] = []
    for column in features:
        lower = column.lower()
        if column in FORBIDDEN_FEATURES:
            continue
        if "future" in lower or "target" in lower or "label" in lower:
            continue
        filtered.append(column)
    return list(dict.fromkeys(filtered))


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
            ("cat", Pipeline(steps=[("impute", SimpleImputer(strategy="most_frequent")), ("onehot", encoder)]), categoricals),
        ],
        remainder="drop",
    )
    model = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=250,
        max_leaf_nodes=31,
        l2_regularization=0.1,
        random_state=42,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def categorical_columns(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [column for column in features if not is_numeric_dtype(df[column])]


def numeric_columns(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [column for column in features if is_numeric_dtype(df[column])]


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
        "block_precision": round_float(report["BLOCK"]["precision"]),
        "block_recall": round_float(report["BLOCK"]["recall"]),
        "confusion_matrix": {"labels": LABELS, "matrix": matrix.astype(int).tolist()},
        "prediction_distribution": value_counts(pd.Series(y_pred)),
        "target_distribution": value_counts(y_true),
    }


def filter_metrics(df: pd.DataFrame, predictions: Any) -> dict[str, Any]:
    pred = pd.Series(predictions, index=df.index)
    original = trade_metrics(df)
    modes = {
        "block_only": pred.eq("BLOCK"),
        "block_plus_caution": pred.isin(["BLOCK", "CAUTION"]),
    }
    results = {}
    for mode, blocked in modes.items():
        remaining = df.loc[~blocked].copy()
        blocked_df = df.loc[blocked].copy()
        results[mode] = {
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


def q2_metrics(test: pd.DataFrame, predictions: Any) -> dict[str, Any]:
    pred = pd.Series(predictions, index=test.index)
    mask = test["timestamp"].between(Q2_START, Q2_END)
    q2 = test.loc[mask].copy()
    q2_pred = pred.loc[q2.index]
    return {"original": trade_metrics(q2), "filters": filter_metrics(q2, q2_pred)}


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
        "# Melchor v2 Risk Classifier",
        "",
        "## Scope",
        "",
        "- Target: `risk_block_rr2`.",
        "- Diagnostic target: `risk_block_rr2_strict`.",
        "- Melchor v2 evaluates accumulated risk before a candidate trade; it does not predict direction.",
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
        "## Operational Filter",
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
        "| Split | Accuracy | Macro F1 | P(BLOCK) | R(BLOCK) | P(APPROVE) | R(APPROVE) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ["validation", "test"]:
        item = metrics["classification"][split]
        block = item["per_class"]["BLOCK"]
        approve = item["per_class"]["APPROVE"]
        rows.append(
            f"| {split} | {item['accuracy']:.4f} | {item['macro_f1']:.4f} | "
            f"{block['precision']:.4f} | {block['recall']:.4f} | "
            f"{approve['precision']:.4f} | {approve['recall']:.4f} |"
        )
    return "\n".join(rows)


def filter_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Split | Mode | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | DD original | DD filtered |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ["validation", "test"]:
        for mode, item in metrics["filter_simulation"][split].items():
            original = item["original"]
            filtered = item["filtered"]
            rows.append(
                f"| {split} | {mode} | {item['trades_blocked']:,} | {item['trades_remaining']:,} | "
                f"{original['avg_r']:.4f} | {filtered['avg_r']:.4f} | "
                f"{original['profit_factor']:.4f} | {filtered['profit_factor']:.4f} | "
                f"{original['max_drawdown_r']:.2f} | {filtered['max_drawdown_r']:.2f} |"
            )
    return "\n".join(rows)


def q2_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Mode | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | DD original | DD filtered |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode, item in metrics["q2_2026"]["filters"].items():
        original = item["original"]
        filtered = item["filtered"]
        rows.append(
            f"| {mode} | {item['trades_blocked']:,} | {item['trades_remaining']:,} | "
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
    candidates = []
    for mode, item in filters.items():
        original = item["original"]
        filtered = item["filtered"]
        candidates.append(
            (
                mode,
                filtered["avg_r"] - original["avg_r"],
                filtered["profit_factor"] - original["profit_factor"],
                original["max_drawdown_r"] - filtered["max_drawdown_r"],
                item,
            )
        )
    best = max(candidates, key=lambda row: (row[1], row[2], row[3]))
    mode, _, _, _, item = best
    original = item["original"]
    filtered = item["filtered"]
    return (
        f"On test, macro F1 is `{test['macro_f1']:.4f}`, BLOCK precision is "
        f"`{test['per_class']['BLOCK']['precision']:.4f}` and BLOCK recall is "
        f"`{test['per_class']['BLOCK']['recall']:.4f}`. Best operational mode by avg R/PF is "
        f"`{mode}`, moving from avg R `{original['avg_r']:.4f}` / PF "
        f"`{original['profit_factor']:.4f}` / DD `{original['max_drawdown_r']:.2f}` to avg R "
        f"`{filtered['avg_r']:.4f}` / PF `{filtered['profit_factor']:.4f}` / DD "
        f"`{filtered['max_drawdown_r']:.2f}`."
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
