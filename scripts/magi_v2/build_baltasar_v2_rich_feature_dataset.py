from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_JSONL = Path("data/clean/bot_a_sub3_full/cleaned_dataset.jsonl")
DEFAULT_LABELS = Path("data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_v2_rich_features")

TARGET = "tradeable_direction_rr2_first_touch"
TIMEFRAMES = ["M15", "H1", "H4", "D1"]
ROLLING_VOL_WINDOW = 12

BASE_FEATURE_COLUMNS = [
    "session",
    "hour",
    "weekday",
    "spread_pips",
    "atr",
    "daily_range_position",
    "regime",
    "anchor_open",
    "anchor_high",
    "anchor_low",
    "anchor_close",
    "candle_body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "returns_1",
    "returns_3",
    "returns_6",
    "volatility_12",
    "recent_range",
    "ema_20",
    "ema_50",
    "ema_200",
    "ema_20_50_distance",
    "ema_50_200_distance",
    "close_to_ema20",
    "close_to_ema50",
    "close_to_ema200",
    "ema_20_slope",
    "ema_50_slope",
    "rsi_14",
    "momentum",
    "market_structure",
    "structure_direction",
    "support_distance_pips",
    "resistance_distance_pips",
    "mtf_alignment_status",
    "htf_directional_alignment",
    "htf_h4_structure",
    "htf_d1_structure",
]

MTF_FIELDS = [
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "market_structure",
    "structure_direction",
    "recent_range",
    "candle_pattern",
]

DIAGNOSTIC_COLUMNS = [
    "buy_R",
    "sell_R",
    "buy_first_touch",
    "sell_first_touch",
    "same_bar_ambiguous_flag",
]

