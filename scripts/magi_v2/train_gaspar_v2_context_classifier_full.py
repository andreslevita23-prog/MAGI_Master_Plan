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
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.utils.class_weight import compute_sample_weight
from pandas.api.types import is_numeric_dtype


DEFAULT_DATASET = Path("data/output/magi_v2/gaspar_v2_dataset_full/gaspar_v2_dataset_full.parquet")
DEFAULT_TRAIN = Path("data/output/magi_v2/gaspar_v2_dataset_full/train.parquet")
DEFAULT_VALIDATION = Path("data/output/magi_v2/gaspar_v2_dataset_full/validation.parquet")
DEFAULT_TEST = Path("data/output/magi_v2/gaspar_v2_dataset_full/test.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/gaspar_v2_context_classifier_full")
DEFAULT_DOC = Path("docs/gaspar_v2_context_classifier_full.md")

TARGET = "context_quality_rr2"
LABELS = ["FAVORABLE", "NEUTRAL", "UNFAVORABLE"]
BLOCK_THRESHOLDS = [0.50, 0.60, 0.70]
Q2_START = pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
Q2_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")

FORBIDDEN_FEATURES = {
    TARGET,
    "timestamp",
    "symbol",
    "split",
    "year",
    "quarter",
    "month",
    "prediction",
    "realized_R",
    "abs_realized_R",
    "policy_threshold",
    "selected_at_050",
    "base_prediction_040",
    "policy_prediction_040",
    "baltasar_max_prob_040",
    "base_prediction_050",
    "policy_prediction_050",
    "baltasar_max_prob_050",
    "tradeable_direction_rr2_first_touch",
    "buy_R",
    "sell_R",
    "buy_first_touch",
    "sell_first_touch",
    "buy_bars_to_exit",
    "sell_bars_to_exit",
    "same_bar_ambiguous_flag",
    "hour",
    "weekday",
    "session",
    "trade_key",
}


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "gaspar_v2_context_metrics.json"
    importance_path = output_dir / "gaspar_v2_feature_importance.csv"

    if args.reuse_existing and metrics_path.exists() and importance_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        importance = pd.read_csv(importance_path)
        summary = markdown_summary(metrics, importance)
        (output_dir / "gaspar_v2_context_summary.md").write_text(summary, encoding="utf-8")
        Path(args.doc).write_text(summary, encoding="utf-8")
        print(f"reused_existing=true")
        print(f"model={metrics['model_type']}")
        print(f"validation_macro_f1={metrics['classification']['validation']['macro_f1']}")
        print(f"test_macro_f1={metrics['classification']['test']['macro_f1']}")
        print(f"output_dir={output_dir}")
        return 0

    full = read_dataset(Path(args.dataset))
    train = read_dataset(Path(args.train))
    validation = read_dataset(Path(args.validation))
    test = read_dataset(Path(args.test))
    feature_columns = infer_feature_columns(full)
    verify_no_leakage(feature_columns)

    pipeline = build_pipeline(train, feature_columns)
    sample_weight = compute_sample_weight(class_weight="balanced", y=train[TARGET])
    pipeline.fit(train[feature_columns], train[TARGET], model__sample_weight=sample_weight)

    validation_pred = pipeline.predict(validation[feature_columns])
    test_pred = pipeline.predict(test[feature_columns])
    validation_proba = probability_frame(pipeline, validation[feature_columns])
    test_proba = probability_frame(pipeline, test[feature_columns])

    metrics = {
        "schema_version": "gaspar_v2_context_classifier_full_v0.1",
        "generated_at": utc_now(),
        "model_type": "HistGradientBoostingClassifier",
        "target": TARGET,
        "labels": LABELS,
        "dataset": str(args.dataset),
        "train": str(args.train),
        "validation": str(args.validation),
        "test": str(args.test),
        "rows": {
            "train": int(len(train)),
            "validation": int(len(validation)),
            "test": int(len(test)),
        },
        "feature_columns": feature_columns,
        "feature_column_count": len(feature_columns),
        "forbidden_feature_intersection": sorted(set(feature_columns) & FORBIDDEN_FEATURES),
        "classification": {
            "validation": classification_metrics(validation[TARGET], validation_pred),
            "test": classification_metrics(test[TARGET], test_pred),
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
            "Gaspar v2 is trained as a context classifier, not a directional predictor.",
            "R, first-touch labels, Baltasar labels, selected_at_050, policy decisions, direct time features and trade result columns are excluded from features.",
            "Operational simulation blocks trades when P(UNFAVORABLE) crosses the configured threshold.",
            "Feature importance uses permutation importance on a validation sample to keep runtime bounded.",
        ],
    }

    importance = feature_importance(pipeline, validation, feature_columns)
    importance.to_csv(output_dir / "gaspar_v2_feature_importance.csv", index=False)

    payload = {
        "schema_version": metrics["schema_version"],
        "trained_at": metrics["generated_at"],
        "model_type": metrics["model_type"],
        "target": TARGET,
        "labels": LABELS,
        "features": feature_columns,
        "categorical_features": categorical_columns(train, feature_columns),
        "numeric_features": numeric_columns(train, feature_columns),
        "pipeline": pipeline,
    }
    joblib.dump(payload, output_dir / "gaspar_v2_context_model.joblib")

    (output_dir / "gaspar_v2_context_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = markdown_summary(metrics, importance)
    (output_dir / "gaspar_v2_context_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")

    print(f"model=HistGradientBoostingClassifier")
    print(f"validation_macro_f1={metrics['classification']['validation']['macro_f1']}")
    print(f"test_macro_f1={metrics['classification']['test']['macro_f1']}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Gaspar v2 full context classifier.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--train", default=str(DEFAULT_TRAIN))
    parser.add_argument("--validation", default=str(DEFAULT_VALIDATION))
    parser.add_argument("--test", default=str(DEFAULT_TEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    parser.add_argument("--reuse-existing", action="store_true", help="Reuse existing model/metrics/importance to regenerate summaries.")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df


def infer_feature_columns(df: pd.DataFrame) -> list[str]:
    columns = []
    for column in df.columns:
        lower = column.lower()
        if column in FORBIDDEN_FEATURES:
            continue
        if "future" in lower or "outcome" in lower:
            continue
        columns.append(column)
    return columns


def verify_no_leakage(feature_columns: list[str]) -> None:
    leaked = sorted(set(feature_columns) & FORBIDDEN_FEATURES)
    if leaked:
        raise ValueError(f"Forbidden features found: {leaked}")


def build_pipeline(train: pd.DataFrame, feature_columns: list[str]) -> Pipeline:
    categoricals = categorical_columns(train, feature_columns)
    numerics = numeric_columns(train, feature_columns)
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


def categorical_columns(df: pd.DataFrame, feature_columns: list[str]) -> list[str]:
    return [c for c in feature_columns if not is_numeric_dtype(df[c])]


def numeric_columns(df: pd.DataFrame, feature_columns: list[str]) -> list[str]:
    return [c for c in feature_columns if is_numeric_dtype(df[c])]


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
        "confusion_matrix": {
            "labels": LABELS,
            "matrix": matrix.astype(int).tolist(),
        },
        "prediction_distribution": value_counts(pd.Series(y_pred)),
        "target_distribution": value_counts(y_true),
    }


def filter_metrics(df: pd.DataFrame, proba: pd.DataFrame) -> dict[str, Any]:
    results = {}
    p_unfavorable = proba["p_UNFAVORABLE"]
    original = trade_metrics(df)
    for threshold in BLOCK_THRESHOLDS:
        blocked = p_unfavorable >= threshold
        remaining = df.loc[~blocked].copy()
        blocked_df = df.loc[blocked].copy()
        results[f"{threshold:.2f}"] = {
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
    return {
        "original": trade_metrics(q2),
        "filters": filter_metrics(q2, q2_proba),
    }


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


def feature_importance(pipeline: Pipeline, validation: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    sample = validation.sample(n=min(5000, len(validation)), random_state=42)
    result = permutation_importance(
        pipeline,
        sample[feature_columns],
        sample[TARGET],
        scoring="f1_macro",
        n_repeats=5,
        random_state=42,
        n_jobs=1,
    )
    return (
        pd.DataFrame(
            {
                "feature": feature_columns,
                "importance_mean": result.importances_mean,
                "importance_std": result.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )


def value_counts(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.fillna("NULL").value_counts(dropna=False).to_dict().items()}


def round_float(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


def markdown_summary(metrics: dict[str, Any], importance: pd.DataFrame) -> str:
    lines = [
        "# Gaspar v2 Context Classifier Full",
        "",
        "## Scope",
        "",
        "- Gaspar v2 classifies context quality: `FAVORABLE`, `UNFAVORABLE`, `NEUTRAL`.",
        "- Gaspar does not predict direction.",
        "- R, selected_at_050, policy decisions, direct time fields, labels and future/result columns are excluded from features.",
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
        "## Gaspar Filter Simulation",
        "",
        filter_table(metrics),
        "",
        "## 2026Q2 Impact",
        "",
        q2_table(metrics),
        "",
        "## Top Feature Importance",
        "",
        importance_markdown(importance.head(20)),
        "",
        "## Interpretation",
        "",
        interpretation(metrics),
    ]
    return "\n".join(lines) + "\n"


def classification_table(metrics: dict[str, Any]) -> str:
    rows = ["| Split | Accuracy | Macro F1 | P(UNFAVORABLE) | R(UNFAVORABLE) | P(FAVORABLE) | R(FAVORABLE) |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for split in ["validation", "test"]:
        item = metrics["classification"][split]
        unf = item["per_class"]["UNFAVORABLE"]
        fav = item["per_class"]["FAVORABLE"]
        rows.append(
            f"| {split} | {item['accuracy']:.4f} | {item['macro_f1']:.4f} | "
            f"{unf['precision']:.4f} | {unf['recall']:.4f} | {fav['precision']:.4f} | {fav['recall']:.4f} |"
        )
    return "\n".join(rows)


def filter_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Split | Block threshold | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | Max DD original | Max DD filtered |",
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
        "| Threshold | Blocked | Remaining | Avg R original | Avg R filtered | PF original | PF filtered | Max DD original | Max DD filtered |",
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


def interpretation(metrics: dict[str, Any]) -> str:
    test = metrics["classification"]["test"]
    test_filters = metrics["filter_simulation"]["test"]
    best = max(
        test_filters.items(),
        key=lambda kv: (kv[1]["filtered"]["avg_r"], kv[1]["filtered"]["profit_factor"]),
    )
    threshold, item = best
    original = item["original"]
    filtered = item["filtered"]
    if filtered["avg_r"] > original["avg_r"] and filtered["profit_factor"] > original["profit_factor"]:
        effect = "improves"
    else:
        effect = "does not improve"
    return (
        f"On test, Gaspar reaches macro F1 `{test['macro_f1']:.4f}` and UNFAVORABLE recall "
        f"`{test['per_class']['UNFAVORABLE']['recall']:.4f}`. The best test filter by avg R/PF is threshold "
        f"`{threshold}`, which {effect} Baltasar v2 from avg R `{original['avg_r']:.4f}` / PF "
        f"`{original['profit_factor']:.4f}` to avg R `{filtered['avg_r']:.4f}` / PF "
        f"`{filtered['profit_factor']:.4f}`."
    )


def importance_markdown(importance: pd.DataFrame) -> str:
    rows = [
        "| feature | importance_mean | importance_std |",
        "| --- | ---: | ---: |",
    ]
    for _, row in importance.iterrows():
        rows.append(
            f"| `{row['feature']}` | {float(row['importance_mean']):.6f} | {float(row['importance_std']):.6f} |"
        )
    return "\n".join(rows)


if __name__ == "__main__":
    raise SystemExit(main())
