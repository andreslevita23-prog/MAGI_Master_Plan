from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from simulator.schemas import Snapshot, as_bool, as_float, parse_timestamp


class LoaderError(ValueError):
    pass


def load_bot_a_snapshots(input_path: str | Path, input_format: str = "auto") -> tuple[list[Snapshot], list[dict[str, Any]]]:
    root = Path(input_path)
    if not root.exists():
        raise LoaderError(f"Input path does not exist: {root}")

    formats = {input_format.lower()}
    if "auto" in formats:
        paths = sorted([*root.rglob("*.jsonl"), *root.rglob("*.csv")])
    elif "jsonl" in formats:
        paths = sorted(root.rglob("*.jsonl"))
    elif "csv" in formats:
        paths = sorted(root.rglob("*.csv"))
    else:
        raise LoaderError(f"Unsupported input_format: {input_format}")

    snapshots: list[Snapshot] = []
    parse_errors: list[dict[str, Any]] = []
    for path in paths:
        if path.suffix.lower() == ".jsonl":
            loaded, errors = load_jsonl(path)
        elif path.suffix.lower() == ".csv":
            loaded, errors = load_csv(path)
        else:
            continue
        snapshots.extend(loaded)
        parse_errors.extend(errors)
    return snapshots, parse_errors


def load_jsonl(path: str | Path) -> tuple[list[Snapshot], list[dict[str, Any]]]:
    file_path = Path(path)
    snapshots: list[Snapshot] = []
    errors: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
                snapshots.append(snapshot_from_record(record, str(file_path), line_number))
            except Exception as exc:
                errors.append({"file": str(file_path), "line": line_number, "error": str(exc)})
    return snapshots, errors


def load_csv(path: str | Path) -> tuple[list[Snapshot], list[dict[str, Any]]]:
    file_path = Path(path)
    snapshots: list[Snapshot] = []
    errors: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for line_number, row in enumerate(reader, 2):
            try:
                snapshots.append(snapshot_from_record(_expand_csv_row(row), str(file_path), line_number))
            except Exception as exc:
                errors.append({"file": str(file_path), "line": line_number, "error": str(exc)})
    return snapshots, errors


def snapshot_from_record(record: dict[str, Any], source_file: str | None = None, source_line: int | None = None) -> Snapshot:
    timestamp = parse_timestamp(record.get("timestamp"))
    anchor_timestamp = parse_timestamp(record.get("anchor_bar_timestamp") or record.get("bar_timestamp"))
    if timestamp is None:
        raise LoaderError("Missing or invalid timestamp")
    if anchor_timestamp is None:
        raise LoaderError("Missing or invalid anchor_bar_timestamp")

    return Snapshot(
        schema_version=str(record.get("schema_version") or "bot_a_snapshot_v1"),
        snapshot_id=str(record.get("snapshot_id") or ""),
        run_id=_optional_str(record.get("run_id")),
        symbol=str(record.get("symbol") or ""),
        timestamp=timestamp,
        anchor_bar_timestamp=anchor_timestamp,
        timeframe=_optional_str(record.get("timeframe") or record.get("anchor_timeframe")),
        open=as_float(record.get("open", record.get("anchor_open"))),
        high=as_float(record.get("high", record.get("anchor_high"))),
        low=as_float(record.get("low", record.get("anchor_low"))),
        close=as_float(record.get("close", record.get("anchor_close"))),
        current_price=as_float(record.get("current_price")),
        spread_pips=as_float(record.get("spread_pips")),
        active_session=_optional_str(record.get("active_session") or _nested(record, "gaspar_context", "timing_quality", "active_session")),
        features=_dict_or_empty(record.get("features")),
        gaspar_context=_build_gaspar_context(record),
        account=_dict_or_empty(record.get("account")),
        validation=_build_validation(record),
        raw=record,
        source_file=source_file,
        source_line=source_line,
    )


def _expand_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    record = dict(row)
    if record.get("features_json"):
        record["features"] = json.loads(record["features_json"])
    if not record.get("gaspar_context"):
        record["gaspar_context"] = {
            "is_available": as_bool(record.get("gaspar_is_available"), default=False),
            "proposed_direction": record.get("gaspar_proposed_direction"),
            "higher_timeframe_confluence": {
                "h4_structure": record.get("gaspar_h4_structure"),
                "d1_structure": record.get("gaspar_d1_structure"),
                "directional_alignment": record.get("gaspar_directional_alignment"),
            },
            "price_structure_position": {
                "distance_to_d1_support": as_float(record.get("gaspar_distance_to_d1_support")),
                "distance_to_d1_resistance": as_float(record.get("gaspar_distance_to_d1_resistance")),
                "position_in_d1_range": as_float(record.get("gaspar_position_in_d1_range")),
                "near_key_level": as_bool(record.get("gaspar_near_key_level"), default=False),
            },
            "timing_quality": {
                "active_session": record.get("gaspar_active_session") or record.get("active_session"),
                "daily_atr_consumed_pct": as_float(record.get("gaspar_daily_atr_consumed_pct")),
                "available_range_to_next_level": as_float(record.get("gaspar_available_range_to_next_level")),
                "h4_candle_pattern": record.get("gaspar_h4_candle_pattern"),
            },
            "day_context": {
                "day_of_week": record.get("gaspar_day_of_week"),
                "d1_volatility_vs_20d_avg": as_float(record.get("gaspar_d1_volatility_vs_20d_avg")),
                "current_d1_range_vs_atr": as_float(record.get("gaspar_current_d1_range_vs_atr")),
            },
        }
    return record


def _build_validation(record: dict[str, Any]) -> dict[str, Any]:
    validation = _dict_or_empty(record.get("validation"))
    if "is_valid" not in validation and "validation_is_valid" in record:
        validation["is_valid"] = as_bool(record.get("validation_is_valid"), default=False)
    validation.setdefault("issues", [])
    return validation


def _build_gaspar_context(record: dict[str, Any]) -> dict[str, Any]:
    context = _dict_or_empty(record.get("gaspar_context"))
    if context:
        return context
    return {}


def _dict_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _nested(record: dict[str, Any], *keys: str) -> Any:
    current: Any = record
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
