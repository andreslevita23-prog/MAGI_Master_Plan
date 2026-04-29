from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


HORIZONS = ("12", "48", "96", "288")
BALTASAR_GROUPS = ("BUY", "SELL", "NEUTRAL")
GASPAR_GROUPS = ("GOOD", "FAIR", "POOR")


def analyze_individual_votes(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    records_path = root / "ceo_training_records.jsonl"
    if not records_path.exists():
        raise FileNotFoundError(f"Missing ceo_training_records.jsonl: {records_path}")

    baltasar = {group: new_group_stats() for group in BALTASAR_GROUPS}
    gaspar = {group: new_group_stats() for group in GASPAR_GROUPS}
    cross = {
        f"{direction}_{quality}": new_group_stats()
        for direction in BALTASAR_GROUPS
        for quality in GASPAR_GROUPS
    }

    records_analyzed = 0
    with records_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            records_analyzed += 1
            direction = record["baltasar_vote"].get("direction") or "NEUTRAL"
            quality = record["gaspar_vote"].get("quality") or "POOR"
            direction = direction if direction in BALTASAR_GROUPS else "NEUTRAL"
            quality = quality if quality in GASPAR_GROUPS else "POOR"
            update_group(baltasar[direction], record, direction)
            update_group(gaspar[quality], record, direction)
            update_group(cross[f"{direction}_{quality}"], record, direction)

    return {
        "schema_version": "ceo_individual_vote_analysis_v0.1",
        "run_dir": str(root),
        "records_analyzed": records_analyzed,
        "horizons": list(HORIZONS),
        "baltasar": {group: finalize_group(stats) for group, stats in baltasar.items()},
        "gaspar": {group: finalize_group(stats) for group, stats in gaspar.items()},
        "baltasar_gaspar_cross": {group: finalize_group(stats) for group, stats in cross.items()},
    }


def write_individual_vote_analysis(run_dir: str | Path, analysis: dict[str, Any]) -> None:
    root = Path(run_dir)
    (root / "ceo_individual_vote_analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_group_csv(root / "baltasar_vote_outcomes.csv", "baltasar_direction", analysis["baltasar"])
    write_group_csv(root / "gaspar_quality_outcomes.csv", "gaspar_quality", analysis["gaspar"])
    write_group_csv(root / "baltasar_gaspar_cross_outcomes.csv", "baltasar_gaspar_group", analysis["baltasar_gaspar_cross"])
    (root / "ceo_individual_vote_analysis.md").write_text(markdown_report(analysis), encoding="utf-8")


def new_group_stats() -> dict[str, Any]:
    return {
        "records": 0,
        "horizons": {
            horizon: {
                "records": 0,
                "real_direction": defaultdict(int),
                "directional_total": 0,
                "directional_hits": 0,
                "future_return_pips": [],
                "favorable_pips": [],
                "adverse_pips": [],
                "mfe": [],
                "mae": [],
            }
            for horizon in HORIZONS
        },
    }


def update_group(stats: dict[str, Any], record: dict[str, Any], baltasar_direction: str) -> None:
    stats["records"] += 1
    for horizon, outcome in record.get("future_outcomes", {}).items():
        if horizon not in stats["horizons"]:
            continue
        hstats = stats["horizons"][horizon]
        real_direction = outcome.get("real_direction") or "NONE"
        future_return_pips = float(outcome.get("future_return_pips") or 0.0)
        mfe = float(outcome.get("max_favorable_excursion") or 0.0)
        mae = float(outcome.get("max_adverse_excursion") or 0.0)
        hstats["records"] += 1
        hstats["real_direction"][real_direction] += 1
        hstats["future_return_pips"].append(future_return_pips)
        hstats["mfe"].append(mfe)
        hstats["mae"].append(mae)
        favorable, adverse = favorable_adverse_pips(outcome, baltasar_direction)
        hstats["favorable_pips"].append(favorable)
        hstats["adverse_pips"].append(adverse)
        if baltasar_direction in {"BUY", "SELL"}:
            hstats["directional_total"] += 1
            if real_direction == baltasar_direction:
                hstats["directional_hits"] += 1


def favorable_adverse_pips(outcome: dict[str, Any], direction: str) -> tuple[float, float]:
    reached_up = float(outcome.get("reached_up_pips") or 0.0)
    reached_down = float(outcome.get("reached_down_pips") or 0.0)
    if direction == "BUY":
        return reached_up, reached_down
    if direction == "SELL":
        return reached_down, reached_up
    return max(reached_up, reached_down), min(reached_up, reached_down)


def finalize_group(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": stats["records"],
        "horizons": {
            horizon: finalize_horizon(hstats)
            for horizon, hstats in stats["horizons"].items()
        },
    }


def finalize_horizon(hstats: dict[str, Any]) -> dict[str, Any]:
    directional_total = hstats["directional_total"]
    return {
        "records": hstats["records"],
        "real_direction_distribution": dict(sorted(hstats["real_direction"].items())),
        "directional_hit_rate": (
            round(hstats["directional_hits"] / directional_total, 6)
            if directional_total
            else None
        ),
        "directional_total": directional_total,
        "avg_future_return_pips": rounded_mean(hstats["future_return_pips"]),
        "avg_favorable_pips": rounded_mean(hstats["favorable_pips"]),
        "avg_adverse_pips": rounded_mean(hstats["adverse_pips"]),
        "avg_mfe": rounded_mean(hstats["mfe"]),
        "avg_mae": rounded_mean(hstats["mae"]),
        "median_return_pips": percentile(hstats["future_return_pips"], 0.50),
        "p25_return_pips": percentile(hstats["future_return_pips"], 0.25),
        "p75_return_pips": percentile(hstats["future_return_pips"], 0.75),
    }


def rounded_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return round((ordered[lower] * (1 - weight)) + (ordered[upper] * weight), 6)


def write_group_csv(path: Path, group_column: str, groups: dict[str, Any]) -> None:
    fieldnames = [
        group_column,
        "group_records",
        "horizon",
        "records",
        "real_direction_distribution",
        "directional_hit_rate",
        "directional_total",
        "avg_future_return_pips",
        "avg_favorable_pips",
        "avg_adverse_pips",
        "avg_mfe",
        "avg_mae",
        "median_return_pips",
        "p25_return_pips",
        "p75_return_pips",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for group, stats in groups.items():
            for horizon in HORIZONS:
                hstats = stats["horizons"][horizon]
                writer.writerow(
                    {
                        group_column: group,
                        "group_records": stats["records"],
                        "horizon": horizon,
                        "records": hstats["records"],
                        "real_direction_distribution": json.dumps(hstats["real_direction_distribution"], sort_keys=True),
                        "directional_hit_rate": hstats["directional_hit_rate"],
                        "directional_total": hstats["directional_total"],
                        "avg_future_return_pips": hstats["avg_future_return_pips"],
                        "avg_favorable_pips": hstats["avg_favorable_pips"],
                        "avg_adverse_pips": hstats["avg_adverse_pips"],
                        "avg_mfe": hstats["avg_mfe"],
                        "avg_mae": hstats["avg_mae"],
                        "median_return_pips": hstats["median_return_pips"],
                        "p25_return_pips": hstats["p25_return_pips"],
                        "p75_return_pips": hstats["p75_return_pips"],
                    }
                )


def markdown_report(analysis: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI Individual Vote Analysis",
        "",
        f"- records_analyzed: {analysis['records_analyzed']}",
        "",
        "## Baltasar",
        group_markdown_table("Baltasar", analysis["baltasar"]),
        "",
        "## Gaspar",
        group_markdown_table("Gaspar", analysis["gaspar"]),
        "",
        "## Baltasar x Gaspar",
        group_markdown_table("Cross", analysis["baltasar_gaspar_cross"]),
    ]
    return "\n".join(lines) + "\n"


def group_markdown_table(label: str, groups: dict[str, Any], horizon: str = "48") -> str:
    lines = [
        f"| {label} | Records | H{horizon} records | Hit rate | Avg return | Avg favorable | Avg adverse | Avg MFE | Avg MAE | Median | P25 | P75 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group, stats in groups.items():
        hstats = stats["horizons"][horizon]
        lines.append(
            f"| {group} | {stats['records']} | {hstats['records']} | {fmt_pct(hstats['directional_hit_rate'])} | "
            f"{fmt_num(hstats['avg_future_return_pips'])} | {fmt_num(hstats['avg_favorable_pips'])} | "
            f"{fmt_num(hstats['avg_adverse_pips'])} | {fmt_num(hstats['avg_mfe'])} | {fmt_num(hstats['avg_mae'])} | "
            f"{fmt_num(hstats['median_return_pips'])} | {fmt_num(hstats['p25_return_pips'])} | {fmt_num(hstats['p75_return_pips'])} |"
        )
    return "\n".join(lines)


def fmt_num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze individual Baltasar and Gaspar vote outcomes.")
    parser.add_argument("run_dir", help="CEO training output run directory.")
    args = parser.parse_args()
    analysis = analyze_individual_votes(args.run_dir)
    write_individual_vote_analysis(args.run_dir, analysis)
    print(
        json.dumps(
            {
                "records_analyzed": analysis["records_analyzed"],
                "outputs": [
                    str(Path(args.run_dir) / "ceo_individual_vote_analysis.json"),
                    str(Path(args.run_dir) / "ceo_individual_vote_analysis.md"),
                    str(Path(args.run_dir) / "baltasar_vote_outcomes.csv"),
                    str(Path(args.run_dir) / "gaspar_quality_outcomes.csv"),
                    str(Path(args.run_dir) / "baltasar_gaspar_cross_outcomes.csv"),
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
