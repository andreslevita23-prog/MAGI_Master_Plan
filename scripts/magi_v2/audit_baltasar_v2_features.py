from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_JSONL = Path("data/clean/bot_a_sub3_full/cleaned_dataset.jsonl")
DEFAULT_LABELS = Path("data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_v2_feature_audit")

UNIQUE_CAP = 2000
RECOMMENDED_FEATURES = [
    "trend_h1",
    "trend_h4",
    "trend_d1",
    "ema_fast_m5",
    "ema_slow_m5",
    "ema_distance",
    "ema_slope",
    "rsi_m5",
    "rsi_h1",
    "atr_m5",
    "atr_h1",
    "momentum_m5",
    "momentum_h1",
    "candle_body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "distance_to_recent_high",
    "distance_to_recent_low",
    "support_distance_pips",
    "resistance_distance_pips",
    "structure_h1",
    "structure_h4",
    "mtf_trend_alignment",
]


def main() -> int:
    args = parse_args()
    setup_logging()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Auditing JSONL: %s", args.jsonl)
    audit = audit_jsonl(Path(args.jsonl))
    labels_audit = audit_labels(Path(args.labels))
    candidates, missing = classify_candidate_features(audit)

    write_csv(output_dir / "available_columns.csv", audit["columns"])
    write_csv(output_dir / "candidate_features.csv", candidates)
    write_csv(output_dir / "missing_recommended_features.csv", missing)

    summary = {
        "schema_version": "baltasar_v2_feature_audit_v0.1",
        "generated_at": utc_now(),
        "source_jsonl": str(args.jsonl),
        "labels_dataset": str(args.labels),
        "records": audit["records"],
        "temporal_range": audit["temporal_range"],
        "top_level_columns": audit["top_level_columns"],
        "available_columns_count": len(audit["columns"]),
        "labels_audit": labels_audit,
        "candidate_feature_count": len(candidates),
        "missing_recommended_count": len(missing),
        "candidate_features": candidates,
        "missing_recommended_features": missing,
        "technical_decisions": [
            "Nested feature dictionaries are expanded by timeframe, e.g. features.H1.ema_20.",
            "Numeric lists such as support_levels/resistance_levels are summarized as count/min/max/first/last paths.",
            "Null percentage is computed as records where the path is missing or null over total JSONL records.",
            "Candidate status values: ready, derivable, needs_bot_a_export.",
        ],
    }
    (output_dir / "baltasar_v2_feature_audit.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "baltasar_v2_feature_audit_summary.md").write_text(markdown_summary(summary), encoding="utf-8")
    logging.info("Outputs written: %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Bot A technical features for Baltasar v2.")
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="Clean Bot A sub3 JSONL.")
    parser.add_argument("--labels", default=str(DEFAULT_LABELS), help="RR2 first-touch labels parquet.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ColumnStats:
    def __init__(self, path: str) -> None:
        self.path = path
        self.present = 0
        self.null = 0
        self.types: Counter[str] = Counter()
        self.unique: set[str] = set()
        self.unique_overflow = False
        self.numeric_count = 0
        self.numeric_min: float | None = None
        self.numeric_max: float | None = None
        self.examples: list[str] = []

    def add(self, value: Any) -> None:
        self.present += 1
        if value is None or value == "":
            self.null += 1
            self.types["null"] += 1
            return
        type_name = type(value).__name__
        self.types[type_name] += 1
        if len(self.examples) < 3:
            self.examples.append(short_value(value))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            number = float(value)
            self.numeric_count += 1
            self.numeric_min = number if self.numeric_min is None else min(self.numeric_min, number)
            self.numeric_max = number if self.numeric_max is None else max(self.numeric_max, number)
        if not self.unique_overflow:
            self.unique.add(short_value(value, 120))
            if len(self.unique) > UNIQUE_CAP:
                self.unique.clear()
                self.unique_overflow = True

    def row(self, total_records: int) -> dict[str, Any]:
        missing = total_records - self.present
        null_total = missing + self.null
        return {
            "path": self.path,
            "present_count": self.present,
            "missing_count": missing,
            "null_count": null_total,
            "null_pct": round(null_total / total_records, 6) if total_records else None,
            "types": ",".join(f"{key}:{value}" for key, value in sorted(self.types.items())),
            "cardinality": f">{UNIQUE_CAP}" if self.unique_overflow else len(self.unique),
            "numeric_min": self.numeric_min,
            "numeric_max": self.numeric_max,
            "examples": " | ".join(self.examples),
        }


def audit_jsonl(path: Path) -> dict[str, Any]:
    stats: dict[str, ColumnStats] = {}
    top_level = Counter()
    records = 0
    first_ts: str | None = None
    last_ts: str | None = None
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            record = json.loads(line)
            records += 1
            top_level.update(record.keys())
            ts = str(record.get("anchor_bar_timestamp") or record.get("timestamp") or "")
            if ts:
                first_ts = ts if first_ts is None else min(first_ts, ts)
                last_ts = ts if last_ts is None else max(last_ts, ts)
            flat = flatten_record(record)
            for key, value in flat.items():
                if key not in stats:
                    stats[key] = ColumnStats(key)
                stats[key].add(value)
            if records % 100000 == 0:
                logging.info("Audited %s records", records)
    columns = [stats[key].row(records) for key in sorted(stats)]
    return {
        "records": records,
        "temporal_range": {"start": first_ts, "end": last_ts},
        "top_level_columns": dict(sorted(top_level.items())),
        "columns": columns,
        "path_set": set(stats.keys()),
    }


def flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in record.items():
        if key == "features" and isinstance(value, list):
            flatten_timeframe_features(value, flat)
        elif isinstance(value, dict):
            flatten_dict(key, value, flat)
        elif isinstance(value, list):
            flatten_list(key, value, flat)
        else:
            flat[key] = value
    return flat


def flatten_timeframe_features(features: list[Any], flat: dict[str, Any]) -> None:
    flat["features.count"] = len(features)
    for item in features:
        if not isinstance(item, dict):
            continue
        timeframe = str(item.get("timeframe") or "UNKNOWN").upper()
        for key, value in item.items():
            if key == "timeframe":
                continue
            path = f"features.{timeframe}.{key}"
            if isinstance(value, dict):
                flatten_dict(path, value, flat)
            elif isinstance(value, list):
                flatten_list(path, value, flat)
            else:
                flat[path] = value


def flatten_dict(prefix: str, data: dict[str, Any], flat: dict[str, Any]) -> None:
    for key, value in data.items():
        path = f"{prefix}.{key}"
        if isinstance(value, dict):
            flatten_dict(path, value, flat)
        elif isinstance(value, list):
            flatten_list(path, value, flat)
        else:
            flat[path] = value


def flatten_list(prefix: str, values: list[Any], flat: dict[str, Any]) -> None:
    flat[f"{prefix}.count"] = len(values)
    if not values:
        return
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        numeric = [float(value) for value in values]
        flat[f"{prefix}.first"] = values[0]
        flat[f"{prefix}.last"] = values[-1]
        flat[f"{prefix}.min"] = min(numeric)
        flat[f"{prefix}.max"] = max(numeric)
        return
    if all(isinstance(value, dict) for value in values):
        for idx, item in enumerate(values[:3]):
            flatten_dict(f"{prefix}.{idx}", item, flat)
        return
    flat[f"{prefix}.sample"] = short_value(values[0])


def audit_labels(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"available": False}
    df = pd.read_parquet(path, columns=["timestamp", "tradeable_direction_rr2_first_touch"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return {
        "available": True,
        "rows": int(len(df)),
        "temporal_range": {"start": df["timestamp"].min().isoformat(), "end": df["timestamp"].max().isoformat()},
        "target_distribution": df["tradeable_direction_rr2_first_touch"].value_counts().to_dict(),
    }


def classify_candidate_features(audit: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    paths = audit["path_set"]
    candidates = [
        cand("ohlc_m5", "ready", "anchor_open/high/low/close", "Top-level M5 OHLC exists.", ["anchor_open", "anchor_high", "anchor_low", "anchor_close"], paths),
        cand("ema_fast_m5", "ready", "ema_20", "Top-level EMA 20 exists.", ["ema_20"], paths),
        cand("ema_mid_m5", "ready", "ema_50", "Top-level EMA 50 exists.", ["ema_50"], paths),
        cand("ema_slow_m5", "ready", "ema_200", "Top-level EMA 200 exists.", ["ema_200"], paths),
        cand("rsi_m5", "ready", "rsi_14", "Top-level RSI exists.", ["rsi_14"], paths),
        cand("momentum_m5", "ready", "momentum", "Top-level categorical momentum exists.", ["momentum"], paths),
        cand("market_structure_m5", "ready", "market_structure + structure_direction", "Top-level structure fields exist.", ["market_structure", "structure_direction"], paths),
        cand("recent_range_m5", "ready", "recent_range", "Top-level recent range exists.", ["recent_range"], paths),
        cand("spread", "ready", "spread_pips", "Spread exists.", ["spread_pips"], paths),
        cand("support_resistance_distance_m5", "ready", "support_levels/resistance_levels", "Support/resistance levels exist as numeric lists.", ["support_levels.min", "support_levels.max", "resistance_levels.min", "resistance_levels.max"], paths),
        cand("mtf_ema_m15_h1_h4_d1", "ready", "features.*.ema_20/50/200", "MTF EMA values exist for M15/H1/H4/D1.", ["features.H1.ema_20", "features.H4.ema_50", "features.D1.ema_200"], paths),
        cand("mtf_rsi_m15_h1_h4_d1", "ready", "features.*.rsi_14", "MTF RSI exists for M15/H1/H4/D1.", ["features.H1.rsi_14", "features.H4.rsi_14", "features.D1.rsi_14"], paths),
        cand("mtf_structure_m15_h1_h4_d1", "ready", "features.*.market_structure/structure_direction", "MTF structure exists.", ["features.H1.market_structure", "features.H4.structure_direction", "features.D1.market_structure"], paths),
        cand("mtf_recent_range_m15_h1_h4_d1", "ready", "features.*.recent_range", "MTF recent range exists.", ["features.H1.recent_range", "features.H4.recent_range", "features.D1.recent_range"], paths),
        cand("mtf_alignment", "ready", "mtf_alignment_status + gaspar_context.higher_timeframe_confluence", "Alignment/context fields exist.", ["mtf_alignment_status", "gaspar_context.higher_timeframe_confluence.directional_alignment"], paths),
        cand("session_time", "ready", "active_session + timestamps", "Session and timestamp fields exist.", ["active_session", "anchor_bar_timestamp"], paths),
        cand("candle_body_wicks_m5", "derivable", "anchor OHLC", "Derive body and wick percentages from M5 OHLC.", ["anchor_open", "anchor_high", "anchor_low", "anchor_close"], paths),
        cand("ema_distance_m5", "derivable", "close + EMA", "Derive close-EMA and EMA spread distances.", ["anchor_close", "ema_20", "ema_50", "ema_200"], paths),
        cand("ema_slope_m5", "derivable", "EMA time series", "Derive lagged EMA deltas after sorting by symbol/time.", ["ema_20", "ema_50", "ema_200"], paths),
        cand("returns_m5", "derivable", "anchor_close time series", "Derive lagged returns from sorted M5 closes.", ["anchor_close"], paths),
        cand("atr_m5", "derivable", "anchor OHLC time series", "Derive true range/rolling ATR from M5 OHLC.", ["anchor_high", "anchor_low", "anchor_close"], paths),
        cand("distance_to_recent_high_low", "derivable", "anchor OHLC rolling windows", "Derive rolling high/low distances.", ["anchor_high", "anchor_low", "anchor_close"], paths),
        cand("trend_h1_h4_d1", "ready", "features.H1/H4/D1 structure_direction", "Use exported MTF structure_direction and market_structure.", ["features.H1.structure_direction", "features.H4.structure_direction", "features.D1.structure_direction"], paths),
        cand("momentum_h1", "derivable", "features.H1 EMA/RSI/structure", "No H1 momentum label, but can derive proxy from H1 EMA/RSI/structure.", ["features.H1.ema_20", "features.H1.ema_50", "features.H1.rsi_14"], paths),
        cand("atr_h1", "needs_bot_a_export", "H1 OHLC or ATR", "H1 ATR is not exported directly; recent_range is present but not ATR.", [], paths),
        cand("fractals", "needs_bot_a_export", "swing/fractal markers", "No explicit fractal/swing markers found.", [], paths),
    ]

    recommended_status = {
        "trend_h1": ("ready", "features.H1.structure_direction / features.H1.market_structure"),
        "trend_h4": ("ready", "features.H4.structure_direction / features.H4.market_structure"),
        "trend_d1": ("ready", "features.D1.structure_direction / features.D1.market_structure"),
        "ema_fast_m5": ("ready", "ema_20"),
        "ema_slow_m5": ("ready", "ema_200"),
        "ema_distance": ("derivable", "anchor_close, ema_20, ema_50, ema_200"),
        "ema_slope": ("derivable", "lagged EMA time series"),
        "rsi_m5": ("ready", "rsi_14"),
        "rsi_h1": ("ready", "features.H1.rsi_14"),
        "atr_m5": ("derivable", "M5 OHLC rolling true range"),
        "atr_h1": ("needs_bot_a_export", "H1 ATR or H1 OHLC bars"),
        "momentum_m5": ("ready", "momentum"),
        "momentum_h1": ("derivable", "H1 EMA/RSI/structure proxy; direct label missing"),
        "candle_body_pct": ("derivable", "M5 OHLC"),
        "upper_wick_pct": ("derivable", "M5 OHLC"),
        "lower_wick_pct": ("derivable", "M5 OHLC"),
        "distance_to_recent_high": ("derivable", "rolling M5 highs"),
        "distance_to_recent_low": ("derivable", "rolling M5 lows"),
        "support_distance_pips": ("ready", "support_levels"),
        "resistance_distance_pips": ("ready", "resistance_levels"),
        "structure_h1": ("ready", "features.H1.market_structure"),
        "structure_h4": ("ready", "features.H4.market_structure"),
        "mtf_trend_alignment": ("ready", "mtf_alignment_status / gaspar_context.higher_timeframe_confluence.directional_alignment"),
    }
    missing = [
        {
            "feature": feature,
            "status": recommended_status[feature][0],
            "available_source_or_gap": recommended_status[feature][1],
            "needs_bot_a_export": recommended_status[feature][0] == "needs_bot_a_export",
        }
        for feature in RECOMMENDED_FEATURES
    ]
    return candidates, missing


def cand(name: str, status: str, source: str, notes: str, paths_needed: list[str], available_paths: set[str]) -> dict[str, Any]:
    present = [path for path in paths_needed if path in available_paths]
    missing = [path for path in paths_needed if path not in available_paths]
    if status == "ready" and missing:
        effective = "partial"
    else:
        effective = status
    return {
        "feature_group": name,
        "status": effective,
        "source": source,
        "present_paths": ";".join(present),
        "missing_paths": ";".join(missing),
        "notes": notes,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def markdown_summary(summary: dict[str, Any]) -> str:
    ready = [row for row in summary["candidate_features"] if row["status"] == "ready"]
    derivable = [row for row in summary["candidate_features"] if row["status"] == "derivable"]
    needs_export = [row for row in summary["candidate_features"] if row["status"] == "needs_bot_a_export"]
    lines = [
        "# Baltasar v2 Feature Audit",
        "",
        "## Resultado ejecutivo",
        "",
        f"- Registros auditados: `{summary['records']}`",
        f"- Rango temporal: `{summary['temporal_range']['start']}` a `{summary['temporal_range']['end']}`",
        f"- Rutas/columnas reales detectadas: `{summary['available_columns_count']}`",
        f"- Candidate feature groups: `{summary['candidate_feature_count']}`",
        f"- Features listas: `{len(ready)}`",
        f"- Features derivables: `{len(derivable)}`",
        f"- Features que requieren export de Bot A: `{len(needs_export)}`",
        "",
        "El dataset limpio de Bot A contiene bastante mas senal tecnica que el dataset tabular usado por Baltasar v2 pure_directional. En particular, hay EMA/RSI/estructura/rango reciente por M15/H1/H4/D1 dentro de `features`, ademas de OHLC M5, soporte/resistencia, momentum y spread.",
        "",
        "## Top-level columns",
        "",
        ", ".join(summary["top_level_columns"].keys()),
        "",
        "## Candidate features listas",
        "",
        table(summary["candidate_features"], ["feature_group", "status", "source", "notes"]),
        "",
        "## Features recomendadas",
        "",
        table(summary["missing_recommended_features"], ["feature", "status", "available_source_or_gap", "needs_bot_a_export"]),
        "",
        "## Dataset de labels",
        "",
        f"- Disponible: `{summary['labels_audit']['available']}`",
        f"- Filas: `{summary['labels_audit'].get('rows')}`",
        f"- Target distribution: `{summary['labels_audit'].get('target_distribution')}`",
        "",
        "## Conclusion",
        "",
        "Si podemos entrenar un Baltasar v2 rich_features con lo disponible. La siguiente version debe expandir `cleaned_dataset.jsonl` a una tabla de features tecnicas M5+MTF y unirla con `rr2_first_touch_labels.parquet` por `symbol + anchor_bar_timestamp/timestamp`.",
        "",
        "La unica advertencia importante: H1 ATR directo, fractals/swing markers y momentum H1 explicito no estan exportados como campos directos; pueden derivarse parcialmente o pedirse a Bot A.",
    ]
    return "\n".join(lines) + "\n"


def table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def short_value(value: Any, limit: int = 80) -> str:
    text = str(value).replace("\n", " ")
    return text[:limit]


if __name__ == "__main__":
    raise SystemExit(main())
