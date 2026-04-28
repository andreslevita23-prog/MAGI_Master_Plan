from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


MAX_AGE_MINUTES = {
    "M15": 15.0,
    "H1": 60.0,
    "H4": 240.0,
    "D1": 1440.0,
}

CRITICAL_CSV_COLUMNS = [
    "snapshot_id",
    "symbol",
    "timestamp",
    "anchor_bar_timestamp",
    "bar_timestamp",
    "anchor_open",
    "anchor_high",
    "anchor_low",
    "anchor_close",
    "current_price",
    "spread_pips",
    "rsi_14",
    "mtf_data_source_status",
    "validation_is_valid",
    "features_json",
    "gaspar_h4_bar_timestamp",
    "gaspar_d1_bar_timestamp",
    "gaspar_h4_age_minutes",
    "gaspar_d1_age_minutes",
]

FORBIDDEN_GASPAR_KEYS = {
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "momentum",
    "confidence",
    "probability",
    "baltasar_confidence",
    "baltasar_probability",
    "baltasar_score",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Bot_A_sub3 operational datasets.")
    parser.add_argument("--data-path", required=True, help="Run folder or dataset root containing CSV/JSONL files.")
    parser.add_argument("--output-dir", default="reports/bot_a_sub3_audits", help="Directory for audit reports.")
    return parser.parse_args()


def discover_files(root: Path) -> tuple[list[Path], list[Path]]:
    if root.is_file():
        return ([root] if root.suffix.lower() == ".csv" else []), ([root] if root.suffix.lower() == ".jsonl" else [])
    return sorted(root.rglob("*.csv")), sorted(root.rglob("*.jsonl"))


def walk_keys(value: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            full = f"{prefix}.{key}" if prefix else key
            keys.append(full)
            keys.extend(walk_keys(nested, full))
    elif isinstance(value, list):
        for nested in value:
            keys.extend(walk_keys(nested, prefix))
    return keys


def load_jsonl(files: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for path in files:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception as exc:  # noqa: BLE001
                    errors.append({"file": str(path), "line": line_number, "error": str(exc)})
    return records, errors


def load_csv(files: list[Path]) -> tuple[pd.DataFrame, list[dict[str, Any]], Counter]:
    frames: list[pd.DataFrame] = []
    errors: list[dict[str, Any]] = []
    headers: Counter = Counter()
    for path in files:
        try:
            frame = pd.read_csv(path)
            headers[tuple(frame.columns)] += 1
            frame["source_file"] = str(path)
            frames.append(frame)
        except Exception as exc:  # noqa: BLE001
            errors.append({"file": str(path), "error": str(exc)})
    if not frames:
        return pd.DataFrame(), errors, headers
    return pd.concat(frames, ignore_index=True), errors, headers


def parse_features_json(value: Any) -> list[dict[str, Any]] | None:
    if pd.isna(value):
        return None
    try:
        parsed = json.loads(str(value))
    except Exception:
        return None
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and isinstance(parsed.get("features"), list):
        return parsed["features"]
    return None


def audit_temporal_alignment_from_csv(df: pd.DataFrame) -> dict[str, Any]:
    failures = Counter()
    counts = Counter()
    data_source_statuses = Counter()
    bad_features_json = 0
    max_seen: dict[str, float] = {}

    if "features_json" not in df.columns:
        return {"bad_features_json": len(df), "counts": {}, "failures": {}, "data_source_statuses": {}, "max_age_seen": {}}

    for raw in df["features_json"]:
        features = parse_features_json(raw)
        if features is None:
            bad_features_json += 1
            continue
        for feature in features:
            timeframe = str(feature.get("timeframe", ""))
            if timeframe not in MAX_AGE_MINUTES:
                continue
            counts[timeframe] += 1
            data_source_status = str(feature.get("data_source_status", "MISSING")).upper()
            data_source_statuses[data_source_status] += 1
            if data_source_status != "OK":
                failures[timeframe] += 1
                continue
            age = pd.to_numeric(feature.get("age_minutes"), errors="coerce")
            if pd.isna(age):
                failures[timeframe] += 1
                continue
            age_float = float(age)
            max_seen[timeframe] = max(max_seen.get(timeframe, age_float), age_float)
            if age_float < -0.01 or age_float > MAX_AGE_MINUTES[timeframe] + 0.01:
                failures[timeframe] += 1

    return {
        "bad_features_json": bad_features_json,
        "counts": dict(counts),
        "failures": dict(failures),
        "data_source_statuses": dict(data_source_statuses),
        "max_age_seen": max_seen,
    }


def audit_gaspar_forbidden(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations = []
    for record in records:
        gaspar = record.get("gaspar_context") or {}
        bad = []
        for key in walk_keys(gaspar):
            leaf = key.split(".")[-1].lower()
            if leaf in FORBIDDEN_GASPAR_KEYS or "probability" in leaf or "confidence" in leaf or "baltasar" in leaf:
                bad.append(key)
        if bad:
            violations.append({"snapshot_id": record.get("snapshot_id"), "keys": bad[:10]})
    return violations


def build_report(data_path: Path, csv_files: list[Path], jsonl_files: list[Path], df: pd.DataFrame, csv_errors: list[dict[str, Any]], json_records: list[dict[str, Any]], json_errors: list[dict[str, Any]], headers: Counter) -> dict[str, Any]:
    duplicate_csv = int(df["snapshot_id"].duplicated().sum()) if "snapshot_id" in df else None
    duplicate_json = None
    if json_records:
        ids = [record.get("snapshot_id") for record in json_records]
        duplicate_json = len(ids) - len(set(ids))

    missing_columns = [column for column in CRITICAL_CSV_COLUMNS if column not in df.columns]
    critical_nulls = {
        column: int(df[column].isna().sum())
        for column in CRITICAL_CSV_COLUMNS
        if column in df.columns
    }

    for column in ["timestamp", "anchor_bar_timestamp", "bar_timestamp", "gaspar_h4_bar_timestamp", "gaspar_d1_bar_timestamp"]:
        if column in df.columns:
            df[f"{column}_dt"] = pd.to_datetime(df[column], errors="coerce", utc=True)

    numeric_columns = ["anchor_open", "anchor_high", "anchor_low", "anchor_close", "current_price", "spread_pips", "rsi_14", "gaspar_h4_age_minutes", "gaspar_d1_age_minutes"]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    ohlc_bad = 0
    if {"anchor_open", "anchor_high", "anchor_low", "anchor_close"}.issubset(df.columns):
        ohlc_bad = int(((df.anchor_high < df.anchor_low) | (df.anchor_open > df.anchor_high) | (df.anchor_open < df.anchor_low) | (df.anchor_close > df.anchor_high) | (df.anchor_close < df.anchor_low)).sum())

    spread_negative = int((df["spread_pips"] < 0).sum()) if "spread_pips" in df.columns else None
    rsi_bad = int(((df["rsi_14"] < 0) | (df["rsi_14"] > 100)).sum()) if "rsi_14" in df.columns else None

    mtf = audit_temporal_alignment_from_csv(df)
    gaspar_violations = audit_gaspar_forbidden(json_records)

    gaspar_age_failures = {}
    if "gaspar_h4_age_minutes" in df.columns:
        gaspar_age_failures["H4"] = int(((df["gaspar_h4_age_minutes"] < -0.01) | (df["gaspar_h4_age_minutes"] > 240.01)).sum())
    if "gaspar_d1_age_minutes" in df.columns:
        gaspar_age_failures["D1"] = int(((df["gaspar_d1_age_minutes"] < -0.01) | (df["gaspar_d1_age_minutes"] > 1440.01)).sum())

    penalties = 0
    penalties += min(30, len(json_errors) * 5 + len(csv_errors) * 5)
    penalties += 20 if duplicate_csv or duplicate_json else 0
    penalties += min(20, ohlc_bad)
    penalties += min(15, spread_negative or 0)
    penalties += min(15, rsi_bad or 0)
    penalties += 25 if mtf["bad_features_json"] else 0
    penalties += min(35, sum(mtf["failures"].values()) if mtf["failures"] else 0)
    penalties += min(20, sum(gaspar_age_failures.values()) if gaspar_age_failures else 0)
    penalties += 20 if gaspar_violations else 0
    score = max(0, 100 - penalties)

    decision = "APTO"
    if score < 75 or mtf["bad_features_json"] or any(mtf["failures"].values()) or any(gaspar_age_failures.values()):
        decision = "NO APTO"
    elif score < 90:
        decision = "APTO CON AJUSTES"

    return {
        "data_path": str(data_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {"csv": len(csv_files), "jsonl": len(jsonl_files)},
        "rows": {"csv": int(len(df)), "jsonl": len(json_records)},
        "parse_errors": {"csv": csv_errors[:10], "jsonl": json_errors[:10]},
        "schema": {
            "csv_header_variants": len(headers),
            "missing_columns": missing_columns,
            "critical_nulls": critical_nulls,
        },
        "integrity": {
            "duplicate_snapshot_id_csv": duplicate_csv,
            "duplicate_snapshot_id_json": duplicate_json,
        },
        "logic": {
            "ohlc_bad": ohlc_bad,
            "spread_negative": spread_negative,
            "rsi_out_of_range": rsi_bad,
            "gaspar_forbidden_violations": gaspar_violations[:10],
        },
        "temporal_alignment": {
            "features": mtf,
            "gaspar_age_failures": gaspar_age_failures,
        },
        "score": score,
        "decision": decision,
    }


def write_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"{stamp}_bot_a_sub3_audit.json"
    md_path = output_dir / f"{stamp}_bot_a_sub3_audit.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Bot_A_sub3 Dataset Audit",
        "",
        f"- Decision: `{report['decision']}`",
        f"- Score: `{report['score']}`",
        f"- CSV rows: `{report['rows']['csv']}`",
        f"- JSONL rows: `{report['rows']['jsonl']}`",
        f"- CSV parse errors: `{len(report['parse_errors']['csv'])}`",
        f"- JSONL parse errors: `{len(report['parse_errors']['jsonl'])}`",
        f"- Duplicate CSV snapshot_id: `{report['integrity']['duplicate_snapshot_id_csv']}`",
        f"- Duplicate JSON snapshot_id: `{report['integrity']['duplicate_snapshot_id_json']}`",
        f"- OHLC bad rows: `{report['logic']['ohlc_bad']}`",
        f"- Negative spreads: `{report['logic']['spread_negative']}`",
        f"- RSI out of range: `{report['logic']['rsi_out_of_range']}`",
        "",
        "## Temporal Alignment",
        "",
        f"- Bad `features_json`: `{report['temporal_alignment']['features']['bad_features_json']}`",
        f"- Feature counts: `{report['temporal_alignment']['features']['counts']}`",
        f"- Feature failures: `{report['temporal_alignment']['features']['failures']}`",
        f"- Feature data source statuses: `{report['temporal_alignment']['features']['data_source_statuses']}`",
        f"- Max age seen: `{report['temporal_alignment']['features']['max_age_seen']}`",
        f"- Gaspar age failures: `{report['temporal_alignment']['gaspar_age_failures']}`",
    ]
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    args = parse_args()
    data_path = Path(args.data_path)
    csv_files, jsonl_files = discover_files(data_path)
    json_records, json_errors = load_jsonl(jsonl_files)
    df, csv_errors, headers = load_csv(csv_files)
    report = build_report(data_path, csv_files, jsonl_files, df, csv_errors, json_records, json_errors, headers)
    json_path, md_path = write_reports(report, Path(args.output_dir))
    print(f"decision={report['decision']} score={report['score']} json_report={json_path} markdown_report={md_path}")


if __name__ == "__main__":
    main()
