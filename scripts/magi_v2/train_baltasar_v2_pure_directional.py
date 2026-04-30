from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from collections import Counter
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
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.utils.class_weight import compute_sample_weight


DEFAULT_INPUT = Path("data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_v2_pure_directional")
PREVIOUS_BASELINE_METRICS = Path("data/output/magi_v2/baltasar_v2_baseline/baltasar_v2_baseline_metrics.json")

TARGET = "tradeable_direction_rr2_first_touch"
LABELS = ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"]
THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70]

TRAIN_START = "2020-01-15"
TRAIN_END = "2023-12-31 23:59:59"
VALIDATION_START = "2024-01-01"
VALIDATION_END = "2024-12-31 23:59:59"
TEST_START = "2025-01-01"
TEST_END = "2026-04-14 23:59:59"

CATEGORICAL_FEATURES = ["session", "weekday", "regime"]
NUMERIC_FEATURES = ["hour", "spread_pips", "atr", "daily_range_position"]
FEATURES = ["session", "hour", "weekday", "spread_pips", "atr", "daily_range_position", "regime"]

FORBIDDEN_FEATURES = {
    "melchor_signal",
    "melchor_confidence",
    "melchor_risk_flags",
    "baltasar_signal",
    "baltasar_confidence",
    "gaspar_signal",
    "gaspar_confidence",
    "mage_agreement",
    "baltasar_gaspar_alignment",
    "buy_outcome",
    "sell_outcome",
    "buy_R",
    "sell_R",
    "buy_first_touch",
    "sell_first_touch",
    "buy_bars_to_exit",
    "sell_bars_to_exit",
    "same_bar_ambiguous_flag",
    TARGET,
    "future_outcome_h12",
    "future_outcome_h48",
    "future_outcome_h96",
    "future_outcome_h288",
    "future_return",
    "future_return_pips",
    "max_favorable_excursion",
    "max_adverse_excursion",
}

