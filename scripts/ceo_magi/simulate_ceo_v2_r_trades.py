from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_JSONL = RUN_DIR / "ceo_training_records.jsonl"
DEFAULT_DATASET = RUN_DIR / "ceo_v2_tradeable" / "ceo_v2_tradeable_dataset.parquet"
DEFAULT_MODEL = RUN_DIR / "ceo_v2_tradeable" / "ceo_v2_tradeable_model.joblib"
DEFAULT_OUTPUT_DIR = RUN_DIR / "ceo_v2_tradeable" / "r_simulation"

TARGET = "ceo_label_h48_tradeable"
THRESHOLD = 0.70
ALLOWED_SESSIONS = {"london", "new_york", "overlap"}
RR_PROFILES = {
    "rr_1_1": {"sl_pips": 10.0, "tp_pips": 10.0},
    "rr_1_1_5": {"sl_pips": 10.0, "tp_pips": 15.0},
    "rr_1_2": {"sl_pips": 10.0, "tp_pips": 20.0},
}
SCENARIOS = ("conservative", "optimistic")


def main() -> int:
    args = parse_args()
    setup_logging()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading dataset: %s", args.dataset)
    df = pd.read_parquet(args.dataset)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["year"] = df["timestamp"].dt.year.astype("Int64").astype("string")
    df["quarter"] = df["timestamp"].dt.to_period("Q").astype(str)
    df["month"] = df["timestamp"].dt.strftime("%Y-%m")

    payload = joblib.load(args.model)
    pipeline = payload["pipeline"] if isinstance(payload, dict) else payload
    features = payload.get("features") if isinstance(payload, dict) else infer_features()

    selected = selected_policy_rows(df, pipeline, features)
    logging.info("Policy selected rows: %s", int(selected.sum()))

    selected_outcomes = load_selected_outcomes(Path(args.jsonl), selected)
    trades = simulate_trades(df.loc[selected].copy(), selected_outcomes)
    write_trades(output_dir / "simulated_trades.csv", trades)

    metrics = build_metrics(trades)
    (output_dir / "r_simulation_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "r_simulation_summary.md").write_text(markdown_summary(metrics), encoding="utf-8")
    write_group_metrics(output_dir / "metrics_by_year.csv", metrics["by_year"])
    write_group_metrics(output_dir / "metrics_by_quarter.csv", metrics["by_quarter"])
    write_group_metrics(output_dir / "metrics_by_month.csv", metrics["by_month"])
    write_group_metrics(output_dir / "metrics_by_rr.csv", metrics["by_rr"])
    logging.info("R simulation written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Proxy R/SL/TP simulation for CEO v2 conservative_core.")
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="Raw CEO JSONL path.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="CEO v2 dataset parquet.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="CEO v2 model joblib.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output R simulation directory.")
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


def selected_policy_rows(df: pd.DataFrame, pipeline: Any, features: list[str]) -> pd.Series:
    probabilities = pipeline.predict_proba(df[features])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
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
    pred = pd.Series(predictions, index=df.index)
    context = context_mask(df)
    return pred.isin(["ENTER_BUY", "ENTER_SELL"]) & context


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


def load_selected_outcomes(jsonl_path: Path, selected: pd.Series) -> dict[int, dict[str, Any]]:
    selected_indices = set(int(index) for index in selected[selected].index)
    outcomes: dict[int, dict[str, Any]] = {}
    with jsonl_path.open("r", encoding="utf-8-sig") as handle:
        for index, line in enumerate(handle):
            if index not in selected_indices:
                continue
            record = json.loads(line)
            future_outcomes = record.get("future_outcomes") if isinstance(record.get("future_outcomes"), dict) else {}
            h48 = future_outcomes.get("48") if isinstance(future_outcomes.get("48"), dict) else {}
            outcomes[index] = h48
            if len(outcomes) == len(selected_indices):
                break
    if len(outcomes) != len(selected_indices):
        raise ValueError(f"Outcome count mismatch: selected={len(selected_indices)} outcomes={len(outcomes)}")
    return outcomes