FORBIDDEN_AS_FEATURES = {
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
    "future_outcomes",
}


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading Bot A clean JSONL: %s", args.jsonl)
    raw_df = read_bot_a_jsonl(Path(args.jsonl))
    logging.info("Raw feature rows: %s", len(raw_df))
    raw_df = add_derived_features(raw_df)

    logging.info("Reading labels: %s", args.labels)
    labels_df = read_labels(Path(args.labels))
    dataset = join_labels(labels_df, raw_df)
    feature_columns = build_feature_columns(dataset)
    verify_no_forbidden_features(feature_columns)
    dataset = select_output_columns(dataset, feature_columns)

    parquet_path = output_dir / "baltasar_v2_rich_features.parquet"
    csv_path = output_dir / "baltasar_v2_rich_features.csv"
    summary_json_path = output_dir / "baltasar_v2_rich_features_summary.json"
    summary_md_path = output_dir / "baltasar_v2_rich_features_summary.md"

    dataset.to_parquet(parquet_path, index=False)
    dataset.to_csv(csv_path, index=False)

    summary = build_summary(dataset, feature_columns)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary_md_path.write_text(markdown_summary(summary), encoding="utf-8")
    logging.info("Outputs written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Baltasar v2 rich technical feature dataset.")
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="Clean Bot A sub3 JSONL.")
    parser.add_argument("--labels", default=str(DEFAULT_LABELS), help="RR2 first-touch labels parquet.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def read_bot_a_jsonl(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = json.loads(line)
            rows.append(flatten_bot_a_record(record))
            if line_number % 100000 == 0:
                logging.info("Parsed %s records", line_number)
    df = pd.DataFrame(rows)
    df["anchor_bar_timestamp"] = pd.to_datetime(df["anchor_bar_timestamp"], utc=True, errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df.sort_values(["symbol", "anchor_bar_timestamp"]).reset_index(drop=True)


def flatten_bot_a_record(record: dict[str, Any]) -> dict[str, Any]:
    symbol = str(record.get("symbol") or "").upper()
    close = as_float(record.get("anchor_close"))
    support_levels = record.get("support_levels") if isinstance(record.get("support_levels"), list) else []
    resistance_levels = record.get("resistance_levels") if isinstance(record.get("resistance_levels"), list) else []
    row: dict[str, Any] = {
        "snapshot_id_raw": record.get("snapshot_id"),
        "symbol": symbol,
        "timestamp": record.get("timestamp"),
        "anchor_bar_timestamp": record.get("anchor_bar_timestamp"),
        "active_session_raw": record.get("active_session"),
        "anchor_open": as_float(record.get("anchor_open")),
        "anchor_high": as_float(record.get("anchor_high")),
        "anchor_low": as_float(record.get("anchor_low")),
        "anchor_close": close,
        "current_price": as_float(record.get("current_price")),
        "spread_pips_raw": as_float(record.get("spread_pips")),
        "ema_20": as_float(record.get("ema_20")),
        "ema_50": as_float(record.get("ema_50")),
        "ema_200": as_float(record.get("ema_200")),
        "rsi_14": as_float(record.get("rsi_14")),
        "momentum": record.get("momentum"),
        "market_structure": record.get("market_structure"),
        "structure_direction": record.get("structure_direction"),
        "recent_range": as_float(record.get("recent_range")),
        "support_distance_pips": nearest_level_distance_pips(close, support_levels, symbol),
        "resistance_distance_pips": nearest_level_distance_pips(close, resistance_levels, symbol),
        "support_levels_count": len(support_levels),
        "resistance_levels_count": len(resistance_levels),
        "mtf_alignment_status": record.get("mtf_alignment_status"),
        "mtf_data_source_status": record.get("mtf_data_source_status"),
    }
    confluence = nested(record, "gaspar_context", "higher_timeframe_confluence") or {}
    if isinstance(confluence, dict):
        row["htf_directional_alignment"] = confluence.get("directional_alignment")
        row["htf_h4_structure"] = confluence.get("h4_structure")
        row["htf_d1_structure"] = confluence.get("d1_structure")
    features = record.get("features") if isinstance(record.get("features"), list) else []
    for item in features:
        if not isinstance(item, dict):
            continue
        timeframe = str(item.get("timeframe") or "").upper()
        if timeframe not in TIMEFRAMES:
            continue
        prefix = timeframe.lower()
        for field in MTF_FIELDS:
            value = item.get(field)
            row[f"{prefix}_{field}"] = as_float(value) if field in {"ema_20", "ema_50", "ema_200", "rsi_14", "recent_range"} else value
    return row


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    candle_range = (out["anchor_high"] - out["anchor_low"]).replace(0, pd.NA)
    out["candle_body_pct"] = (out["anchor_close"] - out["anchor_open"]).abs() / candle_range
    out["upper_wick_pct"] = (out["anchor_high"] - out[["anchor_open", "anchor_close"]].max(axis=1)) / candle_range
    out["lower_wick_pct"] = (out[["anchor_open", "anchor_close"]].min(axis=1) - out["anchor_low"]) / candle_range
    out["ema_20_50_distance"] = pips(out["ema_20"] - out["ema_50"], out["symbol"])
    out["ema_50_200_distance"] = pips(out["ema_50"] - out["ema_200"], out["symbol"])
    out["close_to_ema20"] = pips(out["anchor_close"] - out["ema_20"], out["symbol"])
    out["close_to_ema50"] = pips(out["anchor_close"] - out["ema_50"], out["symbol"])
    out["close_to_ema200"] = pips(out["anchor_close"] - out["ema_200"], out["symbol"])
    grouped = out.groupby("symbol", sort=False)
    out["returns_1"] = grouped["anchor_close"].pct_change(1)
    out["returns_3"] = grouped["anchor_close"].pct_change(3)
    out["returns_6"] = grouped["anchor_close"].pct_change(6)
    out["volatility_12"] = out.groupby("symbol", sort=False)["returns_1"].transform(
        lambda s: s.rolling(ROLLING_VOL_WINDOW, min_periods=3).std()
    )
    out["ema_20_slope"] = grouped["ema_20"].diff(1)
    out["ema_50_slope"] = grouped["ema_50"].diff(1)
    out["ema_20_slope"] = pips(out["ema_20_slope"], out["symbol"])
    out["ema_50_slope"] = pips(out["ema_50_slope"], out["symbol"])
    return out


def read_labels(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["anchor_bar_timestamp"] = pd.to_datetime(df["anchor_bar_timestamp"], utc=True, errors="coerce")
    df["join_anchor_bar_timestamp"] = df["anchor_bar_timestamp"]
    missing_anchor = df["join_anchor_bar_timestamp"].isna()
    df.loc[missing_anchor, "join_anchor_bar_timestamp"] = df.loc[missing_anchor, "timestamp"].dt.floor("5min")
    return df


def join_labels(labels_df: pd.DataFrame, raw_df: pd.DataFrame) -> pd.DataFrame:
    raw_keys = raw_df.rename(columns={"anchor_bar_timestamp": "join_anchor_bar_timestamp"})
    merged = labels_df.merge(
        raw_keys,
        on=["symbol", "join_anchor_bar_timestamp"],
        how="left",
        suffixes=("", "_raw"),
        indicator=True,
    )
    merged["rich_feature_match"] = merged["_merge"] == "both"
    merged["rich_feature_match_method"] = merged.apply(match_method, axis=1)
    merged = merged.drop(columns=["_merge"])
    if "anchor_bar_timestamp_raw" in merged.columns:
        merged["raw_anchor_bar_timestamp"] = merged["anchor_bar_timestamp_raw"]
    return merged


def match_method(row: pd.Series) -> str:
    if not bool(row.get("rich_feature_match")):
        return "missing_raw_features"
    anchor = row.get("anchor_bar_timestamp")
    join_anchor = row.get("join_anchor_bar_timestamp")
    if pd.isna(anchor):
        return "timestamp_floor_to_m5"
    if anchor == join_anchor:
        return "symbol_anchor_bar_timestamp"
    return "timestamp_floor_to_m5"


def build_feature_columns(df: pd.DataFrame) -> list[str]:
    mtf_columns = [f"{tf.lower()}_{field}" for tf in TIMEFRAMES for field in MTF_FIELDS]
    columns = [*BASE_FEATURE_COLUMNS, *mtf_columns]
    return [column for column in columns if column in df.columns]


def verify_no_forbidden_features(feature_columns: list[str]) -> None:
    forbidden = sorted(set(feature_columns) & FORBIDDEN_AS_FEATURES)
    if forbidden:
        raise ValueError(f"Forbidden columns in feature columns: {forbidden}")


def select_output_columns(df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    identity_columns = [
        "source_index",
        "snapshot_id",
        "snapshot_id_raw",
        "timestamp",
        "anchor_bar_timestamp",
        "join_anchor_bar_timestamp",
        "raw_anchor_bar_timestamp",
        "symbol",
        "entry_price",
        "rich_feature_match",
        "rich_feature_match_method",
    ]
    columns = [
        column
        for column in [*identity_columns, TARGET, *feature_columns, *DIAGNOSTIC_COLUMNS]
        if column in df.columns
    ]
    seen: set[str] = set()
    ordered = []
    for column in columns:
        if column not in seen:
            ordered.append(column)
            seen.add(column)
    return df[ordered].copy()


def build_summary(df: pd.DataFrame, feature_columns: list[str]) -> dict[str, Any]:
    diagnostic_columns = [column for column in DIAGNOSTIC_COLUMNS if column in df.columns]
    match_count = int(df["rich_feature_match"].sum())
    return {
        "schema_version": "baltasar_v2_rich_feature_dataset_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "column_count": int(len(df.columns)),
        "target": TARGET,
        "target_distribution": {str(key): int(value) for key, value in df[TARGET].value_counts(dropna=False).to_dict().items()},
        "feature_columns": feature_columns,
        "feature_column_count": len(feature_columns),
        "diagnostic_columns": diagnostic_columns,
        "null_counts": {column: int(value) for column, value in df.isna().sum().sort_values(ascending=False).to_dict().items()},
        "match": {
            "matched_rows": match_count,
            "total_rows": int(len(df)),
            "match_pct": round(match_count / len(df), 6) if len(df) else None,
            "method_distribution": {
                str(key): int(value)
                for key, value in df["rich_feature_match_method"].value_counts(dropna=False).to_dict().items()
            },
        },
        "temporal_range": {
            "start": df["timestamp"].min().isoformat(),
            "end": df["timestamp"].max().isoformat(),
        },
        "forbidden_feature_check": {
            "passed": True,
            "forbidden_columns_in_features": [],
        },
        "technical_decisions": [
            "Labels are left-joined to Bot A clean features by symbol + anchor_bar_timestamp.",
            "If anchor_bar_timestamp is missing in labels, timestamp floor_to_m5 is used as fallback.",
            "M5 candle/EMA/return/volatility derived features use current and past rows only.",
            "buy_R/sell_R/first_touch diagnostics are retained for evaluation but excluded from feature_columns.",
            "future outcomes and label columns are not included in feature_columns.",
        ],
    }


def markdown_summary(summary: dict[str, Any]) -> str:
    null_top = [
        {"column": column, "nulls": count}
        for column, count in list(summary["null_counts"].items())[:20]
    ]
    lines = [
        "# Baltasar v2 Rich Feature Dataset",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['rows']}`",
        f"- Columns: `{summary['column_count']}`",
        f"- Feature columns: `{summary['feature_column_count']}`",
        f"- Match pct: `{summary['match']['match_pct']:.4%}`",
        f"- Temporal range: `{summary['temporal_range']['start']}` to `{summary['temporal_range']['end']}`",
        "",
        "## Target Distribution",
        "",
        table_from_dict(summary["target_distribution"], ["label", "rows"]),
        "",
        "## Match Method Distribution",
        "",
        table_from_dict(summary["match"]["method_distribution"], ["method", "rows"]),
        "",
        "## Feature Columns",
        "",
        ", ".join(summary["feature_columns"]),
        "",
        "## Diagnostic Columns",
        "",
        ", ".join(summary["diagnostic_columns"]),
        "",
        "## Top Null Counts",
        "",
        table_from_rows(null_top),
        "",
        "## Technical Decisions",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["technical_decisions"])
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


def nearest_level_distance_pips(price: float | None, levels: list[Any], symbol: str) -> float | None:
    if price is None:
        return None
    numeric = [as_float(level) for level in levels]
    numeric = [level for level in numeric if level is not None]
    if not numeric:
        return None
    nearest = min(abs(price - level) for level in numeric)
    return round(nearest / pip_size(symbol), 6)


def pips(values: Any, symbols: pd.Series | str) -> Any:
    if isinstance(symbols, pd.Series):
        pip_sizes = symbols.astype(str).str.upper().map(lambda symbol: pip_size(symbol))
        return values / pip_sizes
    return values / pip_size(str(symbols))


def pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def nested(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
