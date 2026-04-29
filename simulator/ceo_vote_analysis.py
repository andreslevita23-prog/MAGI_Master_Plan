from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


HORIZONS = ("12", "48", "96", "288")


def analyze_ceo_votes(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    records_path = root / "ceo_training_records.jsonl"
    if not records_path.exists():
        raise FileNotFoundError(f"Missing ceo_training_records.jsonl: {records_path}")

    combo_stats: dict[tuple[str, str, str], dict[str, Any]] = {}
    segment_stats: dict[str, dict[str, Any]] = {
        "melchor": defaultdict(new_stats),
        "gaspar": defaultdict(new_stats),
        "baltasar_directional_vs_neutral": defaultdict(new_stats),
        "approve_good_directional": defaultdict(new_stats),
        "alignment": defaultdict(new_stats),
    }

    total_records = 0
    with records_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            total_records += 1
            melchor = record["melchor_vote"].get("vote") or "NONE"
            baltasar = record["baltasar_vote"].get("direction") or "NONE"
            gaspar = record["gaspar_vote"].get("quality") or "NONE"
            key = (melchor, baltasar, gaspar)
            stats = combo_stats.setdefault(key, new_stats())
            update_stats(stats, record)

            update_stats(segment_stats["melchor"][melchor], record)
            update_stats(segment_stats["gaspar"][gaspar], record)
            update_stats(
                segment_stats["baltasar_directional_vs_neutral"]["DIRECTIONAL" if baltasar in {"BUY", "SELL"} else "NEUTRAL"],
                record,
            )
            approve_good_directional = (
                "APPROVE_GOOD_DIRECTIONAL"
                if melchor == "APPROVE" and gaspar == "GOOD" and baltasar in {"BUY", "SELL"}
                else "OTHER"
            )
            update_stats(segment_stats["approve_good_directional"][approve_good_directional], record)
            update_stats(segment_stats["alignment"][alignment_bucket(melchor, baltasar, gaspar)], record)

    combo_rows = [finalize_combo(key, stats) for key, stats in combo_stats.items()]
    combo_rows.sort(key=lambda item: (combo_score(item), item["records"]), reverse=True)
    segment_summary = {
        group: {name: finalize_stats(stats) for name, stats in sorted(values.items())}
        for group, values in segment_stats.items()
    }
    analysis = {
        "schema_version": "ceo_vote_analysis_v0.1",
        "run_dir": str(root),
        "records_analyzed": total_records,
        "horizons": list(HORIZONS),
        "combination_count": len(combo_rows),
        "best_combinations": combo_rows[:10],
        "worst_combinations": sorted(combo_rows, key=lambda item: (combo_score(item), -item["records"]))[:10],
        "segments": segment_summary,
        "all_combinations": combo_rows,
    }
    return analysis


def write_analysis(run_dir: str | Path, analysis: dict[str, Any]) -> None:
    root = Path(run_dir)
    (root / "ceo_vote_analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    write_combo_csv(root / "ceo_vote_analysis_by_combo.csv", analysis["all_combinations"])
    (root / "ceo_vote_analysis.md").write_text(analysis_markdown(analysis), encoding="utf-8")


def new_stats() -> dict[str, Any]:
    return {
        "records": 0,
        "horizons": {
            horizon: {
                "records": 0,
                "real_direction": Counter(),
                "future_return_pips_sum": 0.0,
                "mfe_sum": 0.0,
                "mae_sum": 0.0,
                "directional_total": 0,
                "directional_hits": 0,
            }
            for horizon in HORIZONS
        },
    }


def update_stats(stats: dict[str, Any], record: dict[str, Any]) -> None:
    stats["records"] += 1
    baltasar = record["baltasar_vote"].get("direction") or "NONE"
    for horizon, outcome in record.get("future_outcomes", {}).items():
        if horizon not in stats["horizons"]:
            continue
        hstats = stats["horizons"][horizon]
        hstats["records"] += 1
        real_direction = outcome.get("real_direction") or "NONE"
        hstats["real_direction"][real_direction] += 1
        hstats["future_return_pips_sum"] += float(outcome.get("future_return_pips") or 0.0)
        hstats["mfe_sum"] += float(outcome.get("max_favorable_excursion") or 0.0)
        hstats["mae_sum"] += float(outcome.get("max_adverse_excursion") or 0.0)
        if baltasar in {"BUY", "SELL"}:
            hstats["directional_total"] += 1
            if real_direction == baltasar:
                hstats["directional_hits"] += 1


def finalize_combo(key: tuple[str, str, str], stats: dict[str, Any]) -> dict[str, Any]:
    melchor, baltasar, gaspar = key
    return {
        "melchor_vote": melchor,
        "baltasar_direction": baltasar,
        "gaspar_quality": gaspar,
        **finalize_stats(stats),
    }


def finalize_stats(stats: dict[str, Any]) -> dict[str, Any]:
    horizons = {}
    for horizon, hstats in stats["horizons"].items():
        count = hstats["records"]
        directional_total = hstats["directional_total"]
        horizons[horizon] = {
            "records": count,
            "real_direction_distribution": dict(sorted(hstats["real_direction"].items())),
            "avg_future_return_pips": average(hstats["future_return_pips_sum"], count),
            "avg_mfe": average(hstats["mfe_sum"], count),
            "avg_mae": average(hstats["mae_sum"], count),
            "directional_hit_rate": average(hstats["directional_hits"], directional_total),
            "directional_total": directional_total,
        }
    return {"records": stats["records"], "horizons": horizons}


def average(total: float, count: int) -> float | None:
    if count == 0:
        return None
    return round(total / count, 6)


def combo_score(row: dict[str, Any], horizon: str = "48") -> float:
    hstats = row["horizons"].get(horizon, {})
    hit_rate = hstats.get("directional_hit_rate")
    avg_return = hstats.get("avg_future_return_pips") or 0.0
    avg_mfe = hstats.get("avg_mfe") or 0.0
    avg_mae = hstats.get("avg_mae") or 0.0
    if hit_rate is None:
        hit_rate = 0.0
    return (hit_rate * 100.0) + avg_return + (0.1 * avg_mfe) + (0.1 * avg_mae)


def alignment_bucket(melchor: str, baltasar: str, gaspar: str) -> str:
    if baltasar == "NEUTRAL":
        return "BALTASAR_NEUTRAL"
    if melchor == "APPROVE" and gaspar in {"GOOD", "FAIR"} and baltasar in {"BUY", "SELL"}:
        return "ALIGNED_ACTIONABLE"
    if melchor == "BLOCK" and baltasar in {"BUY", "SELL"}:
        return "MELCHOR_BLOCKS_DIRECTIONAL"
    if gaspar == "POOR" and baltasar in {"BUY", "SELL"}:
        return "GASPAR_POOR_DIRECTIONAL"
    return "MIXED_OR_DESALIGNED"


def write_combo_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "melchor_vote",
        "baltasar_direction",
        "gaspar_quality",
        "records",
    ]
    for horizon in HORIZONS:
        fieldnames.extend(
            [
                f"h{horizon}_records",
                f"h{horizon}_directional_hit_rate",
                f"h{horizon}_avg_future_return_pips",
                f"h{horizon}_avg_mfe",
                f"h{horizon}_avg_mae",
                f"h{horizon}_real_direction_distribution",
            ]
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = {
                "melchor_vote": row["melchor_vote"],
                "baltasar_direction": row["baltasar_direction"],
                "gaspar_quality": row["gaspar_quality"],
                "records": row["records"],
            }
            for horizon in HORIZONS:
                hstats = row["horizons"][horizon]
                flat[f"h{horizon}_records"] = hstats["records"]
                flat[f"h{horizon}_directional_hit_rate"] = hstats["directional_hit_rate"]
                flat[f"h{horizon}_avg_future_return_pips"] = hstats["avg_future_return_pips"]
                flat[f"h{horizon}_avg_mfe"] = hstats["avg_mfe"]
                flat[f"h{horizon}_avg_mae"] = hstats["avg_mae"]
                flat[f"h{horizon}_real_direction_distribution"] = json.dumps(
                    hstats["real_direction_distribution"], sort_keys=True
                )
            writer.writerow(flat)


def analysis_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI Vote Analysis",
        "",
        f"- records_analyzed: {analysis['records_analyzed']}",
        f"- combination_count: {analysis['combination_count']}",
        "",
        "## Best Combinations",
        combo_table(analysis["best_combinations"][:10]),
        "",
        "## Worst Combinations",
        combo_table(analysis["worst_combinations"][:10]),
        "",
        "## Segment Summary",
    ]
    for group, values in analysis["segments"].items():
        lines.extend(["", f"### {group}"])
        lines.append(segment_table(values))
    return "\n".join(lines) + "\n"


def combo_table(rows: list[dict[str, Any]], horizon: str = "48") -> str:
    lines = [
        "| Melchor | Baltasar | Gaspar | Records | H48 hit rate | H48 avg return | H48 avg MFE | H48 avg MAE |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        hstats = row["horizons"][horizon]
        lines.append(
            f"| {row['melchor_vote']} | {row['baltasar_direction']} | {row['gaspar_quality']} | "
            f"{row['records']} | {format_pct(hstats['directional_hit_rate'])} | "
            f"{format_num(hstats['avg_future_return_pips'])} | {format_num(hstats['avg_mfe'])} | {format_num(hstats['avg_mae'])} |"
        )
    return "\n".join(lines)


def segment_table(values: dict[str, Any], horizon: str = "48") -> str:
    lines = [
        "| Segment | Records | H48 hit rate | H48 avg return | H48 avg MFE | H48 avg MAE | H48 real_direction |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for name, stats in values.items():
        hstats = stats["horizons"][horizon]
        lines.append(
            f"| {name} | {stats['records']} | {format_pct(hstats['directional_hit_rate'])} | "
            f"{format_num(hstats['avg_future_return_pips'])} | {format_num(hstats['avg_mfe'])} | "
            f"{format_num(hstats['avg_mae'])} | {json.dumps(hstats['real_direction_distribution'], sort_keys=True)} |"
        )
    return "\n".join(lines)


def format_num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def format_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze CEO-MAGI vote combinations.")
    parser.add_argument("run_dir", help="CEO training output run directory.")
    args = parser.parse_args()
    analysis = analyze_ceo_votes(args.run_dir)
    write_analysis(args.run_dir, analysis)
    print(json.dumps({
        "records_analyzed": analysis["records_analyzed"],
        "combination_count": analysis["combination_count"],
        "outputs": [
            str(Path(args.run_dir) / "ceo_vote_analysis.json"),
            str(Path(args.run_dir) / "ceo_vote_analysis.md"),
            str(Path(args.run_dir) / "ceo_vote_analysis_by_combo.csv"),
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
