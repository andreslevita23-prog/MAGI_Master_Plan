from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


FORBIDDEN_KEYWORDS = (
    "future",
    "outcome",
    "pnl",
    "mfe",
    "mae",
    "target",
    "label",
    "forward_return",
    "hit_tp",
    "hit_sl",
)
REQUIRED_FEATURE_TIMEFRAMES = {"M15", "H1", "H4", "D1"}
MAX_AGE_MINUTES = {"M15": 15.0, "H1": 60.0, "H4": 240.0, "D1": 1440.0}


def main() -> int:
    parser = argparse.ArgumentParser(description="Full streaming audit for long Bot A sub3 datasets.")
    parser.add_argument("--data-path", required=True, help="Bot A sub3 root or run directory.")
    parser.add_argument("--output-dir", default="reports/bot_a_sub3_audits", help="Audit output directory.")
    args = parser.parse_args()
    data_path = Path(args.data_path)
    output_dir = Path(args.output_dir)
    audit = audit_dataset(data_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "data_quality_full_audit.json"
    md_path = output_dir / "data_quality_full_audit.md"
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(markdown_report(audit), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "decision": audit["decision"]}, indent=2))
    return 0


def audit_dataset(data_path: Path) -> dict[str, Any]:
    runs = discover_runs(data_path)
    jsonl_files = sorted(data_path.rglob("*.jsonl"))
    csv_files = sorted(data_path.rglob("*.csv"))
    seen_snapshot_ids: set[str] = set()
    seen_symbol_anchor: set[tuple[str, datetime]] = set()
    duplicate_snapshot_ids = 0
    duplicate_symbol_anchor = 0
    parse_errors: list[dict[str, Any]] = []
    out_of_order_files: list[dict[str, Any]] = []
    timezone_naive_fields = Counter()
    forbidden_paths = Counter()
    forbidden_non_null_paths = Counter()
    symbols = Counter()
    timeframes = Counter()
    sessions = Counter()
    yearly = Counter()
    monthly = Counter()
    source_runs = Counter()
    validation_valid = 0
    source_invalid = 0
    ohlc_invalid = 0
    spread_negative = 0
    spread_extreme = 0
    missing_features = 0
    complete_features = 0
    feature_status_bad = 0
    missing_gaspar_context = 0
    gaspar_available = 0
    mtf_age_failures = Counter()
    mtf_close_leakage = Counter()
    gaspar_mtf_failures = Counter()
    trigger_not_closed_bar = 0
    anchor_not_m5 = 0
    total_unique = 0
    total_lines = 0
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    first_anchor: datetime | None = None
    last_anchor: datetime | None = None
    spread_values: list[float] = []
    range_pips_values: list[float] = []
    per_symbol_anchors: dict[str, list[datetime]] = defaultdict(list)
    file_empty = 0
    file_corrupt = 0

    for file_path in jsonl_files:
        last_in_file: datetime | None = None
        records_in_file = 0
        with file_path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, 1):
                text = line.strip()
                if not text:
                    continue
                total_lines += 1
                records_in_file += 1
                try:
                    record = json.loads(text)
                except Exception as exc:  # noqa: BLE001
                    parse_errors.append({"file": str(file_path), "line": line_number, "error": str(exc)})
                    continue

                snapshot_id = str(record.get("snapshot_id") or "")
                symbol = str(record.get("symbol") or "")
                timestamp = parse_timestamp(record.get("timestamp"))
                anchor = parse_timestamp(record.get("anchor_bar_timestamp") or record.get("bar_timestamp"))
                if is_naive_timestamp_text(record.get("timestamp")):
                    timezone_naive_fields["timestamp"] += 1
                if is_naive_timestamp_text(record.get("anchor_bar_timestamp")):
                    timezone_naive_fields["anchor_bar_timestamp"] += 1
                if is_naive_timestamp_text(record.get("bar_timestamp")):
                    timezone_naive_fields["bar_timestamp"] += 1
                if timestamp is None or anchor is None:
                    parse_errors.append({"file": str(file_path), "line": line_number, "error": "invalid timestamp"})
                    continue

                if snapshot_id in seen_snapshot_ids:
                    duplicate_snapshot_ids += 1
                    continue
                seen_snapshot_ids.add(snapshot_id)
                if (symbol, anchor) in seen_symbol_anchor:
                    duplicate_symbol_anchor += 1
                    continue
                seen_symbol_anchor.add((symbol, anchor))
                total_unique += 1

                run_name = run_for_path(file_path, runs)
                source_runs[run_name] += 1
                symbols[symbol] += 1
                timeframe = str(record.get("anchor_timeframe") or record.get("timeframe") or "")
                timeframes[timeframe] += 1
                if timeframe != "M5":
                    anchor_not_m5 += 1
                session = str(record.get("active_session") or nested(record, "gaspar_context", "timing_quality", "active_session") or "UNKNOWN").lower()
                sessions[session] += 1
                yearly[str(anchor.year)] += 1
                monthly[anchor.strftime("%Y-%m")] += 1
                first_ts = min_dt(first_ts, timestamp)
                last_ts = max_dt(last_ts, timestamp)
                first_anchor = min_dt(first_anchor, anchor)
                last_anchor = max_dt(last_anchor, anchor)
                per_symbol_anchors[symbol].append(anchor)

                if last_in_file and anchor < last_in_file:
                    out_of_order_files.append({"file": str(file_path), "line": line_number, "previous": iso(last_in_file), "current": iso(anchor)})
                last_in_file = anchor

                if nested(record, "validation", "is_valid") is True:
                    validation_valid += 1
                else:
                    source_invalid += 1
                if str(record.get("trigger_type") or "").lower() != "closed_bar":
                    trigger_not_closed_bar += 1

                if invalid_ohlc(record):
                    ohlc_invalid += 1
                spread = to_float(record.get("spread_pips"))
                if spread is not None:
                    spread_values.append(spread)
                    if spread < 0:
                        spread_negative += 1
                    if spread > 5.0:
                        spread_extreme += 1
                high = to_float(record.get("anchor_high") or record.get("high"))
                low = to_float(record.get("anchor_low") or record.get("low"))
                if high is not None and low is not None:
                    range_pips_values.append(max(0.0, (high - low) / pip_size(symbol)))

                features = record.get("features")
                if not isinstance(features, list):
                    missing_features += 1
                else:
                    feature_timeframes = {str(item.get("timeframe")) for item in features if isinstance(item, dict)}
                    if REQUIRED_FEATURE_TIMEFRAMES.issubset(feature_timeframes):
                        complete_features += 1
                    else:
                        missing_features += 1
                    feature_status_bad += audit_feature_alignment(features, timestamp, mtf_age_failures, mtf_close_leakage)

                gaspar_context = record.get("gaspar_context")
                if not isinstance(gaspar_context, dict):
                    missing_gaspar_context += 1
                else:
                    if gaspar_context.get("is_available") is True:
                        gaspar_available += 1
                    audit_gaspar_mtf(gaspar_context, timestamp, gaspar_mtf_failures)

                for path, has_value in find_forbidden_paths(record):
                    forbidden_paths[path] += 1
                    if has_value:
                        forbidden_non_null_paths[path] += 1
        if records_in_file == 0:
            file_empty += 1
        if records_in_file == 0 and file_path.stat().st_size > 0:
            file_corrupt += 1

    gaps = audit_gaps(per_symbol_anchors)
    issues = classify_issues(
        total_unique=total_unique,
        parse_errors=parse_errors,
        duplicate_snapshot_ids=duplicate_snapshot_ids,
        duplicate_symbol_anchor=duplicate_symbol_anchor,
        out_of_order_count=len(out_of_order_files),
        ohlc_invalid=ohlc_invalid,
        spread_negative=spread_negative,
        spread_extreme=spread_extreme,
        missing_features=missing_features,
        missing_gaspar_context=missing_gaspar_context,
        mtf_age_failures=sum(mtf_age_failures.values()),
        mtf_close_leakage=sum(mtf_close_leakage.values()),
        gaspar_mtf_failures=sum(gaspar_mtf_failures.values()),
        forbidden_paths=sum(forbidden_paths.values()),
        forbidden_non_null_paths=sum(forbidden_non_null_paths.values()),
        trigger_not_closed_bar=trigger_not_closed_bar,
        gaps=gaps,
    )
    decision = dataset_decision(issues)
    total_size = sum(path.stat().st_size for path in jsonl_files + csv_files)
    return {
        "schema_version": "bot_a_sub3_full_audit_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "data_path": str(data_path),
        "runs_detected": [{"path": str(path), "last_write_time": path.stat().st_mtime} for path in runs],
        "inventory": {
            "jsonl_files": len(jsonl_files),
            "csv_files": len(csv_files),
            "empty_jsonl_files": file_empty,
            "corrupt_jsonl_files": file_corrupt,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "jsonl_size_mb": round(sum(path.stat().st_size for path in jsonl_files) / (1024 * 1024), 2),
            "csv_size_mb": round(sum(path.stat().st_size for path in csv_files) / (1024 * 1024), 2),
            "raw_jsonl_lines": total_lines,
            "unique_snapshots": total_unique,
            "duplicate_snapshot_ids_removed_from_view": duplicate_snapshot_ids,
            "duplicate_symbol_anchor_removed_from_view": duplicate_symbol_anchor,
            "source_runs_unique_snapshots": dict(source_runs),
            "symbols": dict(symbols),
            "timeframes": dict(timeframes),
            "first_timestamp": iso(first_ts),
            "last_timestamp": iso(last_ts),
            "first_anchor_bar_timestamp": iso(first_anchor),
            "last_anchor_bar_timestamp": iso(last_anchor),
        },
        "quality": {
            "valid_snapshots_by_source_flag": validation_valid,
            "invalid_or_unflagged_snapshots": source_invalid,
            "parse_errors_count": len(parse_errors),
            "parse_errors_sample": parse_errors[:20],
            "duplicates_by_snapshot_id": duplicate_snapshot_ids,
            "duplicates_by_symbol_anchor": duplicate_symbol_anchor,
            "timestamps_out_of_order_count": len(out_of_order_files),
            "timestamps_out_of_order_sample": out_of_order_files[:20],
            "timezone_naive_fields": dict(timezone_naive_fields),
            "ohlc_invalid": ohlc_invalid,
            "spread_negative": spread_negative,
            "spread_extreme_gt_5_pips": spread_extreme,
            "features_complete_count": complete_features,
            "features_complete_pct": pct(complete_features, total_unique),
            "gaspar_context_available_count": gaspar_available,
            "gaspar_context_available_pct": pct(gaspar_available, total_unique),
            "missing_gaspar_context": missing_gaspar_context,
        },
        "magi_critical_checks": {
            "trigger_not_closed_bar": trigger_not_closed_bar,
            "anchor_not_m5": anchor_not_m5,
            "mtf_age_failures": dict(mtf_age_failures),
            "mtf_close_timestamp_leakage": dict(mtf_close_leakage),
            "gaspar_mtf_failures": dict(gaspar_mtf_failures),
            "forbidden_future_columns_total": sum(forbidden_paths.values()),
            "forbidden_future_columns_top": dict(forbidden_paths.most_common(30)),
            "forbidden_future_columns_non_null_total": sum(forbidden_non_null_paths.values()),
            "forbidden_future_columns_non_null_top": dict(forbidden_non_null_paths.most_common(30)),
        },
        "temporal_gaps": gaps,
        "market_distribution": {
            "by_year": dict(sorted(yearly.items())),
            "by_month": dict(sorted(monthly.items())),
            "by_session": dict(sorted(sessions.items())),
            "spread_pips": distribution(spread_values),
            "m5_range_pips": distribution(range_pips_values),
        },
        "issues": issues,
        "decision": decision,
        "cleaning_proposal": cleaning_proposal(issues),
    }


