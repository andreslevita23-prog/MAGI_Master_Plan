from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_INPUT = DEFAULT_RUN_DIR / "ceo_training_records.jsonl"
DEFAULT_CSV_OUTPUT = DEFAULT_RUN_DIR / "ceo_final_dataset.csv"
DEFAULT_PARQUET_OUTPUT = DEFAULT_RUN_DIR / "ceo_final_dataset.parquet"
DEFAULT_SUMMARY_OUTPUT = DEFAULT_RUN_DIR / "ceo_final_dataset_summary.json"

HORIZONS = ("12", "48", "96", "288")
CLEAR_EDGE_PIPS = 3.0

FINAL_COLUMNS = [
    "timestamp",
    "symbol",
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
    "future_outcome_h12",
    "future_outcome_h48",
    "future_outcome_h96",
    "future_outcome_h288",
    "ceo_label_h48",
]


def main() -> int:
    args = parse_args()
    setup_logging()

    input_path = Path(args.input)
    csv_output = Path(args.csv_output)
    parquet_output = Path(args.parquet_output)
    summary_output = Path(args.summary_output)

    logging.info("Reading CEO JSONL: %s", input_path)
    rows, summary_stats = build_rows(input_path)
    logging.info("Rows flattened: %s", len(rows))

    csv_output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(csv_output, rows)
    logging.info("CSV written: %s", csv_output)

    write_parquet(parquet_output, rows)
    logging.info("Parquet written: %s", parquet_output)

    summary = build_summary(rows, summary_stats)
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    logging.info("Summary written: %s", summary_output)
    logging.info("Label distribution H48: %s", dict(summary["label_distribution"]))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build final tabular CEO-MAGI dataset.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input raw CEO JSONL path.")
    parser.add_argument("--csv-output", default=str(DEFAULT_CSV_OUTPUT), help="Output CSV path.")
    parser.add_argument("--parquet-output", default=str(DEFAULT_PARQUET_OUTPUT), help="Output Parquet path.")
    parser.add_argument("--summary-output", default=str(DEFAULT_SUMMARY_OUTPUT), help="Output summary JSON path.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_rows(input_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input JSONL not found: {input_path}")

    rows: list[dict[str, Any]] = []
    parse_errors = 0
    with input_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                logging.warning("Skipping invalid JSON at line %s", line_number)
                continue
            rows.append(flatten_record(record))
            if line_number % 50000 == 0:
                logging.info("Processed %s lines", line_number)

    return rows, {"parse_errors": parse_errors}


def flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    features = as_dict(record.get("features_at_decision_time"))
    gaspar_context = as_dict(features.get("gaspar_context"))
    timing = as_dict(gaspar_context.get("timing_quality"))
    day = as_dict(gaspar_context.get("day_context"))
    htf = as_dict(gaspar_context.get("higher_timeframe_confluence"))
    position = as_dict(gaspar_context.get("price_structure_position"))

    timestamp = clean_str(record.get("timestamp"))
    parsed_ts = parse_timestamp(timestamp)
    session = first_non_empty(features.get("active_session"), timing.get("active_session"))
    atr = as_float(first_non_empty(timing.get("daily_atr_consumed_pct"), day.get("current_d1_range_vs_atr")))
    daily_range_position = as_float(position.get("position_in_d1_range"))

    melchor_vote = as_dict(record.get("melchor_vote"))
    baltasar_vote = as_dict(record.get("baltasar_vote"))
    gaspar_vote = as_dict(record.get("gaspar_vote"))
    outcomes = as_dict(record.get("future_outcomes"))

    melchor_signal = clean_str(melchor_vote.get("vote")) or "UNKNOWN"
    baltasar_signal = clean_str(baltasar_vote.get("direction")) or "NEUTRAL"
    gaspar_signal = clean_str(gaspar_vote.get("quality")) or "UNKNOWN"

    row = {
        "timestamp": timestamp,
        "symbol": clean_str(record.get("symbol") or features.get("symbol")),
        "session": clean_str(session),
        "hour": parsed_ts.hour if parsed_ts else None,
        "weekday": day_name(parsed_ts, day.get("day_of_week")),
        "spread": as_float(features.get("spread_pips")),
        "atr": atr,
        "daily_range_position": daily_range_position,
        "regime": regime_label(session, htf, atr, daily_range_position),
        "melchor_signal": melchor_signal,
        "melchor_confidence": as_float(melchor_vote.get("confidence")),
        "melchor_risk_flags": clean_str(melchor_vote.get("risk_flag")),
        "baltasar_signal": baltasar_signal,
        "baltasar_confidence": as_float(baltasar_vote.get("confidence")),
        "gaspar_signal": gaspar_signal,
        "gaspar_confidence": as_float(gaspar_vote.get("confidence")),
        "mage_agreement": mage_agreement(melchor_signal, baltasar_signal, gaspar_signal),
        "baltasar_gaspar_alignment": baltasar_gaspar_alignment(
            baltasar_signal,
            gaspar_signal,
            clean_str(gaspar_context.get("proposed_direction")),
        ),
        "future_outcome_h12": future_direction(outcomes, "12"),
        "future_outcome_h48": future_direction(outcomes, "48"),
        "future_outcome_h96": future_direction(outcomes, "96"),
        "future_outcome_h288": future_direction(outcomes, "288"),
    }
    row["ceo_label_h48"] = ceo_label_h48(row, outcomes)
    return row


def ceo_label_h48(row: dict[str, Any], outcomes: dict[str, Any]) -> str:
    outcome = as_dict(outcomes.get("48"))
    direction = clean_str(outcome.get("real_direction"))
    future_return_pips = as_float(outcome.get("future_return_pips"))
    baltasar_signal = row.get("baltasar_signal")
    if future_return_pips is None:
        return "DO_NOTHING"
    if baltasar_signal == "BUY" and direction == "BUY" and future_return_pips >= CLEAR_EDGE_PIPS:
        return "ENTER_BUY"
    if baltasar_signal == "SELL" and direction == "SELL" and future_return_pips <= -CLEAR_EDGE_PIPS:
        return "ENTER_SELL"
    return "DO_NOTHING"


def future_direction(outcomes: dict[str, Any], horizon: str) -> str | None:
    outcome = as_dict(outcomes.get(horizon))
    return clean_str(outcome.get("real_direction"))


def mage_agreement(melchor_signal: str, baltasar_signal: str, gaspar_signal: str) -> str:
    if melchor_signal == "BLOCK":
        return "BLOCKED_BY_MELCHOR"
    if baltasar_signal == "NEUTRAL":
        return "NO_DIRECTION"
    if melchor_signal == "APPROVE" and baltasar_signal in {"BUY", "SELL"} and gaspar_signal in {"GOOD", "FAIR"}:
        return "ACTIONABLE_CONSENSUS"
    if gaspar_signal == "POOR" and baltasar_signal in {"BUY", "SELL"}:
        return "DIRECTION_WITH_POOR_QUALITY"
    return "MIXED"


def baltasar_gaspar_alignment(baltasar_signal: str, gaspar_signal: str, gaspar_proposed_direction: str | None) -> str:
    if baltasar_signal not in {"BUY", "SELL"}:
        return "BALTASAR_NEUTRAL"
    if gaspar_signal == "POOR":
        return "DIRECTION_REJECTED_BY_GASPAR"
    if gaspar_proposed_direction in {"BUY", "SELL"}:
        return "DIRECTION_MATCH" if gaspar_proposed_direction == baltasar_signal else "DIRECTION_MISMATCH"
    if gaspar_signal in {"GOOD", "FAIR"}:
        return "QUALITY_SUPPORTS_DIRECTION"
    return "UNKNOWN"


