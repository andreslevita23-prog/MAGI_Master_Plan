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


DEFAULT_MODEL = Path("data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_model.joblib")
DEFAULT_DATASET = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_v2_rich_features_model/policy")
DEFAULT_DOC = Path("docs/baltasar_v2_rich_policy.md")

RICH_METRICS = Path("data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_metrics.json")
NO_TIMING_METRICS = Path("data/output/magi_v2/baltasar_v2_rich_no_timing/baltasar_v2_rich_no_timing_metrics.json")
COARSE_METRICS = Path("data/output/magi_v2/baltasar_v2_rich_coarse_timing/baltasar_v2_rich_coarse_timing_metrics.json")
PURE_METRICS = Path("data/output/magi_v2/baltasar_v2_pure_directional/baltasar_v2_pure_directional_metrics.json")

TARGET = "tradeable_direction_rr2_first_touch"
LABELS = ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"]
THRESHOLDS = [0.40, 0.50]
BAD_HOURS = {13, 15, 16, 20, 22}
TRAIN_END = pd.Timestamp("2023-12-31 23:59:59", tz="UTC")
VALIDATION_END = pd.Timestamp("2024-12-31 23:59:59", tz="UTC")
TEST_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = joblib.load(args.model)
    pipeline = payload["pipeline"]
    feature_columns = list(payload["features"])
    verify_payload(payload, feature_columns)

    df = read_dataset(Path(args.dataset), feature_columns)
    logging.info("Loaded %s rows and %s features", len(df), len(feature_columns))
    base_predictions = build_threshold_predictions(pipeline, df, feature_columns)

    policy_predictions = build_policy_predictions(df, base_predictions)
    variant_rows = build_variant_rows(df, policy_predictions)
    yearly_rows = grouped_rows(df, policy_predictions, "year")
    quarterly_rows = grouped_rows(df, policy_predictions, "quarter")
    monthly_rows = grouped_rows(df, policy_predictions, "month")
    trades_rows = selected_trade_rows(df, policy_predictions)

    write_csv(output_dir / "policy_by_variant.csv", variant_rows)
    write_csv(output_dir / "policy_by_year.csv", yearly_rows)
    write_csv(output_dir / "policy_by_quarter.csv", quarterly_rows)
    write_csv(output_dir / "policy_by_month.csv", monthly_rows)
    write_csv(output_dir / "policy_trades.csv", trades_rows)

    metrics = {
        "schema_version": "baltasar_v2_rich_policy_v0.1",
        "generated_at": utc_now(),
        "model": str(args.model),
        "dataset": str(args.dataset),
        "thresholds": [f"{threshold:.2f}" for threshold in THRESHOLDS],
        "bad_hours": sorted(BAD_HOURS),
        "policies": policy_descriptions(),
        "variant_metrics": variant_rows,
        "temporal": {
            "yearly": yearly_rows,
            "quarterly": quarterly_rows,
            "monthly": monthly_rows,
        },
        "comparisons": load_comparisons(),
        "diagnostic_2026q2": diagnostic_2026q2(df, policy_predictions),
        "technical_decisions": [
            "No retraining is performed; policies only post-process existing rich_full_timing predictions.",
            "Blocked predictions are converted to DO_NOTHING.",
            "Month/quarter blocking is diagnostic only and is not part of any real policy.",
            "Diagnostic R columns are used only for evaluation.",
            "late_week is derived from textual weekday when available.",
        ],
    }
    (output_dir / "baltasar_v2_rich_policy_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = markdown_summary(metrics)
    (output_dir / "baltasar_v2_rich_policy_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")
    logging.info("Outputs written to %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate operational policy layer for Baltasar v2 rich full timing.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Rich full timing model joblib.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Rich feature dataset parquet.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    parser.add_argument("--doc", default=str(DEFAULT_DOC), help="Documentation markdown path.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_payload(payload: dict[str, Any], feature_columns: list[str]) -> None:
    if payload.get("target") != TARGET:
        raise ValueError(f"Unexpected target in model payload: {payload.get('target')}")
    forbidden = {TARGET, "buy_R", "sell_R", "buy_first_touch", "sell_first_touch"}
    leaked = sorted(set(feature_columns) & forbidden)
    if leaked:
        raise ValueError(f"Forbidden model features: {leaked}")


def read_dataset(path: Path, feature_columns: list[str]) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["split"] = df["timestamp"].apply(split_name)
    df["year"] = df["timestamp"].dt.year.astype(str)
    df["quarter"] = df["timestamp"].dt.tz_convert(None).dt.to_period("Q").astype(str)
    df["month"] = df["timestamp"].dt.tz_convert(None).dt.to_period("M").astype(str)
    required = [
        "timestamp",
        TARGET,
        "buy_R",
        "sell_R",
        "session",
        "hour",
        "weekday",
        "daily_range_position",
        *feature_columns,
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


def split_name(timestamp: pd.Timestamp) -> str:
    if timestamp <= TRAIN_END:
        return "train"
    if timestamp <= VALIDATION_END:
        return "validation"
    if timestamp <= TEST_END:
        return "test"
    return "outside"


def build_threshold_predictions(pipeline: Any, df: pd.DataFrame, feature_columns: list[str]) -> dict[str, pd.Series]:
    probabilities = pipeline.predict_proba(df[feature_columns])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    predictions: dict[str, list[str]] = {f"{threshold:.2f}": [] for threshold in THRESHOLDS}
    max_probs: dict[str, list[float]] = {f"{threshold:.2f}": [] for threshold in THRESHOLDS}
    for row in probabilities:
        buy_prob = float(row[buy_idx])
        sell_prob = float(row[sell_idx])
        best_prob = max(buy_prob, sell_prob)
        for threshold in THRESHOLDS:
            key = f"{threshold:.2f}"
            max_probs[key].append(best_prob)
            if buy_prob >= sell_prob and buy_prob >= threshold:
                predictions[key].append("ENTER_BUY")
            elif sell_prob > buy_prob and sell_prob >= threshold:
                predictions[key].append("ENTER_SELL")
            else:
                predictions[key].append("DO_NOTHING")
    out = {f"base_{key}": pd.Series(values, index=df.index) for key, values in predictions.items()}
    for key, values in max_probs.items():
        out[f"max_prob_{key}"] = pd.Series(values, index=df.index)
    return out


def build_policy_predictions(df: pd.DataFrame, base_predictions: dict[str, pd.Series]) -> dict[tuple[str, str], pd.Series]:
    out: dict[tuple[str, str], pd.Series] = {}
    masks = policy_masks(df)
    for threshold in [f"{value:.2f}" for value in THRESHOLDS]:
        base = base_predictions[f"base_{threshold}"]
        out[("no_policy", threshold)] = base
        for variant, allowed in masks.items():
            pred = base.where(allowed | ~base.isin(["ENTER_BUY", "ENTER_SELL"]), "DO_NOTHING")
            out[(variant, threshold)] = pred
    return out


def policy_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    hour = pd.to_numeric(df["hour"], errors="coerce")
    daily_range = pd.to_numeric(df["daily_range_position"], errors="coerce")
    session = df["session"].astype(str).str.lower()
    weekday_bucket_series = df["weekday"].apply(weekday_bucket)
    light = (session != "inactive") & ~((daily_range > 0.85) & daily_range.notna())
    medium = light & ~hour.isin(BAD_HOURS)
    strict = medium & (session != "overlap") & (weekday_bucket_series != "late_week")
    return {
        "rich_policy_light": light,
        "rich_policy_medium": medium,
        "rich_policy_strict": strict,
    }


def weekday_bucket(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"monday", "tuesday"}:
        return "early_week"
    if text in {"wednesday", "thursday"}:
        return "mid_week"
    if text == "friday":
        return "late_week"
    numeric = as_float(value)
    if numeric is None:
        return "UNKNOWN"
    day = int(numeric)
    if day in {0, 1}:
        return "early_week"
    if day in {2, 3}:
        return "mid_week"
    if day == 4:
        return "late_week"
    return "inactive"


def build_variant_rows(df: pd.DataFrame, predictions: dict[tuple[str, str], pd.Series]) -> list[dict[str, Any]]:
    rows = []
    for (variant, threshold), pred in predictions.items():
        for split in ["validation", "test", "oos"]:
            if split == "oos":
                mask = df["split"].isin(["validation", "test"])
            else:
                mask = df["split"] == split
            item = evaluate_predictions(df.loc[mask], pred.loc[df.loc[mask].index])
            rows.append({"variant": variant, "threshold": threshold, "split": split, **item})
    return rows


def grouped_rows(df: pd.DataFrame, predictions: dict[tuple[str, str], pd.Series], group_column: str) -> list[dict[str, Any]]:
    rows = []
    oos = df[df["split"].isin(["validation", "test"])]
    for (variant, threshold), pred in predictions.items():
        oos_pred = pred.loc[oos.index]
        for value in sorted(oos[group_column].astype(str).unique()):
            group = oos[oos[group_column].astype(str) == value]
            item = evaluate_predictions(group, oos_pred.loc[group.index])
            rows.append(
                {
                    "variant": variant,
                    "threshold": threshold,
                    group_column: value,
                    **item,
                    "low_sample": item["trades"] < 100,
                }
            )
    return rows


def selected_trade_rows(df: pd.DataFrame, predictions: dict[tuple[str, str], pd.Series]) -> list[dict[str, Any]]:
    rows = []
    oos_mask = df["split"].isin(["validation", "test"])
    for (variant, threshold), pred in predictions.items():
        selected = oos_mask & pred.isin(["ENTER_BUY", "ENTER_SELL"])
        subset = df.loc[selected, ["timestamp", "symbol", "split", TARGET, "buy_R", "sell_R", "session", "hour", "weekday", "daily_range_position"]].copy()
        subset["variant"] = variant
        subset["threshold"] = threshold
        subset["prediction"] = pred.loc[subset.index]
        subset["realized_R"] = realized_r(subset, subset["prediction"])
        rows.extend(subset.to_dict(orient="records"))
    return rows


def diagnostic_2026q2(df: pd.DataFrame, predictions: dict[tuple[str, str], pd.Series]) -> list[dict[str, Any]]:
    mask = df["quarter"] == "2026Q2"
    rows = []
    for (variant, threshold), pred in predictions.items():
        item = evaluate_predictions(df.loc[mask], pred.loc[df.loc[mask].index])
        rows.append({"variant": variant, "threshold": threshold, "quarter": "2026Q2", **item})
    return rows


def evaluate_predictions(df: pd.DataFrame, predictions: pd.Series) -> dict[str, Any]:
    y_true = df[TARGET].astype(str)
    predictions = predictions.astype(str)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    trade_r = [value for value, is_trade in zip(realized_r(df, predictions), trades, strict=False) if is_trade and value is not None]
    return {
        "rows": int(len(df)),
        "trades": int(trades.sum()),
        "coverage": round_float(safe_div(int(trades.sum()), len(df))),
        "trade_precision": precision_on_mask(y_true, predictions, trades),
        "buy_precision": precision_on_mask(y_true, predictions, buy_trades),
        "sell_precision": precision_on_mask(y_true, predictions, sell_trades),
        "avg_r": round_float(sum(trade_r) / len(trade_r)) if trade_r else None,
        "total_r": round_float(sum(trade_r)) if trade_r else None,
        "profit_factor": profit_factor(trade_r),
        "max_drawdown_r": round_float(max_drawdown(trade_r)),
        "prediction_distribution": dict(Counter(predictions)),
        "target_distribution": dict(Counter(y_true)),
    }


def realized_r(df: pd.DataFrame, predictions: pd.Series) -> list[float | None]:
    out = []
    for pred, buy_r, sell_r in zip(predictions, df["buy_R"], df["sell_R"], strict=False):
        if pred == "ENTER_BUY":
            out.append(as_float(buy_r))
        elif pred == "ENTER_SELL":
            out.append(as_float(sell_r))
        else:
            out.append(0.0)
    return out


def policy_descriptions() -> dict[str, list[str]]:
    return {
        "rich_policy_light": ["block session == inactive", "block daily_range_position > 0.85"],
        "rich_policy_medium": ["rich_policy_light", "block hours 20, 22, 16, 13, 15"],
        "rich_policy_strict": ["rich_policy_medium", "block session == overlap", "block late_week"],
    }


def load_comparisons() -> dict[str, Any]:
    rich = load_json(RICH_METRICS)
    no_timing = load_json(NO_TIMING_METRICS)
    coarse = load_json(COARSE_METRICS)
    pure = load_json(PURE_METRICS)
    return {
        "rich_full_timing": compact_thresholds(rich.get("thresholds", {})),
        "rich_no_timing": compact_thresholds(no_timing.get("thresholds", {})),
        "rich_coarse_timing": compact_thresholds(coarse.get("thresholds", {})),
        "baltasar_v1_signal": {
            split: compact_operational(pure.get("comparisons", {}).get("baltasar_v1_signal", {}).get(split, {}))
            for split in ["validation", "test"]
        },
    }


def compact_thresholds(thresholds: dict[str, Any]) -> dict[str, Any]:
    return {
        split: {
            threshold: compact_operational(thresholds.get(split, {}).get(threshold, {}))
            for threshold in ["0.40", "0.50"]
        }
        for split in ["validation", "test"]
    }


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


def markdown_summary(metrics: dict[str, Any]) -> str:
    rows = [
        row for row in metrics["variant_metrics"] if row["split"] in {"validation", "test"} and row["threshold"] in {"0.40", "0.50"}
    ]
    yearly = [
        row
        for row in metrics["temporal"]["yearly"]
        if row["threshold"] in {"0.40", "0.50"} and row["variant"] in {"no_policy", "rich_policy_light", "rich_policy_medium", "rich_policy_strict"}
    ]
    quarterly = [
        row
        for row in metrics["temporal"]["quarterly"]
        if row["threshold"] == "0.40" and row["variant"] in {"rich_policy_light", "rich_policy_medium", "rich_policy_strict"}
    ]
    lines = [
        "# Baltasar v2 Rich Policy Layer",
        "",
        "## Scope",
        "",
        "- Model: `baltasar_v2_rich_model.joblib`.",
        "- No retraining was performed.",
        "- Policies only block trades by converting predictions to `DO_NOTHING`.",
        "- Month/quarter blocking is diagnostic only.",
        "",
        "## Variant Results",
        "",
        table_from_rows(summary_rows(rows)),
        "",
        "## Yearly Stability",
        "",
        table_from_rows(temporal_summary_rows(yearly)),
        "",
        "## Quarterly Stability at Threshold 0.40",
        "",
        table_from_rows(temporal_summary_rows(quarterly)),
        "",
        "## Comparisons",
        "",
        comparison_table(metrics["comparisons"]),
        "",
        "## 2026Q2 Diagnostic",
        "",
        table_from_rows(summary_rows(metrics["diagnostic_2026q2"])),
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
    by_key = {
        (row["variant"], row["threshold"], row["split"]): row
        for row in metrics["variant_metrics"]
    }
    base = by_key[("no_policy", "0.40", "test")]
    light = by_key[("rich_policy_light", "0.40", "test")]
    medium = by_key[("rich_policy_medium", "0.40", "test")]
    strict = by_key[("rich_policy_strict", "0.40", "test")]
    return (
        f"On test at threshold 0.40, no_policy has avg R `{format_value(base['avg_r'])}` and PF "
        f"`{format_value(base['profit_factor'])}`. Light policy changes this to avg R `{format_value(light['avg_r'])}` "
        f"and PF `{format_value(light['profit_factor'])}`; medium to avg R `{format_value(medium['avg_r'])}` and PF "
        f"`{format_value(medium['profit_factor'])}`; strict to avg R `{format_value(strict['avg_r'])}` and PF "
        f"`{format_value(strict['profit_factor'])}`. Prefer the policy that improves drawdown and PF without collapsing "
        "coverage or failing validation."
    )


def summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "variant": row.get("variant"),
            "threshold": row.get("threshold"),
            "split": row.get("split", row.get("quarter")),
            "trades": row.get("trades"),
            "coverage": row.get("coverage"),
            "trade_precision": row.get("trade_precision"),
            "avg_r": row.get("avg_r"),
            "total_r": row.get("total_r"),
            "PF": row.get("profit_factor"),
            "max_DD": row.get("max_drawdown_r"),
            "BUY_precision": row.get("buy_precision"),
            "SELL_precision": row.get("sell_precision"),
        }
        for row in rows
    ]


def temporal_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        period = row.get("year") or row.get("quarter") or row.get("month")
        out.append(
            {
                "variant": row["variant"],
                "threshold": row["threshold"],
                "period": period,
                "trades": row["trades"],
                "avg_r": row["avg_r"],
                "total_r": row["total_r"],
                "PF": row["profit_factor"],
                "max_DD": row["max_drawdown_r"],
                "low_sample": row["low_sample"],
            }
        )
    return out


def comparison_table(comparisons: dict[str, Any]) -> str:
    rows = []
    for model in ["rich_full_timing", "rich_no_timing", "rich_coarse_timing"]:
        for split in ["validation", "test"]:
            for threshold in ["0.40", "0.50"]:
                item = comparisons[model][split][threshold]
                rows.append({"model": model, "split": split, "threshold": threshold, **item})
    for split in ["validation", "test"]:
        rows.append({"model": "baltasar_v1_signal", "split": split, "threshold": "signal", **comparisons["baltasar_v1_signal"][split]})
    return table_from_rows(rows)


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


def table_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(format_value(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
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