def discover_runs(data_path: Path) -> list[Path]:
    if data_path.name.startswith("run_"):
        return [data_path]
    runs = sorted([path for path in data_path.iterdir() if path.is_dir() and path.name.startswith("run_")])
    return runs or [data_path]


def run_for_path(file_path: Path, runs: list[Path]) -> str:
    for run in runs:
        try:
            file_path.relative_to(run)
            return run.name
        except ValueError:
            continue
    return "<root>"


def parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def is_naive_timestamp_text(value: Any) -> bool:
    if value in (None, ""):
        return False
    text = str(value)
    return "T" in text and not text.endswith("Z") and "+" not in text[10:] and "-" not in text[10:]


def invalid_ohlc(record: dict[str, Any]) -> bool:
    open_ = to_float(record.get("anchor_open") or record.get("open"))
    high = to_float(record.get("anchor_high") or record.get("high"))
    low = to_float(record.get("anchor_low") or record.get("low"))
    close = to_float(record.get("anchor_close") or record.get("close"))
    if None in {open_, high, low, close}:
        return True
    return bool(high < low or open_ > high or open_ < low or close > high or close < low)


def audit_feature_alignment(features: list[dict[str, Any]], snapshot_ts: datetime, age_failures: Counter, close_leakage: Counter) -> int:
    failures = 0
    for feature in features:
        if not isinstance(feature, dict):
            failures += 1
            continue
        timeframe = str(feature.get("timeframe") or "")
        status = str(feature.get("data_source_status") or "").upper()
        age = to_float(feature.get("age_minutes"))
        close_ts = parse_timestamp(feature.get("bar_close_timestamp"))
        if status != "OK":
            failures += 1
        if timeframe in MAX_AGE_MINUTES and (age is None or age < -0.01 or age > MAX_AGE_MINUTES[timeframe] + 0.01):
            age_failures[timeframe] += 1
            failures += 1
        if close_ts is not None and close_ts > snapshot_ts:
            close_leakage[timeframe] += 1
            failures += 1
    return failures


