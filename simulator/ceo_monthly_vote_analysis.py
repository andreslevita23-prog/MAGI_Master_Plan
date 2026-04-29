from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


HORIZONS = ("12", "48", "96", "288")


def analyze_monthly_votes(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    records_path = root / "ceo_training_records.jsonl"
    if not records_path.exists():
        raise FileNotFoundError(f"Missing ceo_training_records.jsonl: {records_path}")

    baltasar = {horizon: new_baltasar_horizon() for horizon in HORIZONS}
    gaspar = {horizon: {"GOOD": 0, "FAIR": 0, "POOR": 0} for horizon in HORIZONS}
    good_cross = {
        horizon: {
            "BUY_GOOD": new_directional_stats(),
            "SELL_GOOD": new_directional_stats(),
            "NEUTRAL_GOOD": new_neutral_stats(),
        }
        for horizon in HORIZONS
    }
    monthly = defaultdict(new_monthly_stats)
    records_analyzed = 0

    with records_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            records_analyzed += 1
            month = str(record.get("timestamp") or "")[:7]
            direction = record["baltasar_vote"].get("direction") or "NEUTRAL"
            quality = record["gaspar_vote"].get("quality") or "POOR"
            if direction not in {"BUY", "SELL", "NEUTRAL"}:
                direction = "NEUTRAL"
            if quality not in {"GOOD", "FAIR", "POOR"}:
                quality = "POOR"

            for horizon, outcome in record.get("future_outcomes", {}).items():
                if horizon not in HORIZONS:
                    continue
                update_baltasar_horizon(baltasar[horizon], direction, outcome)
                gaspar[horizon][quality] += 1
                if quality == "GOOD":
                    update_good_cross(good_cross[horizon], direction, outcome)
                if horizon == "48":
                    update_monthly(monthly[month], direction, quality, outcome)

    monthly_rows = {month: finalize_monthly(stats) for month, stats in sorted(monthly.items())}
    analysis = {
        "schema_version": "ceo_monthly_vote_analysis_v0.1",
        "run_dir": str(root),
        "records_analyzed": records_analyzed,
        "horizons": list(HORIZONS),
        "baltasar_by_horizon": {horizon: finalize_baltasar_horizon(stats) for horizon, stats in baltasar.items()},
        "gaspar_counts_by_horizon": gaspar,
        "gaspar_good_cross_by_horizon": {
            horizon: finalize_good_cross(groups)
            for horizon, groups in good_cross.items()
        },
        "monthly_h48": monthly_rows,
        "homogeneity_h48": homogeneity(monthly_rows),
    }
    return analysis


def write_monthly_analysis(run_dir: str | Path, analysis: dict[str, Any]) -> None:
    root = Path(run_dir)
    (root / "ceo_monthly_vote_analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True), encoding="utf-8")
    write_baltasar_monthly_csv(root / "baltasar_monthly_outcomes.csv", analysis["monthly_h48"])
    write_good_monthly_csv(root / "gaspar_good_monthly_outcomes.csv", analysis["monthly_h48"])
    (root / "ceo_monthly_vote_analysis.md").write_text(markdown_report(analysis), encoding="utf-8")


def new_directional_stats() -> dict[str, Any]:
    return {
        "cases": 0,
        "hits": 0,
        "fails": 0,
        "favorable": [],
        "adverse": [],
        "net": [],
    }


def new_neutral_stats() -> dict[str, Any]:
    return {
        "cases": 0,
        "future_return_pips": [],
        "favorable": [],
        "adverse": [],
    }


def new_baltasar_horizon() -> dict[str, Any]:
    return {
        "BUY": new_directional_stats(),
        "SELL": new_directional_stats(),
        "NEUTRAL": new_neutral_stats(),
    }


def new_monthly_stats() -> dict[str, Any]:
    return {
        "BUY": new_directional_stats(),
        "SELL": new_directional_stats(),
        "BUY_GOOD": new_directional_stats(),
        "SELL_GOOD": new_directional_stats(),
    }


def update_baltasar_horizon(stats: dict[str, Any], direction: str, outcome: dict[str, Any]) -> None:
    if direction in {"BUY", "SELL"}:
        update_directional(stats[direction], direction, outcome)
    else:
        update_neutral(stats["NEUTRAL"], outcome)


def update_good_cross(stats: dict[str, Any], direction: str, outcome: dict[str, Any]) -> None:
    if direction == "BUY":
        update_directional(stats["BUY_GOOD"], direction, outcome)
    elif direction == "SELL":
        update_directional(stats["SELL_GOOD"], direction, outcome)
    else:
        update_neutral(stats["NEUTRAL_GOOD"], outcome)


def update_monthly(stats: dict[str, Any], direction: str, quality: str, outcome: dict[str, Any]) -> None:
    if direction == "BUY":
        update_directional(stats["BUY"], direction, outcome)
        if quality == "GOOD":
            update_directional(stats["BUY_GOOD"], direction, outcome)
    elif direction == "SELL":
        update_directional(stats["SELL"], direction, outcome)
        if quality == "GOOD":
            update_directional(stats["SELL_GOOD"], direction, outcome)


def update_directional(stats: dict[str, Any], direction: str, outcome: dict[str, Any]) -> None:
    stats["cases"] += 1
    real_direction = outcome.get("real_direction")
    if real_direction == direction:
        stats["hits"] += 1
    else:
        stats["fails"] += 1
    favorable, adverse = favorable_adverse(outcome, direction)
    stats["favorable"].append(favorable)
    stats["adverse"].append(adverse)
    stats["net"].append(net_directional_pips(outcome, direction))


def update_neutral(stats: dict[str, Any], outcome: dict[str, Any]) -> None:
    stats["cases"] += 1
    reached_up = float(outcome.get("reached_up_pips") or 0.0)
    reached_down = float(outcome.get("reached_down_pips") or 0.0)
    stats["future_return_pips"].append(float(outcome.get("future_return_pips") or 0.0))
    stats["favorable"].append(max(reached_up, reached_down))
    stats["adverse"].append(min(reached_up, reached_down))


def favorable_adverse(outcome: dict[str, Any], direction: str) -> tuple[float, float]:
    reached_up = float(outcome.get("reached_up_pips") or 0.0)
    reached_down = float(outcome.get("reached_down_pips") or 0.0)
    if direction == "BUY":
        return reached_up, reached_down
    return reached_down, reached_up


def net_directional_pips(outcome: dict[str, Any], direction: str) -> float:
    value = float(outcome.get("future_return_pips") or 0.0)
    return value if direction == "BUY" else -value


def finalize_baltasar_horizon(stats: dict[str, Any]) -> dict[str, Any]:
    buy = finalize_stats(stats["BUY"])
    sell = finalize_stats(stats["SELL"])
    neutral = finalize_neutral(stats["NEUTRAL"])
    return {
        "total_directional": buy["cases"] + sell["cases"],
        "total_buy": buy["cases"],
        "total_sell": sell["cases"],
        "total_neutral": neutral["cases"],
        "buy": buy,
        "sell": sell,
        "neutral": neutral,
    }


def finalize_good_cross(groups: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "BUY_GOOD": finalize_stats(groups["BUY_GOOD"]),
        "SELL_GOOD": finalize_stats(groups["SELL_GOOD"]),
        "NEUTRAL_GOOD": finalize_neutral(groups["NEUTRAL_GOOD"]),
    }


def finalize_stats(stats: dict[str, Any]) -> dict[str, Any]:
    cases = stats["cases"]
    return {
        "cases": cases,
        "hits": stats["hits"],
        "fails": stats["fails"],
        "hit_rate": round(stats["hits"] / cases, 6) if cases else None,
        "fail_rate": round(stats["fails"] / cases, 6) if cases else None,
        "avg_favorable_pips": mean(stats["favorable"]),
        "avg_adverse_pips": mean(stats["adverse"]),
        "avg_net_directional_pips": mean(stats["net"]),
        "median_net_directional_pips": percentile(stats["net"], 0.5),
        "p25_net_directional_pips": percentile(stats["net"], 0.25),
        "p75_net_directional_pips": percentile(stats["net"], 0.75),
        "net_sum": round(sum(stats["net"]), 6),
    }


def finalize_neutral(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "cases": stats["cases"],
        "avg_future_return_pips": mean(stats["future_return_pips"]),
        "avg_favorable_pips": mean(stats["favorable"]),
        "avg_adverse_pips": mean(stats["adverse"]),
        "median_future_return_pips": percentile(stats["future_return_pips"], 0.5),
        "p25_future_return_pips": percentile(stats["future_return_pips"], 0.25),
        "p75_future_return_pips": percentile(stats["future_return_pips"], 0.75),
    }


def finalize_monthly(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "buy": finalize_stats(stats["BUY"]),
        "sell": finalize_stats(stats["SELL"]),
        "buy_good": finalize_stats(stats["BUY_GOOD"]),
        "sell_good": finalize_stats(stats["SELL_GOOD"]),
    }


def homogeneity(monthly_rows: dict[str, Any]) -> dict[str, Any]:
    return {
        key: homogeneity_for_key(monthly_rows, key)
        for key in ("buy", "sell", "buy_good", "sell_good")
    }


def homogeneity_for_key(monthly_rows: dict[str, Any], key: str) -> dict[str, Any]:
    values = {
        month: row[key]["avg_net_directional_pips"]
        for month, row in monthly_rows.items()
        if row[key]["avg_net_directional_pips"] is not None
    }
    sums = {
        month: row[key]["net_sum"]
        for month, row in monthly_rows.items()
        if row[key]["cases"] > 0
    }
    if not values:
        return {
            "monthly_mean": None,
            "monthly_std": None,
            "best_month": None,
            "worst_month": None,
            "positive_months": 0,
            "negative_months": 0,
            "best_month_total_concentration": None,
        }
    best_month = max(values, key=values.get)
    worst_month = min(values, key=values.get)
    total_net = sum(sums.values())
    best_sum_month = max(sums, key=sums.get) if sums else None
    return {
        "monthly_mean": mean(list(values.values())),
        "monthly_std": stdev(list(values.values())),
        "best_month": {"month": best_month, "avg_net_directional_pips": values[best_month], "net_sum": sums.get(best_month)},
        "worst_month": {"month": worst_month, "avg_net_directional_pips": values[worst_month], "net_sum": sums.get(worst_month)},
        "positive_months": sum(1 for item in values.values() if item > 0),
        "negative_months": sum(1 for item in values.values() if item < 0),
        "best_month_total_concentration": (
            round(sums[best_sum_month] / total_net, 6)
            if best_sum_month and total_net
            else None
        ),
        "best_total_month": {"month": best_sum_month, "net_sum": sums.get(best_sum_month)} if best_sum_month else None,
    }


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return 0.0 if values else None
    avg = sum(values) / len(values)
    return round(math.sqrt(sum((item - avg) ** 2 for item in values) / (len(values) - 1)), 6)


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


def write_baltasar_monthly_csv(path: Path, monthly_rows: dict[str, Any]) -> None:
    fieldnames = [
        "month",
        "buy_cases",
        "buy_hit_rate",
        "buy_fail_rate",
        "buy_avg_net_pips",
        "sell_cases",
        "sell_hit_rate",
        "sell_fail_rate",
        "sell_avg_net_pips",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for month, row in monthly_rows.items():
            writer.writerow(
                {
                    "month": month,
                    "buy_cases": row["buy"]["cases"],
                    "buy_hit_rate": row["buy"]["hit_rate"],
                    "buy_fail_rate": row["buy"]["fail_rate"],
                    "buy_avg_net_pips": row["buy"]["avg_net_directional_pips"],
                    "sell_cases": row["sell"]["cases"],
                    "sell_hit_rate": row["sell"]["hit_rate"],
                    "sell_fail_rate": row["sell"]["fail_rate"],
                    "sell_avg_net_pips": row["sell"]["avg_net_directional_pips"],
                }
            )


def write_good_monthly_csv(path: Path, monthly_rows: dict[str, Any]) -> None:
    fieldnames = [
        "month",
        "buy_good_cases",
        "buy_good_hit_rate",
        "buy_good_fail_rate",
        "buy_good_avg_net_pips",
        "sell_good_cases",
        "sell_good_hit_rate",
        "sell_good_fail_rate",
        "sell_good_avg_net_pips",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for month, row in monthly_rows.items():
            writer.writerow(
                {
                    "month": month,
                    "buy_good_cases": row["buy_good"]["cases"],
                    "buy_good_hit_rate": row["buy_good"]["hit_rate"],
                    "buy_good_fail_rate": row["buy_good"]["fail_rate"],
                    "buy_good_avg_net_pips": row["buy_good"]["avg_net_directional_pips"],
                    "sell_good_cases": row["sell_good"]["cases"],
                    "sell_good_hit_rate": row["sell_good"]["hit_rate"],
                    "sell_good_fail_rate": row["sell_good"]["fail_rate"],
                    "sell_good_avg_net_pips": row["sell_good"]["avg_net_directional_pips"],
                }
            )


def markdown_report(analysis: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI Monthly Vote Analysis",
        "",
        f"- records_analyzed: {analysis['records_analyzed']}",
        "",
        "## Baltasar H48",
        baltasar_horizon_table(analysis["baltasar_by_horizon"]["48"]),
        "",
        "## Gaspar Counts H48",
        gaspar_counts_table(analysis["gaspar_counts_by_horizon"]["48"]),
        "",
        "## Gaspar GOOD x Baltasar H48",
        good_cross_table(analysis["gaspar_good_cross_by_horizon"]["48"]),
        "",
        "## Monthly H48",
        monthly_table(analysis["monthly_h48"]),
        "",
        "## Homogeneity H48",
        homogeneity_table(analysis["homogeneity_h48"]),
    ]
    return "\n".join(lines) + "\n"


def baltasar_horizon_table(row: dict[str, Any]) -> str:
    return "\n".join(
        [
            "| Metric | BUY | SELL | NEUTRAL |",
            "|---|---:|---:|---:|",
            f"| cases | {row['buy']['cases']} | {row['sell']['cases']} | {row['neutral']['cases']} |",
            f"| hit_rate | {fmt_pct(row['buy']['hit_rate'])} | {fmt_pct(row['sell']['hit_rate'])} | n/a |",
            f"| fail_rate | {fmt_pct(row['buy']['fail_rate'])} | {fmt_pct(row['sell']['fail_rate'])} | n/a |",
            f"| avg_favorable_pips | {fmt(row['buy']['avg_favorable_pips'])} | {fmt(row['sell']['avg_favorable_pips'])} | {fmt(row['neutral']['avg_favorable_pips'])} |",
            f"| avg_adverse_pips | {fmt(row['buy']['avg_adverse_pips'])} | {fmt(row['sell']['avg_adverse_pips'])} | {fmt(row['neutral']['avg_adverse_pips'])} |",
            f"| avg_net_directional_pips | {fmt(row['buy']['avg_net_directional_pips'])} | {fmt(row['sell']['avg_net_directional_pips'])} | n/a |",
        ]
    )


def gaspar_counts_table(row: dict[str, int]) -> str:
    return "\n".join(["| GOOD | FAIR | POOR |", "|---:|---:|---:|", f"| {row['GOOD']} | {row['FAIR']} | {row['POOR']} |"])


def good_cross_table(row: dict[str, Any]) -> str:
    lines = ["| Group | Cases | Hit | Fail | Avg favorable | Avg adverse | Avg net | Median | P25 | P75 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key in ("BUY_GOOD", "SELL_GOOD"):
        item = row[key]
        lines.append(
            f"| {key} | {item['cases']} | {fmt_pct(item['hit_rate'])} | {fmt_pct(item['fail_rate'])} | "
            f"{fmt(item['avg_favorable_pips'])} | {fmt(item['avg_adverse_pips'])} | {fmt(item['avg_net_directional_pips'])} | "
            f"{fmt(item['median_net_directional_pips'])} | {fmt(item['p25_net_directional_pips'])} | {fmt(item['p75_net_directional_pips'])} |"
        )
    neutral = row["NEUTRAL_GOOD"]
    lines.append(f"| NEUTRAL_GOOD | {neutral['cases']} | n/a | n/a | {fmt(neutral['avg_favorable_pips'])} | {fmt(neutral['avg_adverse_pips'])} | n/a | n/a | n/a | n/a |")
    return "\n".join(lines)


def monthly_table(rows: dict[str, Any]) -> str:
    lines = ["| Month | BUY | BUY hit | BUY net | SELL | SELL hit | SELL net | BUY+GOOD | BUY+GOOD hit | BUY+GOOD net | SELL+GOOD | SELL+GOOD hit | SELL+GOOD net |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for month, row in rows.items():
        lines.append(
            f"| {month} | {row['buy']['cases']} | {fmt_pct(row['buy']['hit_rate'])} | {fmt(row['buy']['avg_net_directional_pips'])} | "
            f"{row['sell']['cases']} | {fmt_pct(row['sell']['hit_rate'])} | {fmt(row['sell']['avg_net_directional_pips'])} | "
            f"{row['buy_good']['cases']} | {fmt_pct(row['buy_good']['hit_rate'])} | {fmt(row['buy_good']['avg_net_directional_pips'])} | "
            f"{row['sell_good']['cases']} | {fmt_pct(row['sell_good']['hit_rate'])} | {fmt(row['sell_good']['avg_net_directional_pips'])} |"
        )
    return "\n".join(lines)


def homogeneity_table(rows: dict[str, Any]) -> str:
    lines = ["| Series | Monthly mean | Std | Best month | Worst month | Positive months | Negative months | Best total concentration |", "|---|---:|---:|---|---|---:|---:|---:|"]
    for key, row in rows.items():
        best = row["best_month"]
        worst = row["worst_month"]
        lines.append(
            f"| {key} | {fmt(row['monthly_mean'])} | {fmt(row['monthly_std'])} | "
            f"{best['month'] if best else 'n/a'} ({fmt(best['avg_net_directional_pips']) if best else 'n/a'}) | "
            f"{worst['month'] if worst else 'n/a'} ({fmt(worst['avg_net_directional_pips']) if worst else 'n/a'}) | "
            f"{row['positive_months']} | {row['negative_months']} | {fmt_pct(row['best_month_total_concentration'])} |"
        )
    return "\n".join(lines)


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze monthly and directional CEO vote outcomes.")
    parser.add_argument("run_dir", help="CEO training output run directory.")
    args = parser.parse_args()
    analysis = analyze_monthly_votes(args.run_dir)
    write_monthly_analysis(args.run_dir, analysis)
    print(json.dumps({"records_analyzed": analysis["records_analyzed"], "outputs": [
        str(Path(args.run_dir) / "ceo_monthly_vote_analysis.json"),
        str(Path(args.run_dir) / "ceo_monthly_vote_analysis.md"),
        str(Path(args.run_dir) / "baltasar_monthly_outcomes.csv"),
        str(Path(args.run_dir) / "gaspar_good_monthly_outcomes.csv"),
    ]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