def simulate_trades(selected_df: pd.DataFrame, outcomes: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    trades = []
    for index, row in selected_df.iterrows():
        outcome = outcomes[int(index)]
        direction = str(row["baltasar_signal"]).upper()
        spread = as_float(row.get("spread")) or 0.0
        mfe = as_float(outcome.get("max_favorable_excursion")) or 0.0
        mae = abs(as_float(outcome.get("max_adverse_excursion")) or 0.0)
        future_return_pips = as_float(outcome.get("future_return_pips")) or 0.0
        directional_return_pips = future_return_pips if direction == "BUY" else -future_return_pips
        for rr_name, profile in RR_PROFILES.items():
            for scenario in SCENARIOS:
                result = simulate_one(profile["sl_pips"], profile["tp_pips"], spread, mfe, mae, directional_return_pips, scenario)
                trades.append({
                    "source_index": int(index),
                    "timestamp": row["timestamp"].isoformat().replace("+00:00", "Z") if pd.notna(row["timestamp"]) else "",
                    "year": row.get("year"),
                    "quarter": row.get("quarter"),
                    "month": row.get("month"),
                    "symbol": row.get("symbol"),
                    "session": row.get("session"),
                    "direction": direction,
                    "rr_profile": rr_name,
                    "scenario": scenario,
                    "sl_pips": profile["sl_pips"],
                    "tp_pips": profile["tp_pips"],
                    "spread": spread,
                    "future_return_pips": future_return_pips,
                    "directional_return_pips": directional_return_pips,
                    "max_favorable_excursion": mfe,
                    "max_adverse_excursion_abs": mae,
                    **result,
                })
    return trades


def simulate_one(sl_pips: float, tp_pips: float, spread: float, mfe: float, mae: float, directional_return_pips: float, scenario: str) -> dict[str, Any]:
    hit_tp = mfe >= (tp_pips + spread)
    hit_sl = mae >= sl_pips
    ambiguous = bool(hit_tp and hit_sl)
    if ambiguous:
        if scenario == "conservative":
            return {"exit_reason": "SL", "r": -1.0, "hit_tp": hit_tp, "hit_sl": hit_sl, "ambiguous": True}
        return {"exit_reason": "TP", "r": round(tp_pips / sl_pips, 6), "hit_tp": hit_tp, "hit_sl": hit_sl, "ambiguous": True}
    if hit_tp:
        return {"exit_reason": "TP", "r": round(tp_pips / sl_pips, 6), "hit_tp": hit_tp, "hit_sl": hit_sl, "ambiguous": False}
    if hit_sl:
        return {"exit_reason": "SL", "r": -1.0, "hit_tp": hit_tp, "hit_sl": hit_sl, "ambiguous": False}
    close_pips = directional_return_pips - spread
    return {"exit_reason": "TIMEOUT", "r": round(close_pips / sl_pips, 6), "hit_tp": hit_tp, "hit_sl": hit_sl, "ambiguous": False}


def build_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "ceo_v2_r_simulation_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policy": "conservative_core",
        "threshold": THRESHOLD,
        "note": "Proxy simulation only. Ambiguous intrabar TP/SL order is bracketed with conservative and optimistic scenarios.",
        "by_rr": grouped_metrics(trades, "rr_profile"),
        "by_year": grouped_metrics(trades, "year"),
        "by_quarter": grouped_metrics(trades, "quarter"),
        "by_month": grouped_metrics(trades, "month"),
        "global": grouped_metrics(trades, "global"),
        "missing_for_institutional_backtest": [
            "intrabar TP/SL order",
            "real execution price",
            "commission",
            "slippage",
            "position sizing",
            "trade lifecycle with exact entry/exit timestamps",
        ],
    }