def audit_gaspar_mtf(context: dict[str, Any], snapshot_ts: datetime, failures: Counter) -> None:
    for timeframe, max_age in {"h4": 240.0, "d1": 1440.0}.items():
        age = to_float(context.get(f"{timeframe}_age_minutes"))
        ts = parse_timestamp(context.get(f"{timeframe}_bar_timestamp"))
        if age is None or age < -0.01 or age > max_age + 0.01:
            failures[f"{timeframe}_age"] += 1
        if ts is not None and ts > snapshot_ts:
            failures[f"{timeframe}_future_timestamp"] += 1


def find_forbidden_paths(value: Any, prefix: str = "") -> list[tuple[str, bool]]:
    found: list[tuple[str, bool]] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            if forbidden_key(str(key)):
                found.append((current, has_non_null_value(nested_value)))
                continue
            found.extend(find_forbidden_paths(nested_value, current))
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            found.extend(find_forbidden_paths(nested_value, f"{prefix}[{index}]"))
    return found


def has_non_null_value(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, list):
        return any(has_non_null_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_non_null_value(item) for item in value.values())
    return True


def forbidden_key(key: str) -> bool:
    lower = key.lower()
    return any(keyword in lower for keyword in FORBIDDEN_KEYWORDS)


def audit_gaps(per_symbol_anchors: dict[str, list[datetime]]) -> dict[str, Any]:
    result = {}
    for symbol, anchors in per_symbol_anchors.items():
        ordered = sorted(set(anchors))
        gap_counts = Counter()
        examples = []
        duplicate_anchor_count = len(anchors) - len(ordered)
        previous = None
        max_gap_minutes = 0.0
        for current in ordered:
            if previous is None:
                previous = current
                continue
            delta_minutes = (current - previous).total_seconds() / 60.0
            max_gap_minutes = max(max_gap_minutes, delta_minutes)
            if delta_minutes > 5.01:
                if delta_minutes <= 30:
                    bucket = "minor_5_to_30_min"
                elif delta_minutes <= 240:
                    bucket = "intraday_30_to_240_min"
                elif delta_minutes <= 4320:
                    bucket = "market_closure_or_multiday"
                else:
                    bucket = "major_gt_3_days"
                gap_counts[bucket] += 1
                if len(examples) < 20:
                    examples.append({"from": iso(previous), "to": iso(current), "minutes": round(delta_minutes, 2), "bucket": bucket})
            previous = current
        result[symbol] = {
            "ordered_unique_anchors": len(ordered),
            "duplicate_anchor_count_after_id_dedupe": duplicate_anchor_count,
            "gap_counts": dict(gap_counts),
            "max_gap_minutes": round(max_gap_minutes, 2),
            "gap_examples": examples,
        }
    return result


