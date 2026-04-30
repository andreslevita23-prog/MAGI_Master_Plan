from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_POLICY_METRICS = Path("data/output/magi_v2/baltasar_v2_rich_features_model/policy/baltasar_v2_rich_policy_metrics.json")
DEFAULT_POLICY_TRADES = Path("data/output/magi_v2/baltasar_v2_rich_features_model/policy/policy_trades.csv")
DEFAULT_DATASET = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_validation")
DEFAULT_DOC = Path("docs/baltasar_v2_policy_medium_validation.md")

TARGET = "tradeable_direction_rr2_first_touch"
VARIANT = "rich_policy_medium"
THRESHOLDS = ["0.40", "0.50"]
LOW_SAMPLE_TRADES = 100
TRAIN_END = pd.Timestamp("2023-12-31 23:59:59", tz="UTC")
VALIDATION_END = pd.Timestamp("2024-12-31 23:59:59", tz="UTC")
TEST_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    policy_metrics = load_json(Path(args.policy_metrics))
    trades = read_trades(Path(args.policy_trades))
    denominators = read_denominators(Path(args.dataset))

    medium_trades = trades[(trades["variant"] == VARIANT) & (trades["threshold"].isin(THRESHOLDS))].copy()
    if medium_trades.empty:
        raise ValueError("No rich_policy_medium trades found for thresholds 0.40/0.50")

    yearly = temporal_metrics(denominators, medium_trades, "year")
    quarterly = temporal_metrics(denominators, medium_trades, "quarter")
    monthly = temporal_metrics(denominators, medium_trades, "month")
    by_session = segment_metrics(denominators, medium_trades, "session")
    by_hour = segment_metrics(denominators, medium_trades, "hour")
    by_weekday = segment_metrics(denominators, medium_trades, "weekday")
    by_daily_range = segment_metrics(denominators, medium_trades, "daily_range_bucket")
    by_direction = direction_metrics(denominators, medium_trades)
    variant_summary = variant_rows(policy_metrics)

    write_csv(output_dir / "yearly_metrics.csv", yearly)
    write_csv(output_dir / "quarterly_metrics.csv", quarterly)
    write_csv(output_dir / "monthly_metrics.csv", monthly)
    write_csv(output_dir / "segment_by_session.csv", by_session)
    write_csv(output_dir / "segment_by_hour.csv", by_hour)
    write_csv(output_dir / "segment_by_weekday.csv", by_weekday)
    write_csv(output_dir / "segment_by_daily_range_bucket.csv", by_daily_range)
    write_csv(output_dir / "segment_by_direction.csv", by_direction)

    metrics = {
        "schema_version": "baltasar_v2_policy_medium_validation_v0.1",
        "generated_at": utc_now(),
        "variant": VARIANT,
        "thresholds": THRESHOLDS,
        "policy_metrics_source": str(args.policy_metrics),
        "policy_trades_source": str(args.policy_trades),
        "dataset_denominator_source": str(args.dataset),
        "summary": variant_summary,
        "stability": {
            "threshold_0.40": stability_summary(yearly, quarterly, monthly, "0.40"),
            "threshold_0.50": stability_summary(yearly, quarterly, monthly, "0.50"),
        },
        "temporal": {
            "yearly": yearly,
            "quarterly": quarterly,
            "monthly": monthly,
        },
        "segments": {
            "session": by_session,
            "hour": by_hour,
            "weekday": by_weekday,
            "daily_range_bucket": by_daily_range,
            "direction": by_direction,
        },
        "comparisons": comparison_rows(policy_metrics),
        "technical_decisions": [
            "No model inference or retraining is performed; this validates existing policy_trades.csv.",
            "The rich feature dataset is read only to compute denominator rows and true coverage by period/segment.",
            "Only rich_policy_medium thresholds 0.40 and 0.50 are evaluated as candidate policies.",
            "Diagnostic R is read from policy_trades.csv realized_R.",
        ],
    }
    (output_dir / "policy_medium_validation_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    summary = markdown_summary(metrics)
    (output_dir / "policy_medium_validation_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Baltasar v2 rich_policy_medium.")
    parser.add_argument("--policy-metrics", default=str(DEFAULT_POLICY_METRICS))
    parser.add_argument("--policy-trades", default=str(DEFAULT_POLICY_TRADES))
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_trades(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["threshold"] = df["threshold"].map(lambda value: f"{float(value):.2f}")
    df["year"] = df["timestamp"].dt.year.astype(str)
    df["quarter"] = df["timestamp"].dt.tz_convert(None).dt.to_period("Q").astype(str)
    df["month"] = df["timestamp"].dt.tz_convert(None).dt.to_period("M").astype(str)
    df["hour"] = pd.to_numeric(df["hour"], errors="coerce").astype("Int64").astype(str)
    df["weekday"] = df["weekday"].astype(str).str.lower()
    df["daily_range_bucket"] = daily_range_bucket(df["daily_range_position"])
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce")
    return df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


def read_denominators(path: Path) -> pd.DataFrame:
    columns = ["timestamp", "session", "hour", "weekday", "daily_range_position"]
    df = pd.read_parquet(path, columns=columns)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["split"] = df["timestamp"].apply(split_name)
    df = df[df["split"].isin(["validation", "test"])].copy()
    df["year"] = df["timestamp"].dt.year.astype(str)
    df["quarter"] = df["timestamp"].dt.tz_convert(None).dt.to_period("Q").astype(str)
    df["month"] = df["timestamp"].dt.tz_convert(None).dt.to_period("M").astype(str)
    df["hour"] = pd.to_numeric(df["hour"], errors="coerce").astype("Int64").astype(str)
    df["weekday"] = df["weekday"].astype(str).str.lower()
    df["daily_range_bucket"] = daily_range_bucket(df["daily_range_position"])
    return df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


def split_name(timestamp: pd.Timestamp) -> str:
    if timestamp <= TRAIN_END:
        return "train"
    if timestamp <= VALIDATION_END:
        return "validation"
    if timestamp <= TEST_END:
        return "test"
    return "outside"


def daily_range_bucket(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    bins = [-float("inf"), 0.15, 0.35, 0.65, 0.85, float("inf")]
    labels = ["<=0.15", "0.15-0.35", "0.35-0.65", "0.65-0.85", ">0.85"]
    out = pd.cut(numeric, bins=bins, labels=labels)
    return out.astype("object").where(out.notna(), "UNKNOWN").astype(str)


def variant_rows(policy_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in policy_metrics.get("variant_metrics", []):
        if row.get("variant") == VARIANT and row.get("threshold") in THRESHOLDS and row.get("split") in {"validation", "test", "oos"}:
            rows.append(compact_row(row, extra={"split": row.get("split"), "threshold": row.get("threshold")}))
    return rows


def temporal_metrics(denominators: pd.DataFrame, trades: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    rows = []
    for threshold in THRESHOLDS:
        threshold_trades = trades[trades["threshold"] == threshold]
        for value in sorted(denominators[column].astype(str).unique()):
            denom_mask = denominators[column].astype(str) == value
            trade_mask = threshold_trades[column].astype(str) == value
            rows.append(metric_row(denominators.loc[denom_mask], threshold_trades.loc[trade_mask], threshold, column, value))
    return rows


def segment_metrics(denominators: pd.DataFrame, trades: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    rows = []
    for threshold in THRESHOLDS:
        threshold_trades = trades[trades["threshold"] == threshold]
        for value in sorted(denominators[column].astype(str).unique()):
            denom_mask = denominators[column].astype(str) == value
            trade_mask = threshold_trades[column].astype(str) == value
            rows.append(metric_row(denominators.loc[denom_mask], threshold_trades.loc[trade_mask], threshold, "segment", value))
    return rows


def direction_metrics(denominators: pd.DataFrame, trades: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for threshold in THRESHOLDS:
        threshold_trades = trades[trades["threshold"] == threshold]
        for direction in ["ENTER_BUY", "ENTER_SELL"]:
            subset = threshold_trades[threshold_trades["prediction"] == direction]
            rows.append(metric_row(denominators, subset, threshold, "segment", direction))
    return rows


def metric_row(denom: pd.DataFrame, trades: pd.DataFrame, threshold: str, group_key: str, group_value: str) -> dict[str, Any]:
    base = evaluate_trade_subset(denom, trades)
    return {
        "threshold": threshold,
        group_key: group_value,
        **base,
        "low_sample": base["trades"] < LOW_SAMPLE_TRADES,
    }


def evaluate_trade_subset(denom: pd.DataFrame, trades: pd.DataFrame) -> dict[str, Any]:
    trade_count = len(trades)
    realized = trades["realized_R"].dropna().tolist()
    correct = trades[TARGET].astype(str) == trades["prediction"].astype(str)
    buy = trades["prediction"] == "ENTER_BUY"
    sell = trades["prediction"] == "ENTER_SELL"
    return {
        "rows": int(len(denom)),
        "trades": int(trade_count),
        "coverage": round_float(safe_div(trade_count, len(denom))),
        "trade_precision": round_float(correct.mean()) if trade_count else None,
        "win_rate": round_float((trades["realized_R"] > 0).mean()) if trade_count else None,
        "buy_precision": precision_for_mask(trades, buy),
        "sell_precision": precision_for_mask(trades, sell),
        "avg_r": round_float(sum(realized) / len(realized)) if realized else None,
        "total_r": round_float(sum(realized)) if realized else None,
        "profit_factor": profit_factor(realized),
        "max_drawdown_r": round_float(max_drawdown(realized)),
        "prediction_distribution": dict(Counter(trades["prediction"].astype(str))) if trade_count else {},
    }


def precision_for_mask(trades: pd.DataFrame, mask: pd.Series) -> float | None:
    if len(trades) == 0 or int(mask.sum()) == 0:
        return None
    return round_float((trades.loc[mask, TARGET].astype(str) == trades.loc[mask, "prediction"].astype(str)).mean())


def stability_summary(yearly: list[dict[str, Any]], quarterly: list[dict[str, Any]], monthly: list[dict[str, Any]], threshold: str) -> dict[str, Any]:
    return {
        "years_positive": positive_count(yearly, threshold),
        "quarters_positive": positive_count(quarterly, threshold),
        "months_positive": positive_count(monthly, threshold),
        "worst_months": worst_periods(monthly, threshold, 8),
    }


def positive_count(rows: list[dict[str, Any]], threshold: str) -> dict[str, int]:
    selected = [row for row in rows if row["threshold"] == threshold and not row["low_sample"]]
    return {
        "positive": sum(1 for row in selected if (row["avg_r"] or 0) > 0),
        "total": len(selected),
    }


def worst_periods(rows: list[dict[str, Any]], threshold: str, limit: int) -> list[dict[str, Any]]:
    selected = [row for row in rows if row["threshold"] == threshold and not row["low_sample"] and row["avg_r"] is not None]
    selected.sort(key=lambda row: row["avg_r"])
    return selected[:limit]


def comparison_rows(policy_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    by_variant = policy_metrics.get("variant_metrics", [])
    for variant in ["no_policy", "rich_policy_light", "rich_policy_medium", "rich_policy_strict"]:
        for threshold in THRESHOLDS:
            for split in ["validation", "test"]:
                match = next(
                    (
                        row
                        for row in by_variant
                        if row.get("variant") == variant and row.get("threshold") == threshold and row.get("split") == split
                    ),
                    None,
                )
                if match:
                    rows.append(compact_row(match, extra={"model": variant, "threshold": threshold, "split": split}))
    for split, item in policy_metrics.get("comparisons", {}).get("baltasar_v1_signal", {}).items():
        rows.append(
            {
                "model": "baltasar_v1_signal",
                "threshold": "signal",
                "split": split,
                "trades": item.get("trades"),
                "coverage": item.get("coverage"),
                "trade_precision": item.get("trade_precision"),
                "avg_r": item.get("avg_r"),
                "total_r": item.get("total_r"),
                "profit_factor": item.get("profit_factor"),
                "max_drawdown_r": item.get("max_drawdown_r"),
            }
        )
    return rows


def compact_row(row: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    return {
        **extra,
        "trades": row.get("trades"),
        "coverage": row.get("coverage"),
        "trade_precision": row.get("trade_precision"),
        "buy_precision": row.get("buy_precision"),
        "sell_precision": row.get("sell_precision"),
        "avg_r": row.get("avg_r"),
        "total_r": row.get("total_r"),
        "profit_factor": row.get("profit_factor"),
        "max_drawdown_r": row.get("max_drawdown_r"),
    }


def markdown_summary(metrics: dict[str, Any]) -> str:
    summary = metrics["summary"]
    yearly = metrics["temporal"]["yearly"]
    quarterly = metrics["temporal"]["quarterly"]
    monthly = metrics["temporal"]["monthly"]
    segments = metrics["segments"]
    lines = [
        "# Baltasar v2 Policy Medium Validation",
        "",
        "## Scope",
        "",
        "- Variant: `rich_policy_medium` only.",
        "- Thresholds: `0.40` and `0.50`.",
        "- No retraining or model inference; validates existing policy trades.",
        "",
        "## Validation And Test Metrics",
        "",
        table_from_rows(summary_table(summary)),
        "",
        "## Stability Counts",
        "",
        table_from_rows(stability_table(metrics["stability"])),
        "",
        "## Annual Stability",
        "",
        table_from_rows(period_table(yearly, "year")),
        "",
        "## Quarterly Stability",
        "",
        table_from_rows(period_table(quarterly, "quarter")),
        "",
        "## Worst Months",
        "",
        table_from_rows(worst_month_table(metrics["stability"])),
        "",
        "## Segment By Session",
        "",
        table_from_rows(segment_table(segments["session"])),
        "",
        "## Segment By Hour",
        "",
        table_from_rows(segment_table(segments["hour"])),
        "",
        "## Segment By Direction",
        "",
        table_from_rows(segment_table(segments["direction"])),
        "",
        "## Comparison",
        "",
        table_from_rows(comparison_table(metrics["comparisons"])),
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


def summary_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "threshold": row["threshold"],
            "split": row["split"],
            "trades": row["trades"],
            "coverage": row["coverage"],
            "trade_precision": row["trade_precision"],
            "avg_r": row["avg_r"],
            "total_r": row["total_r"],
            "PF": row["profit_factor"],
            "max_DD": row["max_drawdown_r"],
        }
        for row in rows
    ]


def stability_table(stability: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for threshold_key, data in stability.items():
        threshold = threshold_key.replace("threshold_", "")
        rows.append(
            {
                "threshold": threshold,
                "years_positive": f"{data['years_positive']['positive']}/{data['years_positive']['total']}",
                "quarters_positive": f"{data['quarters_positive']['positive']}/{data['quarters_positive']['total']}",
                "months_positive": f"{data['months_positive']['positive']}/{data['months_positive']['total']}",
            }
        )
    return rows


def period_table(rows: list[dict[str, Any]], period_key: str) -> list[dict[str, Any]]:
    return [
        {
            "threshold": row["threshold"],
            "period": row[period_key],
            "trades": row["trades"],
            "coverage": row["coverage"],
            "avg_r": row["avg_r"],
            "total_r": row["total_r"],
            "PF": row["profit_factor"],
            "max_DD": row["max_drawdown_r"],
            "low_sample": row["low_sample"],
        }
        for row in rows
    ]


def worst_month_table(stability: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for threshold_key, data in stability.items():
        threshold = threshold_key.replace("threshold_", "")
        for row in data["worst_months"]:
            rows.append(
                {
                    "threshold": threshold,
                    "month": row["month"],
                    "trades": row["trades"],
                    "avg_r": row["avg_r"],
                    "total_r": row["total_r"],
                    "PF": row["profit_factor"],
                    "max_DD": row["max_drawdown_r"],
                }
            )
    return rows


def segment_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "threshold": row["threshold"],
            "segment": row["segment"],
            "rows": row["rows"],
            "trades": row["trades"],
            "coverage": row["coverage"],
            "trade_precision": row["trade_precision"],
            "avg_r": row["avg_r"],
            "total_r": row["total_r"],
            "PF": row["profit_factor"],
            "max_DD": row["max_drawdown_r"],
            "low_sample": row["low_sample"],
        }
        for row in rows
    ]


def comparison_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "model": row["model"],
            "threshold": row["threshold"],
            "split": row["split"],
            "trades": row["trades"],
            "coverage": row["coverage"],
            "avg_r": row["avg_r"],
            "total_r": row["total_r"],
            "PF": row["profit_factor"],
            "max_DD": row["max_drawdown_r"],
        }
        for row in rows
    ]


def interpretation(metrics: dict[str, Any]) -> str:
    by_key = {(row["threshold"], row["split"]): row for row in metrics["summary"]}
    val_040 = by_key[("0.40", "validation")]
    test_040 = by_key[("0.40", "test")]
    val_050 = by_key[("0.50", "validation")]
    test_050 = by_key[("0.50", "test")]
    return (
        f"Threshold 0.40 keeps much more sample: validation `{val_040['trades']}` trades and test `{test_040['trades']}` trades, "
        f"with test avg R `{format_value(test_040['avg_r'])}` and PF `{format_value(test_040['profit_factor'])}`. "
        f"Threshold 0.50 is more selective: validation `{val_050['trades']}` and test `{test_050['trades']}`, "
        f"with test avg R `{format_value(test_050['avg_r'])}` and PF `{format_value(test_050['profit_factor'])}`. "
        "The final decision should prefer the threshold with acceptable validation/test consistency and enough trades for future policy learning."
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def table_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(format_value(row.get(header)) for header in headers) + " |")
    return "\n".join(lines)


def profit_factor(values: list[float]) -> float | None:
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_loss = abs(sum(losses))
    if gross_loss == 0:
        return None
    return round_float(sum(wins) / gross_loss)


def max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in values:
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


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
