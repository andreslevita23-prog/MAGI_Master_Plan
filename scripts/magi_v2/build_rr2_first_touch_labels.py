from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_INTRABAR_JSONL = Path("data/clean/bot_a_sub3_full/cleaned_dataset.jsonl")
DEFAULT_FIRST_TOUCH_TRADES = RUN_DIR / "ceo_v2_tradeable" / "first_touch" / "first_touch_trades.csv"
DEFAULT_CEO_V2_DATASET = RUN_DIR / "ceo_v2_tradeable" / "ceo_v2_tradeable_dataset.parquet"
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/rr2_first_touch_labels")

SL_PIPS = 10.0
TP_PIPS = 20.0
HORIZON_BARS = 48
TARGET = "tradeable_direction_rr2_first_touch"

FEATURE_COLUMNS = [
    "session",
    "hour",
    "weekday",
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


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading CEO v2 dataset: %s", args.ceo_v2_dataset)
    ceo_df = pd.read_parquet(args.ceo_v2_dataset)
    ceo_df["timestamp"] = pd.to_datetime(ceo_df["timestamp"], utc=True, errors="coerce")

    logging.info("Reading M5 intrabar dataset: %s", args.intrabar_jsonl)
    intrabar = load_intrabar(Path(args.intrabar_jsonl))
    logging.info("Loaded symbols: %s", {symbol: len(data['rows']) for symbol, data in intrabar.items()})

    reference = load_reference_first_touch(Path(args.first_touch_trades))
    rows = build_label_rows(ceo_df, intrabar)
    labels_df = pd.DataFrame(rows)

    parquet_path = output_dir / "rr2_first_touch_labels.parquet"
    csv_path = output_dir / "rr2_first_touch_labels.csv"
    summary_json_path = output_dir / "rr2_first_touch_labels_summary.json"
    summary_md_path = output_dir / "rr2_first_touch_labels_summary.md"

    labels_df.to_parquet(parquet_path, index=False)
    labels_df.to_csv(csv_path, index=False)

    summary = build_summary(labels_df, reference)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary_md_path.write_text(markdown_summary(summary), encoding="utf-8")

    logging.info("Rows generated: %s", len(labels_df))
    logging.info("Label distribution: %s", summary["label_distribution"])
    logging.info("Outputs written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RR 1:2 M5 first-touch labels for Baltasar v2.")
    parser.add_argument("--intrabar-jsonl", default=str(DEFAULT_INTRABAR_JSONL), help="Bot A clean M5 JSONL with OHLC.")
    parser.add_argument("--first-touch-trades", default=str(DEFAULT_FIRST_TOUCH_TRADES), help="CEO v2 first-touch trades CSV for reference/audit.")
    parser.add_argument("--ceo-v2-dataset", default=str(DEFAULT_CEO_V2_DATASET), help="CEO v2 tradeable dataset parquet with context/features.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


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
            snapshot_id = record.get("snapshot_id")
            session = record.get("active_session")
            if not symbol or timestamp is None or None in {open_, high, low, close}:
                continue
            rows_by_symbol[symbol].append(
                {
                    "timestamp": timestamp,
                    "snapshot_id": snapshot_id,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "spread_pips": spread,
                    "session": session,
                }
            )

    intrabar: dict[str, dict[str, Any]] = {}
    for symbol, rows in rows_by_symbol.items():
        rows.sort(key=lambda row: row["timestamp"])
        index_by_ts = {row["timestamp"]: idx for idx, row in enumerate(rows)}
        intrabar[symbol] = {"rows": rows, "index_by_ts": index_by_ts}
    return intrabar


def load_reference_first_touch(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"available": False, "reason": "missing_first_touch_trades_csv"}
    usecols = ["source_index", "rr_profile", "intrabar_status", "exit_reason"]
    df = pd.read_csv(path, usecols=lambda col: col in usecols)
    rr2 = df[df["rr_profile"] == "rr_1_2"] if "rr_profile" in df.columns else df.iloc[0:0]
    return {
        "available": True,
        "rows": int(len(df)),
        "rr2_rows": int(len(rr2)),
        "rr2_exit_reason_distribution": rr2["exit_reason"].value_counts(dropna=False).to_dict() if "exit_reason" in rr2.columns else {},
    }


def build_label_rows(ceo_df: pd.DataFrame, intrabar: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(ceo_df.itertuples(index=False)):
        row_dict = row._asdict()
        symbol = str(row_dict.get("symbol") or "").upper()
        ts_value = row_dict.get("timestamp")
        timestamp = ts_value.to_pydatetime() if hasattr(ts_value, "to_pydatetime") else ts_value
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        candle, anchor_timestamp, match_method = get_entry_candle(intrabar, symbol, timestamp)

        if candle is None:
            buy = missing_outcome("missing_entry_bar")
            sell = missing_outcome("missing_entry_bar")
            entry_price = None
            spread = as_float(row_dict.get("spread"))
            snapshot_id = None
        else:
            entry_price = float(candle["close"])
            spread = as_float(row_dict.get("spread"))
            if spread is None:
                spread = as_float(candle.get("spread_pips")) or 0.0
            snapshot_id = candle.get("snapshot_id")
            entry_idx = intrabar[symbol]["index_by_ts"][anchor_timestamp]
            buy = evaluate_direction(intrabar[symbol]["rows"], entry_idx, symbol, "BUY", entry_price, spread)
            sell = evaluate_direction(intrabar[symbol]["rows"], entry_idx, symbol, "SELL", entry_price, spread)

        label, same_bar = choose_label(buy, sell)
        output = {
            "source_index": idx,
            "snapshot_id": snapshot_id,
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "anchor_bar_timestamp": anchor_timestamp.isoformat().replace("+00:00", "Z") if anchor_timestamp else "",
            "entry_match_method": match_method,
            "symbol": symbol,
            "entry_price": entry_price,
            "buy_outcome": buy["outcome"],
            "sell_outcome": sell["outcome"],
            "buy_R": buy["r"],
            "sell_R": sell["r"],
            "buy_first_touch": buy["first_touch"],
            "sell_first_touch": sell["first_touch"],
            "buy_bars_to_exit": buy["bars_to_exit"],
            "sell_bars_to_exit": sell["bars_to_exit"],
            TARGET: label,
            "same_bar_ambiguous_flag": same_bar,
            "spread_pips": spread,
        }
        for column in FEATURE_COLUMNS:
            output[column] = row_dict.get(column)
        rows.append(output)
    return rows


def get_entry_candle(intrabar: dict[str, dict[str, Any]], symbol: str, timestamp: datetime) -> tuple[dict[str, Any] | None, datetime | None, str]:
    symbol_data = intrabar.get(symbol)
    if not symbol_data:
        return None, None, "missing_symbol"
    idx = symbol_data["index_by_ts"].get(timestamp)
    if idx is not None:
        return symbol_data["rows"][idx], timestamp, "exact_timestamp"
    floored = floor_to_m5(timestamp)
    idx = symbol_data["index_by_ts"].get(floored)
    if idx is not None:
        return symbol_data["rows"][idx], floored, "floor_to_m5"
    return None, floored, "missing_entry_bar"


def evaluate_direction(
    rows: list[dict[str, Any]],
    entry_idx: int,
    symbol: str,
    direction: str,
    entry_price: float,
    spread: float,
) -> dict[str, Any]:
    future = rows[entry_idx + 1 : entry_idx + 1 + HORIZON_BARS]
    if len(future) < HORIZON_BARS:
        return missing_outcome("INSUFFICIENT_FUTURE_BARS", available_future_bars=len(future))
    pip = pip_size(symbol)
    if direction == "BUY":
        tp_price = entry_price + TP_PIPS * pip
        sl_price = entry_price - SL_PIPS * pip
    else:
        tp_price = entry_price - TP_PIPS * pip
        sl_price = entry_price + SL_PIPS * pip

    for offset, bar in enumerate(future, start=1):
        if direction == "BUY":
            hit_tp = float(bar["high"]) >= tp_price
            hit_sl = float(bar["low"]) <= sl_price
        else:
            hit_tp = float(bar["low"]) <= tp_price
            hit_sl = float(bar["high"]) >= sl_price
        if hit_tp and hit_sl:
            return {
                "outcome": "SAME_BAR_AMBIGUOUS",
                "first_touch": "SAME_BAR_AMBIGUOUS",
                "r": -1.0,
                "bars_to_exit": offset,
                "available_future_bars": HORIZON_BARS,
            }
        if hit_tp:
            return {
                "outcome": "TP_FIRST",
                "first_touch": "TP",
                "r": round(TP_PIPS / SL_PIPS, 6),
                "bars_to_exit": offset,
                "available_future_bars": HORIZON_BARS,
            }
        if hit_sl:
            return {
                "outcome": "SL_FIRST",
                "first_touch": "SL",
                "r": -1.0,
                "bars_to_exit": offset,
                "available_future_bars": HORIZON_BARS,
            }

    last_close = float(future[-1]["close"])
    directional_pips = ((last_close - entry_price) / pip) if direction == "BUY" else ((entry_price - last_close) / pip)
    r_value = (directional_pips - spread) / SL_PIPS
    return {
        "outcome": "CLOSE_BY_TIMEOUT",
        "first_touch": "TIMEOUT",
        "r": round(r_value, 6),
        "bars_to_exit": HORIZON_BARS,
        "available_future_bars": HORIZON_BARS,
    }


def missing_outcome(outcome: str, available_future_bars: int = 0) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "first_touch": "INSUFFICIENT",
        "r": None,
        "bars_to_exit": None,
        "available_future_bars": available_future_bars,
    }


def choose_label(buy: dict[str, Any], sell: dict[str, Any]) -> tuple[str, bool]:
    same_bar = buy["outcome"] == "SAME_BAR_AMBIGUOUS" or sell["outcome"] == "SAME_BAR_AMBIGUOUS"
    if same_bar:
        return "DO_NOTHING", True
    buy_r = as_float(buy.get("r"))
    sell_r = as_float(sell.get("r"))
    buy_tp = buy["outcome"] == "TP_FIRST"
    sell_tp = sell["outcome"] == "TP_FIRST"
    if buy_tp and sell_tp:
        if buy_r is not None and sell_r is not None and buy_r > sell_r:
            return "ENTER_BUY", False
        if buy_r is not None and sell_r is not None and sell_r > buy_r:
            return "ENTER_SELL", False
        return "DO_NOTHING", False
    if buy_tp and buy_r is not None and (sell_r is None or buy_r > sell_r):
        return "ENTER_BUY", False
    if sell_tp and sell_r is not None and (buy_r is None or sell_r > buy_r):
        return "ENTER_SELL", False
    return "DO_NOTHING", False


def build_summary(df: pd.DataFrame, reference: dict[str, Any]) -> dict[str, Any]:
    label_dist = df[TARGET].value_counts(dropna=False).to_dict()
    same_bar_count = int(df["same_bar_ambiguous_flag"].sum())
    temporal = {
        "start": str(df["timestamp"].min()),
        "end": str(df["timestamp"].max()),
        "years": df["timestamp"].str.slice(0, 4).value_counts().sort_index().to_dict(),
    }
    avg_r_by_label = (
        df.groupby(TARGET)[["buy_R", "sell_R"]]
        .mean(numeric_only=True)
        .round(6)
        .reset_index()
        .to_dict("records")
    )
    outcome_distribution = {
        "buy_outcome": df["buy_outcome"].value_counts(dropna=False).to_dict(),
        "sell_outcome": df["sell_outcome"].value_counts(dropna=False).to_dict(),
    }
    entry_match_method_distribution = df["entry_match_method"].value_counts(dropna=False).to_dict()
    return {
        "schema_version": "magi_v2_rr2_first_touch_labels_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "target": TARGET,
        "label_distribution": {str(k): int(v) for k, v in label_dist.items()},
        "same_bar_ambiguous_count": same_bar_count,
        "same_bar_ambiguous_pct": round(same_bar_count / len(df), 6) if len(df) else None,
        "avg_r_by_label": avg_r_by_label,
        "outcome_distribution": outcome_distribution,
        "entry_match_method_distribution": {str(k): int(v) for k, v in entry_match_method_distribution.items()},
        "temporal_coverage": temporal,
        "null_counts": {column: int(value) for column, value in df.isna().sum().to_dict().items()},
        "reference_first_touch_trades": reference,
        "assumptions": [
            "Uses real M5 first-touch from Bot A clean anchor candles, not aggregated future_return labels.",
            "Entry price is anchor_close at the snapshot timestamp.",
            "SL is fixed at 10 pips and TP is fixed at 20 pips.",
            "The next 48 M5 candles are evaluated in timestamp order.",
            "same_bar_ambiguous is labeled DO_NOTHING for the principal target.",
            "Timeout R subtracts spread_pips; TP/SL touch levels use raw fixed pip distances because bid/ask OHLC is not available.",
            "This dataset contains outcome diagnostics and labels; future model feature lists must exclude outcome columns.",
        ],
    }


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# MAGI v2 RR 1:2 First-Touch Labels",
        "",
        "## Scope",
        "",
        "- Target: `tradeable_direction_rr2_first_touch`.",
        "- Classes: `ENTER_BUY`, `ENTER_SELL`, `DO_NOTHING`.",
        "- Intrabar source: Bot A clean M5 candles.",
        "- Rule: hypothetical BUY and SELL are evaluated with SL 10 pips / TP 20 pips over 48 future M5 bars.",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['rows']}`",
        f"- Temporal coverage: `{summary['temporal_coverage']['start']}` to `{summary['temporal_coverage']['end']}`",
        f"- Same-bar ambiguous: `{summary['same_bar_ambiguous_count']}` (`{summary['same_bar_ambiguous_pct']:.4%}`)",
        "",
        "## Label Distribution",
        "",
        table_from_dict(summary["label_distribution"], ["label", "rows"]),
        "",
        "## Outcome Distribution",
        "",
        "### BUY hypothetical",
        "",
        table_from_dict(summary["outcome_distribution"]["buy_outcome"], ["outcome", "rows"]),
        "",
        "### SELL hypothetical",
        "",
        table_from_dict(summary["outcome_distribution"]["sell_outcome"], ["outcome", "rows"]),
        "",
        "## Avg R by Label",
        "",
        table_from_rows(summary["avg_r_by_label"]),
        "",
        "## Entry Match Method",
        "",
        table_from_dict(summary["entry_match_method_distribution"], ["method", "rows"]),
        "",
        "## Assumptions",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["assumptions"])
    return "\n".join(lines) + "\n"


def table_from_dict(data: dict[str, Any], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for key, value in data.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def table_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)


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


def floor_to_m5(value: datetime) -> datetime:
    minute = value.minute - (value.minute % 5)
    return value.replace(minute=minute, second=0, microsecond=0)


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


def pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


if __name__ == "__main__":
    raise SystemExit(main())