def classify_issues(**kwargs: Any) -> list[dict[str, Any]]:
    issues = []
    add_issue(issues, "parse_errors", kwargs["parse_errors"], "critical", "JSONL parse errors can corrupt the historical sequence.")
    add_issue(issues, "duplicate_snapshot_ids", kwargs["duplicate_snapshot_ids"], "high", "Duplicates must be removed before simulation.")
    add_issue(issues, "duplicate_symbol_anchor", kwargs["duplicate_symbol_anchor"], "high", "Duplicate symbol/timestamp anchors can overweight periods.")
    add_issue(issues, "timestamps_out_of_order", kwargs["out_of_order_count"], "medium", "Out-of-order files are safe if timeline sorting is enforced.")
    add_issue(issues, "ohlc_invalid", kwargs["ohlc_invalid"], "critical", "Invalid OHLC breaks price outcome calculations.")
    add_issue(issues, "spread_negative", kwargs["spread_negative"], "high", "Negative spread is invalid market data.")
    add_issue(issues, "spread_extreme_gt_5_pips", kwargs["spread_extreme"], "medium", "Extreme spreads may require filtering by session/news.")
    add_issue(issues, "missing_features", kwargs["missing_features"], "high", "Missing MTF features can block real mage inference.")
    add_issue(issues, "missing_gaspar_context", kwargs["missing_gaspar_context"], "high", "Gaspar real requires gaspar_context.")
    add_issue(issues, "mtf_age_failures", kwargs["mtf_age_failures"], "critical", "MTF age failures can indicate stale or future bars.")
    add_issue(issues, "mtf_close_timestamp_leakage", kwargs["mtf_close_leakage"], "critical", "Feature close timestamps after snapshot are leakage.")
    add_issue(issues, "gaspar_mtf_failures", kwargs["gaspar_mtf_failures"], "critical", "Gaspar H4/D1 timestamps or ages are inconsistent.")
    add_issue(issues, "forbidden_future_columns_present", kwargs["forbidden_paths"], "medium", "Forbidden feature names are present and must be stripped before modeling.")
    add_issue(issues, "forbidden_future_columns_non_null", kwargs["forbidden_non_null_paths"], "critical", "Non-null future/outcome values would contaminate model features.")
    add_issue(issues, "trigger_not_closed_bar", kwargs["trigger_not_closed_bar"], "critical", "Non-closed bars may leak current candle state.")
    for symbol, gap_info in kwargs["gaps"].items():
        minor = gap_info["gap_counts"].get("minor_5_to_30_min", 0) + gap_info["gap_counts"].get("intraday_30_to_240_min", 0)
        if minor:
            add_issue(issues, f"temporal_gaps_{symbol}", minor, "medium", "Intraday M5 gaps can bias forward horizons.")
    return issues