EVAL_REQUIRED = ["timestamp", "buy_R", "sell_R", "baltasar_signal", TARGET]


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    verify_no_leakage()

    df = read_dataset(Path(args.input))
    train_df, validation_df, test_df = split_temporally(df)
    train_df.to_parquet(output_dir / "train.parquet", index=False)
    validation_df.to_parquet(output_dir / "validation.parquet", index=False)
    test_df.to_parquet(output_dir / "test.parquet", index=False)
    logging.info("Split rows train=%s validation=%s test=%s", len(train_df), len(validation_df), len(test_df))

    candidates = train_candidates(train_df)
    metrics = build_metrics(candidates, train_df, validation_df, test_df)
    best_name = select_best_model(metrics)
    best_pipeline = candidates[best_name]

    payload = {
        "schema_version": "baltasar_v2_pure_directional_model_v0.1",
        "trained_at": utc_now(),
        "model_type": best_name,
        "target": TARGET,
        "features": FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "pipeline": best_pipeline,
        "selection_rule": "Highest validation best-threshold avg_r, then profit_factor, then trade_precision.",
    }
    joblib.dump(payload, output_dir / "baltasar_v2_pure_directional_model.joblib")
    metrics["selected_model"] = best_name
    metrics["selection_rule"] = payload["selection_rule"]
    (output_dir / "baltasar_v2_pure_directional_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    importances = feature_importances(best_name, best_pipeline, validation_df)
    write_feature_importance(output_dir / "baltasar_v2_pure_directional_feature_importance.csv", importances)
    (output_dir / "baltasar_v2_pure_directional_summary.md").write_text(markdown_summary(metrics, importances), encoding="utf-8")
    logging.info("Selected model: %s", best_name)
    logging.info("Outputs written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train pure directional Baltasar v2 baselines.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="RR2 first-touch labels parquet.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_no_leakage() -> None:
    forbidden = sorted(set(FEATURES) & FORBIDDEN_FEATURES)
    if forbidden:
        raise ValueError(f"Forbidden columns in FEATURES: {forbidden}")


def read_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    missing = [column for column in [*FEATURES, *EVAL_REQUIRED] if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df.sort_values("timestamp").reset_index(drop=True)


def split_temporally(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        between(df, TRAIN_START, TRAIN_END),
        between(df, VALIDATION_START, VALIDATION_END),
        between(df, TEST_START, TEST_END),
    )


def between(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    return df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)].copy()


def train_candidates(train_df: pd.DataFrame) -> dict[str, Pipeline]:
    candidates = {
        "RandomForestClassifier": build_pipeline(
            RandomForestClassifier(
                n_estimators=180,
                max_depth=12,
                min_samples_leaf=90,
                class_weight="balanced_subsample",
                random_state=303,
                n_jobs=1,
            )
        ),
        "HistGradientBoostingClassifier": build_pipeline(
            HistGradientBoostingClassifier(
                max_iter=20,
                learning_rate=0.10,
                max_leaf_nodes=15,
                l2_regularization=0.02,
                early_stopping=True,
                validation_fraction=0.12,
                n_iter_no_change=8,
                random_state=404,
            )
        ),
    }
    for name, pipeline in candidates.items():
        logging.info("Training %s", name)
        if name == "HistGradientBoostingClassifier":
            hgb_train = stratified_sample(train_df, max_rows=12000, random_state=414)
            weights = compute_sample_weight(class_weight="balanced", y=hgb_train[TARGET])
            pipeline.fit(hgb_train[FEATURES], hgb_train[TARGET], model__sample_weight=weights)
        else:
            pipeline.fit(train_df[FEATURES], train_df[TARGET])
    return candidates


def stratified_sample(df: pd.DataFrame, max_rows: int, random_state: int) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df
    fractions = df[TARGET].value_counts(normalize=True)
    pieces = []
    for label, fraction in fractions.items():
        label_df = df[df[TARGET] == label]
        n = max(1, int(round(max_rows * float(fraction))))
        pieces.append(label_df.sample(n=min(n, len(label_df)), random_state=random_state))
    return pd.concat(pieces, ignore_index=True).sample(frac=1.0, random_state=random_state).reset_index(drop=True)


def build_pipeline(model: Any) -> Pipeline:
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    numeric = Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))])
    preprocess = ColumnTransformer(
        transformers=[
            ("categorical", categorical, CATEGORICAL_FEATURES),
            ("numeric", numeric, NUMERIC_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def build_metrics(
    candidates: dict[str, Pipeline],
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict[str, Any]:
    frames = {"train": train_df, "validation": validation_df, "test": test_df}
    model_metrics = {}
    for name, pipeline in candidates.items():
        model_metrics[name] = {
            "argmax": {
                split: evaluate_predictions(frame, pd.Series(pipeline.predict(frame[FEATURES]), index=frame.index))
                for split, frame in frames.items()
            },
            "thresholds": {
                split: {f"{th:.2f}": evaluate_predictions(frame, threshold_predictions(pipeline, frame, th)) for th in THRESHOLDS}
                for split, frame in frames.items()
            },
        }
    comparisons = {
        "always_do_nothing": {split: evaluate_predictions(frame, pd.Series(["DO_NOTHING"] * len(frame), index=frame.index)) for split, frame in frames.items()},
        "baltasar_v1_signal": {split: evaluate_predictions(frame, baltasar_v1_predictions(frame)) for split, frame in frames.items()},
    }
    previous = load_previous_baseline()
    return {
        "schema_version": "baltasar_v2_pure_directional_metrics_v0.1",
        "generated_at": utc_now(),
        "target": TARGET,
        "features": FEATURES,
        "leakage_check": {"passed": True, "forbidden_features_in_model": []},
        "splits": {
            split: {
                "rows": len(frame),
                "start": frame["timestamp"].min().isoformat(),
                "end": frame["timestamp"].max().isoformat(),
                "target_distribution": dict(Counter(frame[TARGET])),
            }
            for split, frame in frames.items()
        },
        "models": model_metrics,
        "comparisons": comparisons,
        "previous_baltasar_v2_baseline": previous,
        "technical_decisions": [
            "Only session/hour/weekday/spread_pips/atr/daily_range_position/regime are used as features.",
            "No mage votes, Baltasar v1 signal, first-touch diagnostics, R values, labels, or future outcomes are used as features.",
            "buy_R and sell_R are used only for evaluation.",
            "HistGradientBoostingClassifier receives balanced sample weights.",
            "The saved model is selected by validation threshold avg_r, then PF, then trade precision.",
        ],
    }


def threshold_predictions(pipeline: Pipeline, df: pd.DataFrame, threshold: float) -> pd.Series:
    probabilities = pipeline.predict_proba(df[FEATURES])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    out: list[str] = []
    for row in probabilities:
        buy_prob = float(row[buy_idx])
        sell_prob = float(row[sell_idx])
        if buy_prob >= sell_prob and buy_prob >= threshold:
            out.append("ENTER_BUY")
        elif sell_prob > buy_prob and sell_prob >= threshold:
            out.append("ENTER_SELL")
        else:
            out.append("DO_NOTHING")
    return pd.Series(out, index=df.index)


def baltasar_v1_predictions(df: pd.DataFrame) -> pd.Series:
    signal = df["baltasar_signal"].fillna("").astype(str).str.upper()
    mapped = signal.map({"BUY": "ENTER_BUY", "SELL": "ENTER_SELL"})
    return mapped.fillna("DO_NOTHING")


def evaluate_predictions(df: pd.DataFrame, predictions: pd.Series) -> dict[str, Any]:
    y_true = df[TARGET].astype(str)
    predictions = predictions.astype(str)
    report = classification_report(y_true, predictions, labels=LABELS, output_dict=True, zero_division=0)
    matrix = confusion_matrix(y_true, predictions, labels=LABELS)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    trade_r = [value for value, is_trade in zip(realized_r(df, predictions), trades, strict=False) if is_trade and value is not None]
    return {
        "accuracy": round_float(accuracy_score(y_true, predictions)),
        "macro_f1": round_float(f1_score(y_true, predictions, labels=LABELS, average="macro", zero_division=0)),
        "precision_by_class": {label: round_float(report[label]["precision"]) for label in LABELS},
        "recall_by_class": {label: round_float(report[label]["recall"]) for label in LABELS},
        "confusion_matrix": matrix_dict(matrix),
        "actual_distribution": dict(Counter(y_true)),
        "prediction_distribution": dict(Counter(predictions)),
        "trades_taken": int(trades.sum()),
        "coverage": round_float(safe_div(trades.sum(), len(predictions))),
        "trade_precision": precision_on_mask(y_true, predictions, trades),
        "buy_precision": precision_on_mask(y_true, predictions, buy_trades),
        "sell_precision": precision_on_mask(y_true, predictions, sell_trades),
        "avg_r": round_float(sum(trade_r) / len(trade_r)) if trade_r else None,
        "total_r": round_float(sum(trade_r)) if trade_r else None,
        "profit_factor": profit_factor(trade_r),
        "max_drawdown_r": round_float(max_drawdown(trade_r)),
    }


def realized_r(df: pd.DataFrame, predictions: pd.Series) -> list[float | None]:
    out: list[float | None] = []
    for pred, buy_r, sell_r in zip(predictions, df["buy_R"], df["sell_R"], strict=False):
        if pred == "ENTER_BUY":
            out.append(as_float(buy_r))
        elif pred == "ENTER_SELL":
            out.append(as_float(sell_r))
        else:
            out.append(0.0)
    return out


def select_best_model(metrics: dict[str, Any]) -> str:
    best_name = ""
    best_score = (-10**9, -10**9, -10**9)
    for name, data in metrics["models"].items():
        for threshold_data in data["thresholds"]["validation"].values():
            if threshold_data["trades_taken"] <= 0:
                continue
            score = (
                threshold_data["avg_r"] if threshold_data["avg_r"] is not None else -10**9,
                threshold_data["profit_factor"] if threshold_data["profit_factor"] is not None else -10**9,
                threshold_data["trade_precision"] if threshold_data["trade_precision"] is not None else -10**9,
            )
            if score > best_score:
                best_score = score
                best_name = name
    if best_name:
        return best_name
    return max(metrics["models"], key=lambda model_name: metrics["models"][model_name]["argmax"]["validation"]["macro_f1"])


def feature_importances(model_name: str, pipeline: Pipeline, validation_df: pd.DataFrame) -> list[dict[str, Any]]:
    if hasattr(pipeline.named_steps["model"], "feature_importances_"):
        names = list(pipeline.named_steps["preprocess"].get_feature_names_out())
        rows = [
            {"feature": name, "importance": round_float(float(value), 10), "method": "native"}
            for name, value in zip(names, pipeline.named_steps["model"].feature_importances_, strict=False)
        ]
        rows.sort(key=lambda row: row["importance"], reverse=True)
        return rows
    sample = validation_df.sample(n=min(15000, len(validation_df)), random_state=505)
    result = permutation_importance(
        pipeline,
        sample[FEATURES],
        sample[TARGET],
        n_repeats=3,
        random_state=606,
        scoring="f1_macro",
        n_jobs=1,
    )
    rows = [
        {"feature": feature, "importance": round_float(float(mean), 10), "method": "permutation_f1_macro"}
        for feature, mean in zip(FEATURES, result.importances_mean, strict=False)
    ]
    rows.sort(key=lambda row: row["importance"], reverse=True)
    return rows


def load_previous_baseline() -> dict[str, Any]:
    if not PREVIOUS_BASELINE_METRICS.exists():
        return {"available": False}
    with PREVIOUS_BASELINE_METRICS.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {
        "available": True,
        "validation_argmax": slim_metrics(data["metrics_argmax"]["validation"]),
        "test_argmax": slim_metrics(data["metrics_argmax"]["test"]),
    }


def slim_metrics(row: dict[str, Any]) -> dict[str, Any]:
    keys = ["trades_taken", "coverage", "trade_precision", "avg_r", "total_r", "profit_factor", "max_drawdown_r"]
    return {key: row.get(key) for key in keys}


def write_feature_importance(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["feature", "importance", "method"])
        writer.writeheader()
        writer.writerows(rows)


def markdown_summary(metrics: dict[str, Any], importances: list[dict[str, Any]]) -> str:
    lines = [
        "# Baltasar v2 Pure Directional",
        "",
        "## Scope",
        "",
        f"- Target: `{TARGET}`.",
        f"- Selected model: `{metrics['selected_model']}`.",
        "- Features: session, hour, weekday, spread_pips, atr, daily_range_position, regime.",
        "- No mage votes, Baltasar v1 signal, first-touch outputs, R values, or future outcomes are used as features.",
        "",
        "## Splits",
        "",
        table_from_rows(split_rows(metrics)),
        "",
        "## Validation Threshold Metrics",
        "",
    ]
    for model_name in metrics["models"]:
        lines.extend([f"### {model_name}", "", threshold_table(metrics, model_name, "validation"), ""])
    lines.extend(["## Test Threshold Metrics", ""])
    for model_name in metrics["models"]:
        lines.extend([f"### {model_name}", "", threshold_table(metrics, model_name, "test"), ""])
    lines.extend(
        [
            "## Comparisons",
            "",
            "### Baltasar v1 signal",
            "",
            comparison_table(metrics["comparisons"]["baltasar_v1_signal"]),
            "",
            "### Previous Baltasar v2 baseline",
            "",
            table_from_rows(previous_rows(metrics["previous_baltasar_v2_baseline"])),
            "",
            "## Feature Importance",
            "",
            table_from_rows(importances[:20]),
            "",
            "## Leakage Check",
            "",
            f"- Passed: `{metrics['leakage_check']['passed']}`",
            f"- Forbidden features in model: `{metrics['leakage_check']['forbidden_features_in_model']}`",
            "",
            "## Technical Notes",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in metrics["technical_decisions"])
    return "\n".join(lines) + "\n"


def split_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "split": split,
            "rows": data["rows"],
            "DO_NOTHING": data["target_distribution"].get("DO_NOTHING", 0),
            "ENTER_BUY": data["target_distribution"].get("ENTER_BUY", 0),
            "ENTER_SELL": data["target_distribution"].get("ENTER_SELL", 0),
        }
        for split, data in metrics["splits"].items()
    ]


def threshold_table(metrics: dict[str, Any], model_name: str, split: str) -> str:
    rows = []
    for threshold, data in metrics["models"][model_name]["thresholds"][split].items():
        rows.append(
            {
                "threshold": threshold,
                "trades": data["trades_taken"],
                "coverage": data["coverage"],
                "trade_precision": data["trade_precision"],
                "avg_r": data["avg_r"],
                "total_r": data["total_r"],
                "PF": data["profit_factor"],
                "max_DD": data["max_drawdown_r"],
                "BUY_precision": data["buy_precision"],
                "SELL_precision": data["sell_precision"],
            }
        )
    return table_from_rows(rows)


def comparison_table(data: dict[str, Any]) -> str:
    return table_from_rows(
        [
            {
                "split": split,
                "trades": row["trades_taken"],
                "coverage": row["coverage"],
                "trade_precision": row["trade_precision"],
                "avg_r": row["avg_r"],
                "total_r": row["total_r"],
                "PF": row["profit_factor"],
                "max_DD": row["max_drawdown_r"],
            }
            for split, row in data.items()
        ]
    )


def previous_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    if not data.get("available"):
        return [{"available": False}]
    return [
        {"split": "validation", **data["validation_argmax"]},
        {"split": "test", **data["test_argmax"]},
    ]


def table_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(format_value(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def matrix_dict(matrix: Any) -> dict[str, dict[str, int]]:
    return {actual: {pred: int(matrix[i][j]) for j, pred in enumerate(LABELS)} for i, actual in enumerate(LABELS)}


def precision_on_mask(y_true: pd.Series, predictions: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if total == 0:
        return None
    return round_float((y_true[mask] == predictions[mask]).sum() / total)


def profit_factor(values: list[float | None]) -> float | None:
    wins = [value for value in values if value is not None and value > 0]
    losses = [value for value in values if value is not None and value < 0]
    gross_loss = abs(sum(losses))
    if gross_loss == 0:
        return None
    return round_float(sum(wins) / gross_loss)


def max_drawdown(values: list[float | None]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in values:
        if value is None:
            continue
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def round_float(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


if __name__ == "__main__":
    raise SystemExit(main())
