from __future__ import annotations

import argparse
import csv
import json
import logging
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_SIMULATED_TRADES = RUN_DIR / "ceo_v2_tradeable" / "r_simulation" / "simulated_trades.csv"
DEFAULT_INTRABAR_JSONL = Path("data/clean/bot_a_sub3_full/cleaned_dataset.jsonl")
DEFAULT_PROXY_METRICS = RUN_DIR / "ceo_v2_tradeable" / "r_simulation" / "r_simulation_metrics.json"
DEFAULT_OUTPUT_DIR = RUN_DIR / "ceo_v2_tradeable" / "first_touch"

HORIZON_BARS = 48
RR_PROFILES = {
    "rr_1_1": {"sl_pips": 10.0, "tp_pips": 10.0},
    "rr_1_1_5": {"sl_pips": 10.0, "tp_pips": 15.0},
    "rr_1_2": {"sl_pips": 10.0, "tp_pips": 20.0},
}


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading policy trades: %s", args.simulated_trades)
    policy_trades = load_policy_trades(Path(args.simulated_trades))
    logging.info("Unique policy trades: %s", len(policy_trades))

    logging.info("Reading M5 intrabar candles: %s", args.intrabar_jsonl)
    intrabar = load_intrabar(Path(args.intrabar_jsonl))
    logging.info("Loaded symbols: %s", {symbol: len(data['timestamps']) for symbol, data in intrabar.items()})

    first_touch_rows = build_first_touch_rows(policy_trades, intrabar)
    write_csv(output_dir / "first_touch_trades.csv", first_touch_rows)

    proxy_metrics = load_json(Path(args.proxy_metrics)) if Path(args.proxy_metrics).exists() else {}
    metrics = build_metrics(first_touch_rows, proxy_metrics)
    (output_dir / "first_touch_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(output_dir / "metrics_by_rr.csv", metrics["by_rr"])
    write_csv(output_dir / "metrics_by_year.csv", metrics["by_year"])
    write_csv(output_dir / "metrics_by_month.csv", metrics["by_month"])
    (output_dir / "first_touch_summary.md").write_text(markdown_summary(metrics), encoding="utf-8")
    logging.info("First-touch outputs written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build M5 intrabar first-touch validation for CEO v2 conservative_core trades.")
    parser.add_argument("--simulated-trades", default=str(DEFAULT_SIMULATED_TRADES), help="Proxy simulated_trades.csv path.")
    parser.add_argument("--intrabar-jsonl", default=str(DEFAULT_INTRABAR_JSONL), help="Bot A clean M5 JSONL with OHLC.")
    parser.add_argument("--proxy-metrics", default=str(DEFAULT_PROXY_METRICS), help="Previous proxy metrics JSON for comparison.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def load_policy_trades(path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    required = {"source_index", "timestamp", "symbol", "direction", "session", "spread"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")
    base = (
        df.sort_values(["source_index", "timestamp"])
        .drop_duplicates(subset=["source_index"])
        [["source_index", "timestamp", "symbol", "direction", "session", "spread"]]
        .copy()
    )
    base["timestamp"] = pd.to_datetime(base["timestamp"], utc=True, errors="coerce")
    base["year"] = base["timestamp"].dt.year.astype("Int64").astype(str)
    base["month"] = base["timestamp"].dt.strftime("%Y-%m")
    return base.to_dict("records")


def load_intrabar(path: Path) -> dict[str, dict[str, Any]]:
    rows_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            timeframe = str(record.get("anchor_timeframe") or record.get("timeframe") or "").upper()
            if timeframe and timeframe != "M5":
                continue
            symbol = str(record.get("symbol") or "").upper()
            timestamp = parse_ts(record.get("anchor_bar_timestamp") or record.get("timestamp"))
            open_ = as_float(record.get("anchor_open") if record.get("anchor_open") is not None else record.get("open"))
            high = as_float(record.get("anchor_high") if record.get("anchor_high") is not None else record.get("high"))
            low = as_float(record.get("anchor_low") if record.get("anchor_low") is not None else record.get("low"))
            close = as_float(record.get("anchor_close") if record.get("anchor_close") is not None else record.get("close"))
            spread = as_float(record.get("spread_pips"))
            if not symbol or timestamp is None or None in {open_, high, low, close}:
                continue
            rows_by_symbol[symbol].append(
                {
                    "timestamp": timestamp,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "spread_pips": spread,
                }
            )

    intrabar: dict[str, dict[str, Any]] = {}
    for symbol, rows in rows_by_symbol.items():
        rows.sort(key=lambda row: row["timestamp"])
        intrabar[symbol] = {
            "rows": rows,
            "timestamps": [row["timestamp"] for row in rows],
        }
    return intrabar


def build_first_touch_rows(policy_trades: list[dict[str, Any]], intrabar: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for trade in policy_trades:
        symbol = str(trade.get("symbol") or "").upper()
        entry_ts = trade["timestamp"].to_pydatetime() if hasattr(trade["timestamp"], "to_pydatetime") else trade["timestamp"]
        if entry_ts.tzinfo is None:
            entry_ts = entry_ts.replace(tzinfo=timezone.utc)
        direction = str(trade.get("direction") or "").upper()
        source_index = int(trade["source_index"])
        spread = as_float(trade.get("spread")) or 0.0
        symbol_data = intrabar.get(symbol)
        for rr_profile, profile in RR_PROFILES.items():
            result = evaluate_trade(symbol_data, symbol, entry_ts, direction, profile["sl_pips"], profile["tp_pips"], spread)
            output.append(
                {
                    "source_index": source_index,
                    "timestamp": iso(entry_ts),
                    "year": str(trade.get("year") or ""),
                    "month": str(trade.get("month") or ""),
                    "symbol": symbol,
                    "session": trade.get("session"),
                    "direction": direction,
                    "rr_profile": rr_profile,
                    "sl_pips": profile["sl_pips"],
                    "tp_pips": profile["tp_pips"],
                    "spread": spread,
                    **result,
                }
            )
    return output


def evaluate_trade(
    symbol_data: dict[str, Any] | None,
    symbol: str,
    entry_ts: datetime,
    direction: str,
    sl_pips: float,
    tp_pips: float,
    spread: float,
) -> dict[str, Any]:
    if symbol_data is None:
        return insufficient("missing_symbol_intrabar")
    timestamps: list[datetime] = symbol_data["timestamps"]
    rows: list[dict[str, Any]] = symbol_data["rows"]
    entry_pos = bisect_right(timestamps, entry_ts) - 1
    if entry_pos < 0 or timestamps[entry_pos] != entry_ts:
        return insufficient("missing_entry_bar")

    entry_bar = rows[entry_pos]
    entry_price = float(entry_bar["close"])
    future = rows[entry_pos + 1 : entry_pos + 1 + HORIZON_BARS]
    if len(future) < HORIZON_BARS:
        return insufficient("insufficient_future_bars", entry_price=entry_price, available_future_bars=len(future))

    pip = pip_size(symbol)
    if direction == "BUY":
        tp_price = entry_price + (tp_pips * pip)
        sl_price = entry_price - (sl_pips * pip)
    elif direction == "SELL":
        tp_price = entry_price - (tp_pips * pip)
        sl_price = entry_price + (sl_pips * pip)
    else:
        return insufficient("invalid_direction", entry_price=entry_price)

    for offset, bar in enumerate(future, start=1):
        if direction == "BUY":
            hit_tp = float(bar["high"]) >= tp_price
            hit_sl = float(bar["low"]) <= sl_price
        else:
            hit_tp = float(bar["low"]) <= tp_price
            hit_sl = float(bar["high"]) >= sl_price
        if hit_tp and hit_sl:
            return touch_result("SAME_BAR_AMBIGUOUS", entry_price, bar, offset, tp_price, sl_price, sl_pips, tp_pips, spread)
        if hit_tp:
            return touch_result("TP_FIRST", entry_price, bar, offset, tp_price, sl_price, sl_pips, tp_pips, spread)
        if hit_sl:
            return touch_result("SL_FIRST", entry_price, bar, offset, tp_price, sl_price, sl_pips, tp_pips, spread)

    last = future[-1]
    directional_pips = directional_move_pips(direction, entry_price, float(last["close"]), pip) - spread
    return {
        "intrabar_status": "OK",
        "exit_reason": "CLOSE_BY_TIMEOUT",
        "entry_price": round(entry_price, 8),
        "exit_timestamp": iso(last["timestamp"]),
        "exit_price": round(float(last["close"]), 8),
        "bars_to_exit": HORIZON_BARS,
        "tp_price": round(tp_price, 8),
        "sl_price": round(sl_price, 8),
        "available_future_bars": HORIZON_BARS,
        "r": round(directional_pips / sl_pips, 6),
        "r_resolved": round(directional_pips / sl_pips, 6),
        "r_conservative_same_bar_sl": round(directional_pips / sl_pips, 6),
    }


def insufficient(reason: str, entry_price: float | None = None, available_future_bars: int = 0) -> dict[str, Any]:
    return {
        "intrabar_status": "INSUFFICIENT",
        "exit_reason": reason,
        "entry_price": round(entry_price, 8) if entry_price is not None else None,
        "exit_timestamp": "",
        "exit_price": None,
        "bars_to_exit": None,
        "tp_price": None,
        "sl_price": None,
        "available_future_bars": available_future_bars,
        "r": None,
        "r_resolved": None,
        "r_conservative_same_bar_sl": None,
    }


def touch_result(
    reason: str,
    entry_price: float,
    bar: dict[str, Any],
    offset: int,
    tp_price: float,
    sl_price: float,
    sl_pips: float,
    tp_pips: float,
    spread: float,
) -> dict[str, Any]:
    if reason == "TP_FIRST":
        r_value = round(tp_pips / sl_pips, 6)
        resolved = r_value
        conservative = r_value
        exit_price = tp_price
    elif reason == "SL_FIRST":
        r_value = -1.0
        resolved = r_value
        conservative = r_value
        exit_price = sl_price
    else:
        r_value = None
        resolved = None
        conservative = -1.0
        exit_price = None
    return {
        "intrabar_status": "OK",
        "exit_reason": reason,
        "entry_price": round(entry_price, 8),
        "exit_timestamp": iso(bar["timestamp"]),
        "exit_price": round(exit_price, 8) if exit_price is not None else None,
        "bars_to_exit": offset,
        "tp_price": round(tp_price, 8),
        "sl_price": round(sl_price, 8),
        "available_future_bars": HORIZON_BARS,
        "r": r_value,
        "r_resolved": resolved,
        "r_conservative_same_bar_sl": conservative,
    }


def build_metrics(rows: list[dict[str, Any]], proxy_metrics: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "schema_version": "ceo_v2_first_touch_intrabar_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "policy": "conservative_core",
        "timeframe": "M5",
        "horizon_bars": HORIZON_BARS,
        "technical_decisions": [
            "Uses Bot A clean M5 anchor candles from data/clean/bot_a_sub3_full/cleaned_dataset.jsonl.",
            "Uses anchor_close as entry_price because CEO decisions are closed-bar snapshots.",
            "Evaluates future M5 candles after the entry bar only.",
            "Touch rules follow raw TP/SL price levels. Timeout R subtracts spread pips.",
            "same_bar_ambiguous remains unresolved at M5; headline avg_r treats it as SL for conservative comparability and reports resolved-only R separately.",
        ],
        "global": metric_row(rows, "global", "all", "all"),
        "by_rr": grouped_metrics(rows, "rr_profile"),
        "by_year": grouped_metrics(rows, "year"),
        "by_month": grouped_metrics(rows, "month"),
        "proxy_comparison": compare_proxy(rows, proxy_metrics),
    }
    return metrics


def grouped_metrics(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(group_key) or "UNKNOWN")].append(row)
    return [metric_row(items, group_key, group_value, "all") for group_value, items in sorted(groups.items())]


def metric_row(rows: list[dict[str, Any]], group: str, period: str, scenario: str) -> dict[str, Any]:
    ok = [row for row in rows if row["intrabar_status"] == "OK"]
    resolved = [row for row in ok if row["exit_reason"] != "SAME_BAR_AMBIGUOUS"]
    r_values = [as_float(row.get("r_conservative_same_bar_sl")) for row in ok if as_float(row.get("r_conservative_same_bar_sl")) is not None]
    resolved_r = [as_float(row.get("r_resolved")) for row in resolved if as_float(row.get("r_resolved")) is not None]
    counts = Counter(row["exit_reason"] for row in ok)
    wins = [value for value in r_values if value is not None and value > 0]
    losses = [value for value in r_values if value is not None and value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "group": group,
        "period": period,
        "scenario": scenario,
        "rows": len(rows),
        "trades_evaluated": len(rows),
        "trades_with_intrabar": len(ok),
        "intrabar_coverage": safe_div(len(ok), len(rows)),
        "tp_first": counts.get("TP_FIRST", 0),
        "sl_first": counts.get("SL_FIRST", 0),
        "timeout": counts.get("CLOSE_BY_TIMEOUT", 0),
        "same_bar_ambiguous": counts.get("SAME_BAR_AMBIGUOUS", 0),
        "win_rate": safe_div(len(wins), len(r_values)),
        "avg_r": round_float(sum(r_values) / len(r_values)) if r_values else None,
        "total_r": round_float(sum(r_values)) if r_values else None,
        "avg_r_resolved_only": round_float(sum(resolved_r) / len(resolved_r)) if resolved_r else None,
        "total_r_resolved_only": round_float(sum(resolved_r)) if resolved_r else None,
        "profit_factor": round_float(gross_profit / gross_loss) if gross_loss else None,
        "max_drawdown_r": round_float(max_drawdown(r_values)),
    }


def compare_proxy(rows: list[dict[str, Any]], proxy_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    first_touch_by_rr = {row["period"]: row for row in grouped_metrics(rows, "rr_profile")}
    proxy_rows = proxy_metrics.get("by_rr", []) if isinstance(proxy_metrics, dict) else []
    comparison: list[dict[str, Any]] = []
    for rr_profile, ft_row in first_touch_by_rr.items():
        conservative = next((row for row in proxy_rows if row.get("rr_profile") == rr_profile and row.get("scenario") == "conservative"), {})
        optimistic = next((row for row in proxy_rows if row.get("rr_profile") == rr_profile and row.get("scenario") == "optimistic"), {})
        comparison.append(
            {
                "rr_profile": rr_profile,
                "first_touch_avg_r": ft_row.get("avg_r"),
                "first_touch_total_r": ft_row.get("total_r"),
                "first_touch_max_drawdown_r": ft_row.get("max_drawdown_r"),
                "proxy_conservative_avg_r": conservative.get("avg_r"),
                "proxy_conservative_total_r": conservative.get("total_r"),
                "proxy_optimistic_avg_r": optimistic.get("avg_r"),
                "proxy_optimistic_total_r": optimistic.get("total_r"),
            }
        )
    return comparison


def markdown_summary(metrics: dict[str, Any]) -> str:
    lines = [
        "# CEO v2 Intrabar First-Touch Summary",
        "",
        "## Scope",
        "",
        "- Policy: `conservative_core`.",
        "- Intrabar source: Bot A clean M5 anchor candles.",
        "- Entry price: `anchor_close` at the CEO decision timestamp.",
        "- Horizon: 48 future M5 bars.",
        "- Same-bar TP/SL remains ambiguous at M5 resolution.",
        "",
        "## Global Metrics",
        "",
        metric_markdown(metrics["global"]),
        "",
        "## By RR",
        "",
        table_markdown(metrics["by_rr"], ["period", "trades_with_intrabar", "intrabar_coverage", "tp_first", "sl_first", "timeout", "same_bar_ambiguous", "avg_r", "total_r", "profit_factor", "max_drawdown_r"]),
        "",
        "## Proxy Comparison",
        "",
        table_markdown(metrics["proxy_comparison"], ["rr_profile", "first_touch_avg_r", "first_touch_total_r", "proxy_conservative_avg_r", "proxy_conservative_total_r", "proxy_optimistic_avg_r", "proxy_optimistic_total_r"]),
        "",
        "## Technical Notes",
        "",
    ]
    lines.extend(f"- {item}" for item in metrics["technical_decisions"])
    return "\n".join(lines) + "\n"


def metric_markdown(row: dict[str, Any]) -> str:
    keys = ["trades_evaluated", "trades_with_intrabar", "intrabar_coverage", "tp_first", "sl_first", "timeout", "same_bar_ambiguous", "avg_r", "total_r", "profit_factor", "max_drawdown_r"]
    return table_markdown([row], keys)


def table_markdown(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(format_value(row.get(column)) for column in columns) + " |")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def directional_move_pips(direction: str, entry: float, close: float, pip: float) -> float:
    if direction == "BUY":
        return (close - entry) / pip
    return (entry - close) / pip


def safe_div(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return round_float(numerator / denominator)


def round_float(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def max_drawdown(r_values: list[float | None]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in r_values:
        if value is None:
            continue
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