def add_issue(issues: list[dict[str, Any]], code: str, count: int | list[Any], severity: str, impact: str) -> None:
    value = len(count) if isinstance(count, list) else int(count or 0)
    if value:
        issues.append({"code": code, "count": value, "severity": severity, "impact": impact})


def dataset_decision(issues: list[dict[str, Any]]) -> str:
    severities = Counter(issue["severity"] for issue in issues)
    if severities["critical"]:
        return "no apto"
    if severities["high"] or severities["medium"]:
        return "apto con advertencias"
    return "apto"


def cleaning_proposal(issues: list[dict[str, Any]]) -> list[str]:
    proposals = [
        "Usar JSONL como fuente primaria y CSV solo como respaldo/inventario para evitar duplicados.",
        "Consolidar por snapshot_id y por (symbol, anchor_bar_timestamp), conservando el primer registro válido.",
        "Ordenar siempre por symbol + anchor_bar_timestamp antes de cualquier simulación.",
        "Filtrar snapshots con validation.is_valid=false o con OHLC inválido.",
        "Mantener timestamps normalizados a UTC y documentar campos fuente sin sufijo Z como UTC asumido.",
    ]
    codes = {issue["code"] for issue in issues}
    if "temporal_gaps_EURUSD" in codes:
        proposals.append("Crear un calendario de mercado para distinguir cierres normales de gaps intradía reales.")
    if "spread_extreme_gt_5_pips" in codes:
        proposals.append("Revisar snapshots con spread_pips > 5 y decidir si se filtran o se etiquetan como régimen de baja calidad.")
    if "forbidden_future_columns_present" in codes or "forbidden_future_columns_non_null" in codes:
        proposals.append("Aplicar leakage guard antes de entregar features a cualquier modelo.")
    return proposals


def nested(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def min_dt(left: datetime | None, right: datetime) -> datetime:
    return right if left is None or right < left else left


def max_dt(left: datetime | None, right: datetime) -> datetime:
    return right if left is None or right > left else left


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def pct(count: int, total: int) -> float:
    return round((count / total) * 100, 4) if total else 0.0


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.upper().endswith("JPY") else 0.0001


def distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "min": None, "p25": None, "median": None, "p75": None, "p95": None, "p99": None, "max": None}
    ordered = sorted(values)
    return {
        "count": len(values),
        "mean": round(mean(values), 6),
        "min": round(ordered[0], 6),
        "p25": percentile(ordered, 0.25),
        "median": percentile(ordered, 0.5),
        "p75": percentile(ordered, 0.75),
        "p95": percentile(ordered, 0.95),
        "p99": percentile(ordered, 0.99),
        "max": round(ordered[-1], 6),
    }