def grouped_metrics(trades: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        group_value = "all" if group_key == "global" else str(trade.get(group_key) or "UNKNOWN")
        groups[(group_value, trade["rr_profile"], trade["scenario"])].append(trade)
    rows = []
    for (group_value, rr_profile, scenario), items in sorted(groups.items()):
        rows.append(metric_row(group_key, group_value, rr_profile, scenario, items))
    return rows


def metric_row(group_key: str, group_value: str, rr_profile: str, scenario: str, trades: list[dict[str, Any]]) -> dict[str, Any]:
    r_values = [float(trade["r"]) for trade in trades]
    wins = [value for value in r_values if value > 0]
    losses = [value for value in r_values if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    exit_counts = Counter(trade["exit_reason"] for trade in trades)
    ambiguous = sum(1 for trade in trades if trade["ambiguous"])
    return {
        "group": group_key,
        "period": group_value,
        "rr_profile": rr_profile,
        "scenario": scenario,
        "trades": len(trades),
        "win_rate": safe_div(len(wins), len(trades)),
        "avg_r": round_float(sum(r_values) / len(r_values)) if r_values else None,
        "total_r": round_float(sum(r_values)),
        "profit_factor": round_float(gross_profit / gross_loss) if gross_loss else None,
        "max_drawdown_r": round_float(max_drawdown(r_values)),
        "ambiguous_trades": ambiguous,
        "timeout_trades": int(exit_counts.get("TIMEOUT", 0)),
        "tp_trades": int(exit_counts.get("TP", 0)),
        "sl_trades": int(exit_counts.get("SL", 0)),
    }


def max_drawdown(r_values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in r_values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def write_trades(path: Path, trades: list[dict[str, Any]]) -> None:
    fieldnames = [
        "source_index",
        "timestamp",
        "year",
        "quarter",
        "month",
        "symbol",
        "session",
        "direction",
        "rr_profile",
        "scenario",
        "sl_pips",
        "tp_pips",
        "spread",
        "future_return_pips",
        "directional_return_pips",
        "max_favorable_excursion",
        "max_adverse_excursion_abs",
        "exit_reason",
        "r",
        "hit_tp",
        "hit_sl",
        "ambiguous",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)


def write_group_metrics(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "group",
        "period",
        "rr_profile",
        "scenario",
        "trades",
        "win_rate",
        "avg_r",
        "total_r",
        "profit_factor",
        "max_drawdown_r",
        "ambiguous_trades",
        "timeout_trades",
        "tp_trades",
        "sl_trades",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
        "# CEO-MAGI v2 R Simulation Proxy",
        "",
        f"- generated_at: {metrics['generated_at']}",
        f"- policy: {metrics['policy']}",
        f"- threshold: {metrics['threshold']}",
        f"- note: {metrics['note']}",
        "",
        "## RR Comparison",
        metrics_table(metrics["by_rr"]),
        "",
        "## Yearly Metrics",
        metrics_table(metrics["by_year"]),
        "",
        "## Worst Months By Total R",
        metrics_table(worst_months(metrics["by_month"])),
        "",
        "## Missing For Institutional Backtest",
    ]
    lines.extend(f"- {item}" for item in metrics["missing_for_institutional_backtest"])
    return "\n".join(lines) + "\n"


def worst_months(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    eligible = [row for row in rows if row["scenario"] == "conservative"]
    return sorted(eligible, key=lambda item: item["total_r"])[:limit]


def metrics_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No rows._"
    lines = [
        "| Period | RR | Scenario | Trades | Win | Avg R | Total R | PF | Max DD R | Ambig | Timeout | TP | SL |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['period']} | {row['rr_profile']} | {row['scenario']} | {row['trades']} | "
            f"{fmt_pct(row['win_rate'])} | {fmt(row['avg_r'])} | {fmt(row['total_r'])} | {fmt(row['profit_factor'])} | "
            f"{fmt(row['max_drawdown_r'])} | {row['ambiguous_trades']} | {row['timeout_trades']} | {row['tp_trades']} | {row['sl_trades']} |"
        )
    return "\n".join(lines)


def fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