def regime_label(session: Any, htf: dict[str, Any], atr: float | None, daily_range_position: float | None) -> str:
    parts = [
        clean_str(session) or "unknown_session",
        f"h4_{clean_str(htf.get('h4_structure')) or 'unknown'}",
        f"d1_{clean_str(htf.get('d1_structure')) or 'unknown'}",
        f"align_{clean_str(htf.get('directional_alignment')) or 'unknown'}",
        f"atr_{bucket(atr, [(0.5, 'low'), (0.85, 'normal'), (1.2, 'extended'), (1.5, 'high')], 'extreme')}",
        f"d1pos_{bucket(daily_range_position, [(0.25, 'low'), (0.5, 'mid_low'), (0.75, 'mid_high'), (1.0, 'high')], 'outside')}",
    ]
    return "|".join(parts).lower()


def build_summary(rows: list[dict[str, Any]], summary_stats: dict[str, Any]) -> dict[str, Any]:
    timestamps = [parse_timestamp(row.get("timestamp")) for row in rows if row.get("timestamp")]
    timestamps = [item for item in timestamps if item is not None]
    null_counts = {
        column: sum(1 for row in rows if is_null(row.get(column)))
        for column in FINAL_COLUMNS
    }
    return {
        "schema_version": "ceo_final_dataset_summary_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows": len(rows),
        "columns": len(FINAL_COLUMNS),
        "temporal_range": {
            "start": min(timestamps).isoformat().replace("+00:00", "Z") if timestamps else None,
            "end": max(timestamps).isoformat().replace("+00:00", "Z") if timestamps else None,
        },
        "label_distribution": dict(Counter(row.get("ceo_label_h48") for row in rows)),
        "year_distribution": dict(sorted(Counter(str(parse_timestamp(row.get("timestamp")).year) for row in rows if parse_timestamp(row.get("timestamp"))).items())),
        "session_distribution": dict(sorted(Counter(row.get("session") or "UNKNOWN" for row in rows).items())),
        "null_counts": null_counts,
        "columns_final": FINAL_COLUMNS,
        "parse_errors": summary_stats.get("parse_errors", 0),
        "label_rule": {
            "primary_horizon": "48",
            "clear_edge_pips": CLEAR_EDGE_PIPS,
            "enter_buy": "baltasar_signal == BUY and H48 real_direction == BUY and future_return_pips >= 3.0",
            "enter_sell": "baltasar_signal == SELL and H48 real_direction == SELL and future_return_pips <= -3.0",
            "else": "DO_NOTHING",
        },
        "technical_decisions": [
            "atr uses gaspar_context.timing_quality.daily_atr_consumed_pct; falls back to day_context.current_d1_range_vs_atr when needed.",
            "daily_range_position uses gaspar_context.price_structure_position.position_in_d1_range.",
            "regime is a compact categorical string built from session, H4/D1 structure, directional alignment, ATR bucket and D1 range-position bucket.",
            "future_outcome_h* columns store future_outcomes[horizon].real_direction.",
            "features_at_decision_time.features is empty in the inspected CEO JSONL, so final columns are sourced from normalized votes and gaspar_context.",
        ],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINAL_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required to write Parquet output") from exc

    dataframe = pd.DataFrame(rows, columns=FINAL_COLUMNS)
    try:
        dataframe.to_parquet(path, index=False)
    except ImportError as exc:
        raise RuntimeError("Parquet output requires pyarrow or fastparquet. Install one of them and rerun.") from exc


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip()


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def day_name(timestamp: datetime | None, fallback: Any) -> str | None:
    value = clean_str(fallback)
    if value:
        return value.lower()
    if timestamp is None:
        return None
    return timestamp.strftime("%A").lower()


def bucket(value: float | None, thresholds: list[tuple[float, str]], above_label: str) -> str:
    if value is None:
        return "unknown"
    for limit, label in thresholds:
        if value <= limit:
            return label
    return above_label


def is_null(value: Any) -> bool:
    return value is None or value == ""


if __name__ == "__main__":
    raise SystemExit(main())
