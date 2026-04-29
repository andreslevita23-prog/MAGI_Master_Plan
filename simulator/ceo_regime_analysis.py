from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


HORIZONS = ("12", "48", "96", "288")
SIGNALS = (
    "BALTASAR_BUY",
    "BALTASAR_SELL",
    "BUY_GOOD",
    "SELL_GOOD",
    "GASPAR_GOOD",
    "GASPAR_FAIR",
    "GASPAR_POOR",
)
MIN_SAMPLE_H48 = 500


def analyze_regimes(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    records_path = root / "ceo_training_records.jsonl"
    if not records_path.exists():
        raise FileNotFoundError(f"Missing ceo_training_records.jsonl: {records_path}")

    stats: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(new_stats)
    records_analyzed = 0
    with records_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            records_analyzed += 1
            segments = segment_values(record)
            signals = record_signals(record)
            for signal in signals:
                for segment_type, segment_value in segments.items():
                    update_stats(stats[(segment_type, segment_value, signal)], record, signal)

    rows = [finalize_row(key, value) for key, value in stats.items()]
    rows.sort(key=lambda item: (item["segment_type"], item["segment_value"], item["signal"]))
    best = sorted(sufficient_h48(rows), key=lambda item: score_h48(item), reverse=True)[:25]
    worst = sorted(sufficient_h48(rows), key=lambda item: score_h48(item))[:25]
    analysis = {
        "schema_version": "ceo_regime_analysis_v0.1",
        "run_dir": str(root),
        "records_analyzed": records_analyzed,
        "horizons": list(HORIZONS),
        "signals": list(SIGNALS),
        "minimum_sufficient_h48_directional_cases": MIN_SAMPLE_H48,
        "best_segments_h48": best,
        "worst_segments_h48": worst,
        "sufficient_segments_h48_count": len(sufficient_h48(rows)),
        "segments": rows,
    }
    return analysis


def write_regime_analysis(run_dir: str | Path, analysis: dict[str, Any]) -> None:
    root = Path(run_dir)
    (root / "ceo_regime_analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    write_segments_csv(root / "ceo_regime_segments.csv", analysis["segments"])
    (root / "ceo_regime_analysis.md").write_text(markdown_report(analysis), encoding="utf-8")


def new_stats() -> dict[str, Any]:
    return {
        horizon: {
            "cases": 0,
            "directional_cases": 0,
            "hits": 0,
            "net": [],
            "mfe": [],
            "mae": [],
        }
        for horizon in HORIZONS
    }


def update_stats(stats: dict[str, Any], record: dict[str, Any], signal: str) -> None:
    direction = record["baltasar_vote"].get("direction")
    for horizon, outcome in record.get("future_outcomes", {}).items():
        if horizon not in stats:
            continue
        hstats = stats[horizon]
        hstats["cases"] += 1
        if direction not in {"BUY", "SELL"}:
            continue
        hstats["directional_cases"] += 1
        if outcome.get("real_direction") == direction:
            hstats["hits"] += 1
        hstats["net"].append(net_directional_pips(outcome, direction))
        hstats["mfe"].append(float(outcome.get("max_favorable_excursion") or 0.0))
        hstats["mae"].append(float(outcome.get("max_adverse_excursion") or 0.0))


def record_signals(record: dict[str, Any]) -> list[str]:
    direction = record["baltasar_vote"].get("direction")
    quality = record["gaspar_vote"].get("quality")
    signals = []
    if direction == "BUY":
        signals.append("BALTASAR_BUY")
        if quality == "GOOD":
            signals.append("BUY_GOOD")
    elif direction == "SELL":
        signals.append("BALTASAR_SELL")
        if quality == "GOOD":
            signals.append("SELL_GOOD")
    if quality in {"GOOD", "FAIR", "POOR"}:
        signals.append(f"GASPAR_{quality}")
    return signals


def segment_values(record: dict[str, Any]) -> dict[str, str]:
    features = record.get("features_at_decision_time") or {}
    gaspar = features.get("gaspar_context") if isinstance(features.get("gaspar_context"), dict) else {}
    htf = gaspar.get("higher_timeframe_confluence") if isinstance(gaspar.get("higher_timeframe_confluence"), dict) else {}
    timing = gaspar.get("timing_quality") if isinstance(gaspar.get("timing_quality"), dict) else {}
    day = gaspar.get("day_context") if isinstance(gaspar.get("day_context"), dict) else {}
    position = gaspar.get("price_structure_position") if isinstance(gaspar.get("price_structure_position"), dict) else {}
    timestamp = parse_dt(record.get("timestamp"))
    high = as_float(features.get("high"))
    low = as_float(features.get("low"))
    spread = as_float(features.get("spread_pips"))
    range_pips = (high - low) / 0.0001 if high is not None and low is not None else None
    return {
        "active_session": str(features.get("active_session") or timing.get("active_session") or "UNKNOWN").lower(),
        "year": str(timestamp.year) if timestamp else "UNKNOWN",
        "month": timestamp.strftime("%Y-%m") if timestamp else "UNKNOWN",
        "day_of_week": str(day.get("day_of_week") or (timestamp.strftime("%A").lower() if timestamp else "UNKNOWN")).lower(),
        "hour_utc": f"{timestamp.hour:02d}" if timestamp else "UNKNOWN",
        "m5_range_bucket": bucket(range_pips, [(2, "<=2"), (5, "2-5"), (10, "5-10"), (20, "10-20")], ">20"),
        "spread_bucket": bucket(spread, [(0.2, "<=0.2"), (0.5, "0.2-0.5"), (1.0, "0.5-1"), (2.0, "1-2"), (5.0, "2-5")], ">5"),
        "h4_structure": str(htf.get("h4_structure") or "UNKNOWN").lower(),
        "d1_structure": str(htf.get("d1_structure") or "UNKNOWN").lower(),
        "directional_alignment": str(htf.get("directional_alignment") or "UNKNOWN").lower(),
        "daily_atr_consumed_pct_bucket": bucket(as_float(timing.get("daily_atr_consumed_pct")), [(0.5, "<=0.5"), (0.85, "0.5-0.85"), (1.2, "0.85-1.2"), (1.5, "1.2-1.5")], ">1.5"),
        "position_in_d1_range_bucket": bucket(as_float(position.get("position_in_d1_range")), [(0.25, "<=0.25"), (0.5, "0.25-0.5"), (0.75, "0.5-0.75"), (1.0, "0.75-1.0")], ">1.0"),
    }


def finalize_row(key: tuple[str, str, str], stats: dict[str, Any]) -> dict[str, Any]:
    segment_type, segment_value, signal = key
    return {
        "segment_type": segment_type,
        "segment_value": segment_value,
        "signal": signal,
        "horizons": {horizon: finalize_horizon(hstats) for horizon, hstats in stats.items()},
    }


def finalize_horizon(hstats: dict[str, Any]) -> dict[str, Any]:
    directional_cases = hstats["directional_cases"]
    return {
        "cases": hstats["cases"],
        "directional_cases": directional_cases,
        "hit_rate": round(hstats["hits"] / directional_cases, 6) if directional_cases else None,
        "avg_net_directional_pips": mean(hstats["net"]),
        "median_net_directional_pips": percentile(hstats["net"], 0.5),
        "avg_mfe": mean(hstats["mfe"]),
        "avg_mae": mean(hstats["mae"]),
    }


def sufficient_h48(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["horizons"]["48"]["directional_cases"] >= MIN_SAMPLE_H48]


def score_h48(row: dict[str, Any]) -> float:
    h = row["horizons"]["48"]
    return float(h.get("avg_net_directional_pips") or 0.0)


def write_segments_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "segment_type",
        "segment_value",
        "signal",
        "horizon",
        "cases",
        "directional_cases",
        "hit_rate",
        "avg_net_directional_pips",
        "median_net_directional_pips",
        "avg_mfe",
        "avg_mae",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            for horizon in HORIZONS:
                h = row["horizons"][horizon]
                writer.writerow({
                    "segment_type": row["segment_type"],
                    "segment_value": row["segment_value"],
                    "signal": row["signal"],
                    "horizon": horizon,
                    **h,
                })


def markdown_report(analysis: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI Regime Analysis",
        "",
        f"- records_analyzed: {analysis['records_analyzed']}",
        f"- minimum_sufficient_h48_directional_cases: {analysis['minimum_sufficient_h48_directional_cases']}",
        f"- sufficient_segments_h48_count: {analysis['sufficient_segments_h48_count']}",
        "",
        "## Best Segments H48",
        segment_table(analysis["best_segments_h48"][:20]),
        "",
        "## Worst Segments H48",
        segment_table(analysis["worst_segments_h48"][:20]),
        "",
        "## Notes",
        "",
        "- Metrics are descriptive and use H48 as the primary horizon.",
        "- Hit rate is calculated only for directional Baltasar votes.",
        "- Gaspar quality groups include all cases, but hit rate/net pips only apply where Baltasar was BUY or SELL.",
    ]
    return "\n".join(lines) + "\n"


def segment_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Segment | Value | Signal | Cases | Directional | Hit | Avg net | Median | MFE | MAE |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        h = row["horizons"]["48"]
        lines.append(
            f"| {row['segment_type']} | {row['segment_value']} | {row['signal']} | "
            f"{h['cases']} | {h['directional_cases']} | {fmt_pct(h['hit_rate'])} | "
            f"{fmt(h['avg_net_directional_pips'])} | {fmt(h['median_net_directional_pips'])} | "
            f"{fmt(h['avg_mfe'])} | {fmt(h['avg_mae'])} |"
        )
    return "\n".join(lines)


def net_directional_pips(outcome: dict[str, Any], direction: str) -> float:
    value = float(outcome.get("future_return_pips") or 0.0)
    return value if direction == "BUY" else -value


def parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def bucket(value: float | None, thresholds: list[tuple[float, str]], above_label: str) -> str:
    if value is None:
        return "UNKNOWN"
    for limit, label in thresholds:
        if value <= limit:
            return label
    return above_label


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    weight = pos - lower
    return round((ordered[lower] * (1 - weight)) + (ordered[upper] * weight), 6)


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze CEO-MAGI signals by market regime.")
    parser.add_argument("run_dir", help="CEO training output run directory.")
    args = parser.parse_args()
    analysis = analyze_regimes(args.run_dir)
    write_regime_analysis(args.run_dir, analysis)
    print(json.dumps({
        "records_analyzed": analysis["records_analyzed"],
        "sufficient_segments_h48_count": analysis["sufficient_segments_h48_count"],
        "outputs": [
            str(Path(args.run_dir) / "ceo_regime_analysis.json"),
            str(Path(args.run_dir) / "ceo_regime_analysis.md"),
            str(Path(args.run_dir) / "ceo_regime_segments.csv"),
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
