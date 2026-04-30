from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_V2_DIR = RUN_DIR / "ceo_v2_tradeable"
DEFAULT_DATASET = DEFAULT_V2_DIR / "ceo_v2_tradeable_dataset.parquet"
DEFAULT_MODEL = DEFAULT_V2_DIR / "ceo_v2_tradeable_model.joblib"
DEFAULT_OUTPUT_DIR = DEFAULT_V2_DIR / "walk_forward_policy"

TARGET = "ceo_label_h48_tradeable"
THRESHOLD = 0.70
ALLOWED_SESSIONS = {"london", "new_york", "overlap"}


def main() -> int:
    args = parse_args()
    setup_logging()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading CEO v2 dataset: %s", args.dataset)
    df = pd.read_parquet(args.dataset)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["year"] = df["timestamp"].dt.year.astype("Int64").astype("string")
    df["quarter"] = df["timestamp"].dt.to_period("Q").astype(str)
    df["month"] = df["timestamp"].dt.strftime("%Y-%m")

    payload = joblib.load(args.model)
    pipeline = payload["pipeline"] if isinstance(payload, dict) else payload
    features = payload.get("features") if isinstance(payload, dict) else infer_features()

    df["prediction"] = policy_predictions(df, pipeline, features)
    logging.info("Policy predictions generated for %s rows", len(df))

    yearly = grouped_metrics(df, "year")
    quarterly = grouped_metrics(df, "quarter")
    monthly = grouped_metrics(df, "month")
    global_metrics = evaluate_group(df)

    write_csv(output_dir / "yearly_metrics.csv", yearly)
    write_csv(output_dir / "quarterly_metrics.csv", quarterly)
    write_csv(output_dir / "monthly_metrics.csv", monthly)

    metrics = {
        "schema_version": "ceo_v2_policy_walk_forward_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policy": policy_description(),
        "global": global_metrics,
        "yearly": yearly,
        "quarterly": quarterly,
        "monthly": monthly,
        "stability": stability_summary(yearly, quarterly, monthly),
    }
    (output_dir / "walk_forward_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "walk_forward_summary.md").write_text(markdown_summary(metrics), encoding="utf-8")
    logging.info("Walk-forward policy audit written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Walk-forward validation for CEO v2 conservative_core policy.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="CEO v2 tradeable dataset parquet.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="CEO v2 model joblib.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output walk-forward directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def infer_features() -> list[str]:
    return [
        "session",
        "hour",
        "weekday",
        "spread",
        "atr",
        "daily_range_position",
        "regime",
        "melchor_signal",
        "melchor_confidence",
        "melchor_risk_flags",
        "baltasar_signal",
        "baltasar_confidence",
        "gaspar_signal",
        "gaspar_confidence",
        "mage_agreement",
        "baltasar_gaspar_alignment",
    ]


def policy_predictions(df: pd.DataFrame, pipeline: Any, features: list[str]) -> pd.Series:
    probabilities = pipeline.predict_proba(df[features])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    base = threshold_predictions(probabilities, buy_idx, sell_idx)
    allowed = context_mask(df)
    return pd.Series(
        [prediction if allowed_flag else "DO_NOTHING" for prediction, allowed_flag in zip(base, allowed, strict=False)],
        index=df.index,
    )


def threshold_predictions(probabilities: Any, buy_idx: int, sell_idx: int) -> list[str]:
    predictions = []
    for row in probabilities:
        buy_prob = float(row[buy_idx])
        sell_prob = float(row[sell_idx])
        if buy_prob >= sell_prob and buy_prob >= THRESHOLD:
            predictions.append("ENTER_BUY")
        elif sell_prob > buy_prob and sell_prob >= THRESHOLD:
            predictions.append("ENTER_SELL")
        else:
            predictions.append("DO_NOTHING")
    return predictions


def context_mask(df: pd.DataFrame) -> pd.Series:
    session = df["session"].fillna("").astype(str).str.lower()
    melchor = df["melchor_signal"].fillna("").astype(str).str.upper()
    gaspar = df["gaspar_signal"].fillna("").astype(str).str.upper()
    baltasar = df["baltasar_signal"].fillna("").astype(str).str.upper()
    d1 = pd.to_numeric(df["daily_range_position"], errors="coerce")
    return (
        session.isin(ALLOWED_SESSIONS)
        & (melchor == "APPROVE")
        & (gaspar != "POOR")
        & baltasar.isin(["BUY", "SELL"])
        & (d1 >= 0.15)
        & (d1 <= 0.65)
    )


def grouped_metrics(df: pd.DataFrame, group_column: str) -> list[dict[str, Any]]:
    rows = []
    for value, group in df.groupby(group_column, dropna=False):
        row = evaluate_group(group)
        row["period"] = "UNKNOWN" if pd.isna(value) else str(value)
        rows.append(row)
    return sorted(rows, key=lambda item: item["period"])


def evaluate_group(df: pd.DataFrame) -> dict[str, Any]:
    predictions = df["prediction"].astype(str)
    actual = df[TARGET].astype(str)
    trades = predictions.isin(["ENTER_BUY", "ENTER_SELL"])
    buy_trades = predictions == "ENTER_BUY"
    sell_trades = predictions == "ENTER_SELL"
    trades_taken = int(trades.sum())
    correct = int((predictions[trades] == actual[trades]).sum()) if trades_taken else 0
    return {
        "rows": int(len(df)),
        "trades_taken": trades_taken,
        "coverage": safe_div(trades_taken, len(df)),
        "trade_precision": safe_div(correct, trades_taken),
        "buy_precision": precision_for(predictions, actual, buy_trades),
        "sell_precision": precision_for(predictions, actual, sell_trades),
        "prediction_do_nothing": int((predictions == "DO_NOTHING").sum()),
        "prediction_enter_buy": int((predictions == "ENTER_BUY").sum()),
        "prediction_enter_sell": int((predictions == "ENTER_SELL").sum()),
        "selected_target_do_nothing": int((actual[trades] == "DO_NOTHING").sum()),
        "selected_target_enter_buy": int((actual[trades] == "ENTER_BUY").sum()),
        "selected_target_enter_sell": int((actual[trades] == "ENTER_SELL").sum()),
    }


def stability_summary(yearly: list[dict[str, Any]], quarterly: list[dict[str, Any]], monthly: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "yearly": period_stability(yearly),
        "quarterly": period_stability(quarterly),
        "monthly": period_stability(monthly),
        "best_months": best_periods(monthly),
        "worst_months": worst_periods(monthly),
    }


def period_stability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in rows if row["trades_taken"] > 0 and row["trade_precision"] is not None]
    precisions = [row["trade_precision"] for row in eligible]
    positive = [row for row in eligible if row["trade_precision"] >= 0.25]
    weak = [row for row in eligible if row["trade_precision"] < 0.20]
    return {
        "periods": len(rows),
        "active_periods": len(eligible),
        "zero_trade_periods": len(rows) - len(eligible),
        "mean_trade_precision": round_float(sum(precisions) / len(precisions)) if precisions else None,
        "min_trade_precision": round_float(min(precisions)) if precisions else None,
        "max_trade_precision": round_float(max(precisions)) if precisions else None,
        "periods_precision_gte_25pct": len(positive),
        "periods_precision_lt_20pct": len(weak),
    }


def best_periods(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    eligible = [row for row in rows if row["trades_taken"] >= 100 and row["trade_precision"] is not None]
    return sorted(eligible, key=lambda item: (item["trade_precision"], item["trades_taken"]), reverse=True)[:limit]


def worst_periods(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    eligible = [row for row in rows if row["trades_taken"] >= 100 and row["trade_precision"] is not None]
    return sorted(eligible, key=lambda item: (item["trade_precision"], -item["trades_taken"]))[:limit]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "period",
        "rows",
        "trades_taken",
        "coverage",
        "trade_precision",
        "buy_precision",
        "sell_precision",
        "prediction_do_nothing",
        "prediction_enter_buy",
        "prediction_enter_sell",
        "selected_target_do_nothing",
        "selected_target_enter_buy",
        "selected_target_enter_sell",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def policy_description() -> dict[str, Any]:
    return {
        "name": "conservative_core",
        "threshold": THRESHOLD,
        "allowed_sessions": sorted(ALLOWED_SESSIONS),
        "daily_range_position": "0.15 <= daily_range_position <= 0.65",
        "melchor": "APPROVE",
        "gaspar": "not POOR",
        "baltasar": "BUY or SELL",
        "retraining": "none; fixed saved model is applied to all periods",
    }


def precision_for(predictions: pd.Series, actual: pd.Series, mask: pd.Series) -> float | None:
    total = int(mask.sum())
    if not total:
        return None
    return round(float((predictions[mask] == actual[mask]).sum()) / total, 6)


def safe_div(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 6)


def round_float(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def markdown_summary(metrics: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI v2 Conservative Core Walk-Forward Policy",
        "",
        f"- generated_at: {metrics['generated_at']}",
        f"- rows: {metrics['global']['rows']}",
        f"- trades_taken: {metrics['global']['trades_taken']}",
        f"- coverage: {fmt_pct(metrics['global']['coverage'])}",
        f"- trade_precision: {fmt_pct(metrics['global']['trade_precision'])}",
        "",
        "## Yearly Metrics",
        period_table(metrics["yearly"]),
        "",
        "## Quarterly Stability",
        stability_table(metrics["stability"]["quarterly"]),
        "",
        "## Best Months",
        period_table(metrics["stability"]["best_months"]),
        "",
        "## Worst Months",
        period_table(metrics["stability"]["worst_months"]),
        "",
        "## Monthly Stability",
        stability_table(metrics["stability"]["monthly"]),
    ]
    return "\n".join(lines) + "\n"


def period_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No active periods._"
    lines = [
        "| Period | Rows | Trades | Coverage | Trade precision | BUY precision | SELL precision |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['period']} | {row['rows']} | {row['trades_taken']} | {fmt_pct(row['coverage'])} | "
            f"{fmt_pct(row['trade_precision'])} | {fmt_pct(row['buy_precision'])} | {fmt_pct(row['sell_precision'])} |"
        )
    return "\n".join(lines)


def stability_table(row: dict[str, Any]) -> str:
    return "\n".join(
        [
            "| Metric | Value |",
            "|---|---:|",
            f"| periods | {row['periods']} |",
            f"| active_periods | {row['active_periods']} |",
            f"| zero_trade_periods | {row['zero_trade_periods']} |",
            f"| mean_trade_precision | {fmt_pct(row['mean_trade_precision'])} |",
            f"| min_trade_precision | {fmt_pct(row['min_trade_precision'])} |",
            f"| max_trade_precision | {fmt_pct(row['max_trade_precision'])} |",
            f"| periods_precision_gte_25pct | {row['periods_precision_gte_25pct']} |",
            f"| periods_precision_lt_20pct | {row['periods_precision_lt_20pct']} |",
        ]
    )


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
