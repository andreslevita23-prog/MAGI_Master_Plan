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
from sklearn.metrics import classification_report, confusion_matrix


DEFAULT_DATASET = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet")
DEFAULT_MODEL = Path("data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_model.joblib")
DEFAULT_RICH_METRICS = Path("data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_metrics.json")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_v2_rich_features_model/walk_forward")
DEFAULT_DOC = Path("docs/baltasar_v2_rich_walkforward.md")

NO_TIMING_METRICS = Path("data/output/magi_v2/baltasar_v2_rich_no_timing/baltasar_v2_rich_no_timing_metrics.json")
PURE_DIRECTIONAL_METRICS = Path("data/output/magi_v2/baltasar_v2_pure_directional/baltasar_v2_pure_directional_metrics.json")

TARGET = "tradeable_direction_rr2_first_touch"
LABELS = ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"]
TRADE_LABELS = {"ENTER_BUY", "ENTER_SELL"}
THRESHOLDS = [0.40, 0.50, 0.60]
LOW_SAMPLE_TRADES = 100
OOS_START = pd.Timestamp("2024-01-01", tz="UTC")


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = joblib.load(args.model)
    pipeline = payload["pipeline"]
    feature_columns = list(payload["features"])
    verify_model_payload(payload, feature_columns)

    df = read_dataset(Path(args.dataset), feature_columns)
    logging.info("Loaded %s rows and %s model features", len(df), len(feature_columns))
    predictions = build_threshold_predictions(pipeline, df, feature_columns)

    temporal = {
        "yearly": temporal_metrics(df, predictions, "Y"),
        "quarterly": temporal_metrics(df, predictions, "Q"),
        "monthly": temporal_metrics(df, predictions, "M"),
    }
    segments = build_segment_metrics(df, predictions)
    comparisons = build_comparisons(Path(args.rich_metrics))

    write_csv(output_dir / "yearly_metrics.csv", temporal["yearly"])
    write_csv(output_dir / "quarterly_metrics.csv", temporal["quarterly"])
    write_csv(output_dir / "monthly_metrics.csv", temporal["monthly"])
    for name, rows in segments.items():
        write_csv(output_dir / f"segment_by_{name}.csv", rows)

    metrics = {
        "schema_version": "baltasar_v2_rich_walkforward_v0.1",
        "generated_at": utc_now(),
        "dataset": str(args.dataset),
        "model": str(args.model),
        "target": TARGET,
        "thresholds": [f"{threshold:.2f}" for threshold in THRESHOLDS],
        "feature_count": len(feature_columns),
        "rows": len(df),
        "date_range": {
            "start": df["timestamp"].min().isoformat(),
            "end": df["timestamp"].max().isoformat(),
        },
        "target_distribution": dict(Counter(df[TARGET].astype(str))),
        "segment_window": {
            "scope": "out_of_sample",
            "start": OOS_START.isoformat(),
            "reason": "Timing/session segments are evaluated out-of-sample to avoid train-window inflation.",
        },
        "temporal": temporal,
        "segments": segments,
        "comparisons": comparisons,
        "technical_decisions": [
            "The existing Baltasar v2 rich model is applied as-is; no retraining is performed.",
            "Operational R uses buy_R for ENTER_BUY predictions and sell_R for ENTER_SELL predictions.",
            "Low sample segments are flagged when trades < 100.",
            "ATR and daily range buckets are computed from available decision-time columns only.",
            "Comparisons are loaded from existing metrics JSON artifacts.",
        ],
    }
    (output_dir / "baltasar_v2_rich_walkforward_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    summary = markdown_summary(metrics)
    (output_dir / "baltasar_v2_rich_walkforward_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")
    logging.info("Outputs written to %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Baltasar v2 rich features walk-forward and timing segments.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Rich features parquet.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Trained rich features joblib payload.")
    parser.add_argument("--rich-metrics", default=str(DEFAULT_RICH_METRICS), help="Existing rich model metrics JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    parser.add_argument("--doc", default=str(DEFAULT_DOC), help="Documentation markdown path.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_model_payload(payload: dict[str, Any], feature_columns: list[str]) -> None:
    if payload.get("target") != TARGET:
        raise ValueError(f"Unexpected model target: {payload.get('target')}")
    forbidden = sorted(set(feature_columns) & {TARGET, "buy_R", "sell_R", "buy_first_touch", "sell_first_touch"})
    if forbidden:
        raise ValueError(f"Forbidden columns in model feature list: {forbidden}")


def read_dataset(path: Path, feature_columns: list[str]) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    required = ["timestamp", TARGET, "buy_R", "sell_R", *feature_columns]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


def build_threshold_predictions(pipeline: Any, df: pd.DataFrame, feature_columns: list[str]) -> dict[str, pd.Series]:
    probabilities = pipeline.predict_proba(df[feature_columns])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    predictions: dict[str, list[str]] = {f"{threshold:.2f}": [] for threshold in THRESHOLDS}
    for row in probabilities:
        buy_prob = float(row[buy_idx])
        sell_prob = float(row[sell_idx])
        for threshold in THRESHOLDS:
            key = f"{threshold:.2f}"
            if buy_prob >= sell_prob and buy_prob >= threshold:
                predictions[key].append("ENTER_BUY")
            elif sell_prob > buy_prob and sell_prob >= threshold:
                predictions[key].append("ENTER_SELL")
            else:
                predictions[key].append("DO_NOTHING")
    return {key: pd.Series(values, index=df.index) for key, values in predictions.items()}


def temporal_metrics(df: pd.DataFrame, predictions: dict[str, pd.Series], frequency: str) -> list[dict[str, Any]]:
    work = df.copy()
    if frequency == "Y":
        work["period"] = work["timestamp"].dt.year.astype(str)
    elif frequency == "Q":
        periods = work["timestamp"].dt.tz_convert(None).dt.to_period("Q")
        work["period"] = periods.astype(str)
    elif frequency == "M":
        periods = work["timestamp"].dt.tz_convert(None).dt.to_period("M")
        work["period"] = periods.astype(str)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")
    return grouped_metrics(work, predictions, "period")


def build_segment_metrics(df: pd.DataFrame, predictions: dict[str, pd.Series]) -> dict[str, list[dict[str, Any]]]:
    work = df[df["timestamp"] >= OOS_START].copy()
    oos_predictions = {key: values.loc[work.index] for key, values in predictions.items()}
    work["atr_bucket"] = bucket_by_quantile(work["atr"], "atr")
    work["daily_range_bucket"] = daily_range_bucket(work["daily_range_position"])
    segment_columns = {
        "hour": "hour",
        "session": "session",
        "weekday": "weekday",
        "regime": "regime",
        "atr_bucket": "atr_bucket",
        "daily_range_bucket": "daily_range_bucket",
    }
    return {name: grouped_metrics(work, oos_predictions, column) for name, column in segment_columns.items()}


def grouped_metrics(df: pd.DataFrame, predictions: dict[str, pd.Series], group_column: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    values = sorted(df[group_column].fillna("UNKNOWN").astype(str).unique())
    for threshold_key, pred in predictions.items():
        for value in values:
            mask = df[group_column].fillna("UNKNOWN").astype(str) == value
            group_df = df.loc[mask]
            group_pred = pred.loc[group_df.index]
            metrics = evaluate_predictions(group_df, group_pred)
            rows.append(
                {
                    "threshold": threshold_key,
                    "segment": value,
                    **metrics,
                    "low_sample": metrics["trades"] < LOW_SAMPLE_TRADES,
                }
            )
    return rows


def evaluate_predictions(df: pd.DataFrame, predictions: pd.Series) -> dict[str, Any]:
    y_true = df[TARGET].astype(str)
    predictions = predictions.astype(str)
    report = classification_report(y_true, predictions, labels=LABELS, output_dict=True, zero_division=0)
    matrix = confusion_matrix(y_true, predictions, labels=LABELS)
    trades = predictions.isin(TRADE_LABELS)
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    trade_r = [value for value, is_trade in zip(realized_r(df, predictions), trades, strict=False) if is_trade and value is not None]
    return {
        "rows": int(len(df)),
        "trades": int(trades.sum()),
        "coverage": round_float(safe_div(int(trades.sum()), len(df))),
        "trade_precision": precision_on_mask(y_true, predictions, trades),
        "avg_r": round_float(sum(trade_r) / len(trade_r)) if trade_r else None,
        "total_r": round_float(sum(trade_r)) if trade_r else None,
        "profit_factor": profit_factor(trade_r),
        "max_drawdown_r": round_float(max_drawdown(trade_r)),
        "buy_precision": precision_on_mask(y_true, predictions, buy_trades),
        "sell_precision": precision_on_mask(y_true, predictions, sell_trades),
        "macro_f1": round_float(report["macro avg"]["f1-score"]),
        "prediction_distribution": dict(Counter(predictions)),
        "target_distribution": dict(Counter(y_true)),
        "confusion_matrix": matrix_dict(matrix),
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


def bucket_by_quantile(series: pd.Series, prefix: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    try:
        buckets = pd.qcut(numeric, q=5, duplicates="drop")
    except ValueError:
        return pd.Series(["UNKNOWN"] * len(series), index=series.index)
    labels = []
    for value in buckets.astype(str):
        if value == "nan":
            labels.append("UNKNOWN")
        else:
            labels.append(f"{prefix}_{value}")
    return pd.Series(labels, index=series.index)


def daily_range_bucket(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    bins = [-float("inf"), 0.15, 0.35, 0.65, 0.85, float("inf")]
    labels = ["<=0.15", "0.15-0.35", "0.35-0.65", "0.65-0.85", ">0.85"]
    out = pd.cut(numeric, bins=bins, labels=labels)
    return out.astype("object").where(out.notna(), "UNKNOWN").astype(str)


def build_comparisons(rich_metrics_path: Path) -> dict[str, Any]:
    rich = load_json(rich_metrics_path)
    no_timing = load_json(NO_TIMING_METRICS)
    pure = load_json(PURE_DIRECTIONAL_METRICS)
    return {
        "baltasar_v2_rich_existing": compact_thresholds(rich.get("thresholds", {})),
        "baltasar_v2_rich_no_timing": compact_thresholds(no_timing.get("thresholds", {})),
        "baltasar_v2_pure_directional": compact_pure_directional(pure),
        "baltasar_v1_signal": compact_baltasar_v1(pure),
    }


def compact_thresholds(thresholds: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for split in ["validation", "test"]:
        out[split] = {}
        for threshold in ["0.40", "0.50", "0.60"]:
            item = thresholds.get(split, {}).get(threshold, {})
            out[split][threshold] = compact_operational(item)
    return out


def compact_pure_directional(metrics: dict[str, Any]) -> dict[str, Any]:
    selected = metrics.get("selected_model")
    thresholds = metrics.get("models", {}).get(selected, {}).get("thresholds", {}) if selected else {}
    return {"selected_model": selected, **compact_thresholds(thresholds)}


def compact_baltasar_v1(metrics: dict[str, Any]) -> dict[str, Any]:
    comparison = metrics.get("comparisons", {}).get("baltasar_v1_signal", {})
    return {split: compact_operational(comparison.get(split, {})) for split in ["validation", "test"]}


def compact_operational(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "trades": item.get("trades_taken", item.get("trades")),
        "coverage": item.get("coverage"),
        "trade_precision": item.get("trade_precision"),
        "avg_r": item.get("avg_r"),
        "total_r": item.get("total_r"),
        "profit_factor": item.get("profit_factor"),
        "max_drawdown_r": item.get("max_drawdown_r"),
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: csv_value(row.get(header)) for header in headers})


def markdown_summary(metrics: dict[str, Any]) -> str:
    threshold = "0.50"
    yearly = filter_threshold(metrics["temporal"]["yearly"], threshold)
    quarterly = filter_threshold(metrics["temporal"]["quarterly"], threshold)
    monthly = filter_threshold(metrics["temporal"]["monthly"], threshold)
    monthly_oos = [row for row in monthly if row["segment"] >= "2024-01"]
    session = filter_threshold(metrics["segments"]["session"], threshold)
    hour = filter_threshold(metrics["segments"]["hour"], threshold)
    comparisons = metrics["comparisons"]
    best_months = best_rows(monthly_oos, "avg_r", 8, reverse=True)
    worst_months = best_rows(monthly_oos, "avg_r", 8, reverse=False)
    best_hours = best_rows([row for row in hour if not row["low_sample"]], "avg_r", 8, reverse=True)
    worst_hours = best_rows([row for row in hour if not row["low_sample"]], "avg_r", 8, reverse=False)
    lines = [
        "# Baltasar v2 Rich Walk-Forward",
        "",
        "## Scope",
        "",
        "- Model analyzed: `baltasar_v2_rich_model.joblib`.",
        "- No model retraining was performed.",
        "- Main threshold for stability readout: `0.50`.",
        "- Low sample flag: `trades < 100`.",
        "- Segment tables use out-of-sample rows from `2024-01-01` onward.",
        "",
        "## Annual Stability at Threshold 0.50",
        "",
        table_from_rows(summary_rows(yearly)),
        "",
        "## Quarterly Stability at Threshold 0.50",
        "",
        table_from_rows(summary_rows(quarterly)),
        "",
        "## Best OOS Months at Threshold 0.50",
        "",
        table_from_rows(summary_rows(best_months)),
        "",
        "## Worst OOS Months at Threshold 0.50",
        "",
        table_from_rows(summary_rows(worst_months)),
        "",
        "## Session Segments at Threshold 0.50",
        "",
        table_from_rows(summary_rows(session)),
        "",
        "## Best Hours at Threshold 0.50",
        "",
        table_from_rows(summary_rows(best_hours)),
        "",
        "## Worst Hours at Threshold 0.50",
        "",
        table_from_rows(summary_rows(worst_hours)),
        "",
        "## Comparison Snapshot",
        "",
        comparison_snapshot(comparisons),
        "",
        "## Interpretation",
        "",
        interpretation(metrics),
        "",
        "## Technical Decisions",
        "",
    ]
    lines.extend(f"- {item}" for item in metrics["technical_decisions"])
    return "\n".join(lines) + "\n"


def interpretation(metrics: dict[str, Any]) -> str:
    test_rich = metrics["comparisons"]["baltasar_v2_rich_existing"]["test"]["0.50"]
    test_no_timing = metrics["comparisons"]["baltasar_v2_rich_no_timing"]["test"]["0.50"]
    test_v1 = metrics["comparisons"]["baltasar_v1_signal"]["test"]
    monthly_050 = [
        row
        for row in metrics["temporal"]["monthly"]
        if row["threshold"] == "0.50" and row["segment"] >= "2024-01" and not row["low_sample"]
    ]
    positive_months = sum(1 for row in monthly_050 if (row["avg_r"] or 0) > 0)
    total_months = len(monthly_050)
    return (
        f"At threshold 0.50, rich with timing has test avg R `{format_value(test_rich.get('avg_r'))}` and PF "
        f"`{format_value(test_rich.get('profit_factor'))}`, versus no_timing avg R "
        f"`{format_value(test_no_timing.get('avg_r'))}` and Baltasar v1 avg R "
        f"`{format_value(test_v1.get('avg_r'))}`. Positive months with adequate sample are "
        f"`{positive_months}/{total_months}`. The timing variables appear useful rather than purely decorative, "
        "but the month-to-month dispersion means they should be constrained with walk-forward policy tests before "
        "replacing Baltasar v1."
    )


def comparison_snapshot(comparisons: dict[str, Any]) -> str:
    rows = []
    for name, data in [
        ("rich_timing", comparisons["baltasar_v2_rich_existing"]),
        ("rich_no_timing", comparisons["baltasar_v2_rich_no_timing"]),
        ("pure_directional", comparisons["baltasar_v2_pure_directional"]),
    ]:
        for split in ["validation", "test"]:
            for threshold in ["0.40", "0.50", "0.60"]:
                item = data.get(split, {}).get(threshold, {})
                rows.append({"model": name, "split": split, "threshold": threshold, **item})
    for split in ["validation", "test"]:
        item = comparisons["baltasar_v1_signal"].get(split, {})
        rows.append({"model": "baltasar_v1_signal", "split": split, "threshold": "signal", **item})
    return table_from_rows(rows)


def filter_threshold(rows: list[dict[str, Any]], threshold: str) -> list[dict[str, Any]]:
    return [row for row in rows if row["threshold"] == threshold]


def best_rows(rows: list[dict[str, Any]], key: str, n: int, reverse: bool) -> list[dict[str, Any]]:
    valid = [row for row in rows if row.get(key) is not None]
    return sorted(valid, key=lambda row: row[key], reverse=reverse)[:n]


def summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "segment": row["segment"],
            "rows": row["rows"],
            "trades": row["trades"],
            "coverage": row["coverage"],
            "trade_precision": row["trade_precision"],
            "avg_r": row["avg_r"],
            "total_r": row["total_r"],
            "PF": row["profit_factor"],
            "max_DD": row["max_drawdown_r"],
            "BUY_precision": row["buy_precision"],
            "SELL_precision": row["sell_precision"],
            "low_sample": row["low_sample"],
        }
        for row in rows
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


def safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def round_float(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


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


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
