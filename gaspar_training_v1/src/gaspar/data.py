from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd


def discover_dataset_files(path: str | Path) -> list[Path]:
    root = Path(path)
    if root.is_file():
        return [root]
    if not root.exists():
        raise FileNotFoundError(f"Dataset path not found: {root}")
    files = [*root.rglob("*.csv"), *root.rglob("*.jsonl")]
    return sorted(files)


def _flatten_record(record: dict) -> dict:
    flat: dict[str, object] = {}

    def walk(prefix: str, value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                next_prefix = f"{prefix}.{key}" if prefix else key
                walk(next_prefix, nested)
        else:
            flat[prefix] = value

    walk("", record)
    return flat


def _read_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(_flatten_record(json.loads(line)))
    return pd.DataFrame(rows)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_dataset(path: str | Path) -> pd.DataFrame:
    frames = []
    for file_path in discover_dataset_files(path):
        if file_path.suffix.lower() == ".csv":
            frame = _read_csv(file_path)
        elif file_path.suffix.lower() == ".jsonl":
            frame = _read_jsonl(file_path)
        else:
            continue
        frame["source_file"] = str(file_path)
        frames.append(frame)

    if not frames:
        raise ValueError(f"No CSV or JSONL files found under {path}")

    data = normalize_columns(pd.concat(frames, ignore_index=True, sort=False))
    return drop_exact_dataset_duplicates(data)


def normalize_columns(data: pd.DataFrame) -> pd.DataFrame:
    normalized = data.copy()
    normalized.columns = [
        column.strip().replace(".", "_").replace(" ", "_").lower()
        for column in normalized.columns
    ]

    aliases = {
        "target_voto": "voto",
        "target_score_oportunidad": "score_oportunidad",
        "baltasar_direction": "proposed_direction",
        "alignment_with_baltasar": "directional_alignment",
        "higher_timeframe_confluence_h4_structure": "h4_structure",
        "higher_timeframe_confluence_d1_structure": "d1_structure",
        "higher_timeframe_confluence_alignment_with_baltasar": "directional_alignment",
        "higher_timeframe_confluence_alignment_with_proposed_direction": "directional_alignment",
        "higher_timeframe_confluence_directional_alignment": "directional_alignment",
        "price_structure_position_distance_to_d1_support": "distance_to_d1_support",
        "price_structure_position_distance_to_d1_resistance": "distance_to_d1_resistance",
        "price_structure_position_position_in_d1_range": "position_in_d1_range",
        "price_structure_position_near_key_level": "near_key_level",
        "timing_quality_active_session": "active_session",
        "timing_quality_daily_atr_consumed_pct": "daily_atr_consumed_pct",
        "timing_quality_available_range_to_next_level": "available_range_to_next_level",
        "timing_quality_h4_candle_pattern": "h4_candle_pattern",
        "day_context_day_of_week": "day_of_week",
        "day_context_d1_volatility_vs_20d_avg": "d1_volatility_vs_20d_avg",
        "day_context_current_d1_range_vs_atr": "current_d1_range_vs_atr",
    }
    normalized = normalized.rename(columns={k: v for k, v in aliases.items() if k in normalized.columns})
    normalized = coalesce_duplicate_columns(normalized)
    normalized = attach_proxy_direction_columns(normalized)
    return normalized


def attach_proxy_direction_columns(data: pd.DataFrame) -> pd.DataFrame:
    prepared = data.copy()
    if "proposed_direction" not in prepared.columns:
        prepared["proposed_direction"] = prepared.apply(proxy_direction_from_structure, axis=1)
    else:
        proposed = prepared["proposed_direction"].astype("string").str.upper()
        proposed = proposed.replace({"HOLD": pd.NA, "": pd.NA, "UNKNOWN": pd.NA})
        missing = proposed.isna()
        if missing.any():
            proposed.loc[missing] = prepared.loc[missing].apply(proxy_direction_from_structure, axis=1)
        prepared["proposed_direction"] = proposed

    prepared["directional_alignment"] = prepared.apply(directional_alignment_from_structure, axis=1)
    return prepared


def proxy_direction_from_structure(row: pd.Series) -> str:
    h4 = str(row.get("h4_structure", "")).strip().lower()
    d1 = str(row.get("d1_structure", "")).strip().lower()
    if d1 == "bullish" and h4 != "bearish":
        return "BUY"
    if d1 == "bearish" and h4 != "bullish":
        return "SELL"
    return "NEUTRAL"


def directional_alignment_from_structure(row: pd.Series) -> str:
    proposed = str(row.get("proposed_direction", "")).strip().upper()
    h4 = str(row.get("h4_structure", "")).strip().lower()
    d1 = str(row.get("d1_structure", "")).strip().lower()
    if proposed == "BUY" and d1 == "bullish" and h4 != "bearish":
        return "aligned"
    if proposed == "SELL" and d1 == "bearish" and h4 != "bullish":
        return "aligned"
    if proposed == "NEUTRAL":
        return "neutral"
    return "contradictory"


def coalesce_duplicate_columns(data: pd.DataFrame) -> pd.DataFrame:
    if not data.columns.has_duplicates:
        return data

    coalesced = pd.DataFrame(index=data.index)
    for column in dict.fromkeys(data.columns):
        values = data.loc[:, data.columns == column]
        if values.shape[1] == 1:
            coalesced[column] = values.iloc[:, 0]
        else:
            coalesced[column] = values.bfill(axis=1).iloc[:, 0]
    return coalesced


def drop_exact_dataset_duplicates(data: pd.DataFrame) -> pd.DataFrame:
    compare_columns = [column for column in data.columns if column != "source_file"]
    if not compare_columns:
        return data
    return data.drop_duplicates(subset=compare_columns, keep="first").reset_index(drop=True)


def ensure_columns(data: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    prepared = data.copy()
    for column in columns:
        if column not in prepared.columns:
            prepared[column] = pd.NA
    return prepared