def percentile(ordered: list[float], q: float) -> float:
    if len(ordered) == 1:
        return round(ordered[0], 6)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round((ordered[lower] * (1 - weight)) + (ordered[upper] * weight), 6)


def markdown_report(audit: dict[str, Any]) -> str:
    inv = audit["inventory"]
    q = audit["quality"]
    m = audit["magi_critical_checks"]
    md = [
        "# Bot A sub3 Full Historical Data Quality Audit",
        "",
        "## Resumen Ejecutivo",
        "",
        f"- Decision: **{audit['decision']}**",
        f"- Dataset auditado: `{audit['data_path']}`",
        f"- Runs detectados: `{len(audit['runs_detected'])}`",
        f"- Archivos JSONL: `{inv['jsonl_files']}`",
        f"- Archivos CSV: `{inv['csv_files']}`",
        f"- Tamaño total: `{inv['total_size_mb']} MB`",
        f"- Snapshots únicos consolidados: `{inv['unique_snapshots']}`",
        f"- Rango anchor: `{inv['first_anchor_bar_timestamp']}` a `{inv['last_anchor_bar_timestamp']}`",
        f"- Símbolos: `{inv['symbols']}`",
        f"- Timeframes: `{inv['timeframes']}`",
        "",
        "## Problemas Encontrados",
        "",
    ]
    if audit["issues"]:
        md.extend(["| Severidad | Código | Conteo | Impacto |", "|---|---|---:|---|"])
        for issue in audit["issues"]:
            md.append(f"| {issue['severity']} | {issue['code']} | {issue['count']} | {issue['impact']} |")
    else:
        md.append("No se encontraron problemas materiales.")
    md.extend(
        [
            "",
            "## Calidad",
            "",
            f"- Snapshots validos por flag fuente: `{q['valid_snapshots_by_source_flag']}`",
            f"- Invalidos o sin flag valido: `{q['invalid_or_unflagged_snapshots']}`",
            f"- Duplicados snapshot_id removidos de la vista unica: `{q['duplicates_by_snapshot_id']}`",
            f"- Duplicados symbol+anchor removidos de la vista unica: `{q['duplicates_by_symbol_anchor']}`",
            f"- OHLC invalido: `{q['ohlc_invalid']}`",
            f"- Spreads negativos: `{q['spread_negative']}`",
            f"- Spreads extremos > 5 pips: `{q['spread_extreme_gt_5_pips']}`",
            f"- Features completas: `{q['features_complete_pct']}%`",
            f"- Gaspar context disponible: `{q['gaspar_context_available_pct']}%`",
            "",
            "## Chequeos Criticos MAGI",
            "",
            f"- Trigger no closed_bar: `{m['trigger_not_closed_bar']}`",
            f"- Anchor distinto de M5: `{m['anchor_not_m5']}`",
            f"- MTF age failures: `{m['mtf_age_failures']}`",
            f"- MTF close timestamp leakage: `{m['mtf_close_timestamp_leakage']}`",
            f"- Gaspar MTF failures: `{m['gaspar_mtf_failures']}`",
            f"- Columnas futuras/prohibidas detectadas: `{m['forbidden_future_columns_total']}`",
            f"- Top columnas prohibidas: `{m['forbidden_future_columns_top']}`",
            f"- Columnas futuras/prohibidas con valor no nulo: `{m['forbidden_future_columns_non_null_total']}`",
            f"- Top columnas prohibidas no nulas: `{m['forbidden_future_columns_non_null_top']}`",
            "",
            "## Distribucion De Mercado",
            "",
            f"- Conteo por año: `{audit['market_distribution']['by_year']}`",
            f"- Conteo por sesión: `{audit['market_distribution']['by_session']}`",
            f"- Spread pips: `{audit['market_distribution']['spread_pips']}`",
            f"- Rango M5 pips: `{audit['market_distribution']['m5_range_pips']}`",
            "",
            "## Gaps Temporales",
            "",
            f"`{audit['temporal_gaps']}`",
            "",
            "## Propuesta De Limpieza",
            "",
        ]
    )
    md.extend(f"- {item}" for item in audit["cleaning_proposal"])
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
