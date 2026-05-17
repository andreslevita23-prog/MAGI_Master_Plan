from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sweep_online_priority_threshold import select_online_scoring_fast
from priority_scenario_c_realistic import enrich_candidates
from validate_scenario_c_realistic import RANDOM_SEED, SCENARIO_C, SL_PIPS, load_scenario_c_candidates, max_drawdown, round_float


OUTPUT_DIR = Path("artifacts/magi_validation")
SUMMARY_MD = OUTPUT_DIR / "online_priority_cost_validation.md"
SUMMARY_CSV = OUTPUT_DIR / "online_priority_cost_validation.csv"
TEMPORAL_CSV = OUTPUT_DIR / "online_priority_cost_temporal.csv"
DIRECTION_CSV = OUTPUT_DIR / "online_priority_cost_direction_breakdown.csv"

MIN_SCORE = 0.20

COST_SCENARIOS = [
    {
        "scenario_id": "low_costs",
        "label": "Costos bajos",
        "spread_multiplier": 0.50,
        "commission_pips": 0.35,
        "slippage_min_r": 0.00,
        "slippage_max_r": 0.10,
    },
    {
        "scenario_id": "medium_costs",
        "label": "Costos medios",
        "spread_multiplier": 1.00,
        "commission_pips": 0.70,
        "slippage_min_r": 0.10,
        "slippage_max_r": 0.30,
    },
    {
        "scenario_id": "high_costs_stress",
        "label": "Costos altos / stress",
        "spread_multiplier": 2.00,
        "commission_pips": 0.70,
        "slippage_min_r": 0.30,
        "slippage_max_r": 0.50,
    },
]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = enrich_candidates(load_scenario_c_candidates())

    base_c = select_base_online(candidates)
    score_000 = select_online_scoring_fast(candidates, 0.00)
    score_020 = select_online_scoring_fast(candidates, MIN_SCORE)

    summary_rows = []
    temporal_rows = []
    direction_rows = []

    comparison_frames = {
        "comparison_base_c_no_costs": base_c,
        "comparison_score_0_00_no_costs": score_000,
        "comparison_score_0_20_no_costs": score_020,
    }
    for scenario_id, frame in comparison_frames.items():
        evaluated = apply_costs(frame, scenario_id, scenario_id, 1.0, 0.0, 0.0, 0.0, adjusted=False)
        append_all(summary_rows, temporal_rows, direction_rows, evaluated, scenario_id, scenario_id)

    for idx, config in enumerate(COST_SCENARIOS, start=1):
        evaluated = apply_costs(
            score_020,
            str(config["scenario_id"]),
            str(config["label"]),
            float(config["spread_multiplier"]),
            float(config["commission_pips"]),
            float(config["slippage_min_r"]),
            float(config["slippage_max_r"]),
            seed=RANDOM_SEED + 5000 + idx,
            adjusted=True,
        )
        append_all(summary_rows, temporal_rows, direction_rows, evaluated, str(config["scenario_id"]), str(config["label"]))

    summary = pd.DataFrame(summary_rows)
    temporal = pd.DataFrame(temporal_rows)
    direction = pd.DataFrame(direction_rows)

    summary.to_csv(SUMMARY_CSV, index=False)
    temporal.to_csv(TEMPORAL_CSV, index=False)
    direction.to_csv(DIRECTION_CSV, index=False)
    SUMMARY_MD.write_text(markdown_summary(summary, temporal, direction), encoding="utf-8")

    print(f"output_md={SUMMARY_MD}")
    print(f"output_summary={SUMMARY_CSV}")
    print(f"output_temporal={TEMPORAL_CSV}")
    print(f"output_direction={DIRECTION_CSV}")
    print(summary.to_string(index=False))
    return 0


def select_base_online(candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    active_until: pd.Timestamp | None = None
    ordered = candidates.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)
    for _, row in ordered.iterrows():
        if active_until is not None and row["timestamp"] < active_until:
            continue
        rows.append(row.copy())
        active_until = row["exit_timestamp_raw"]
    return pd.DataFrame(rows).reset_index(drop=True)


def apply_costs(
    frame: pd.DataFrame,
    scenario_id: str,
    label: str,
    spread_multiplier: float,
    commission_pips: float,
    slippage_min_r: float,
    slippage_max_r: float,
    seed: int = RANDOM_SEED,
    adjusted: bool = True,
) -> pd.DataFrame:
    out = frame.copy()
    rng = np.random.default_rng(seed)
    spread_r = pd.to_numeric(out["spread_pips"], errors="coerce").fillna(1.0) * spread_multiplier / SL_PIPS
    commission_r = commission_pips / SL_PIPS
    slippage_r = rng.uniform(slippage_min_r, slippage_max_r, size=len(out)) if adjusted else np.zeros(len(out))
    out["cost_scenario"] = scenario_id
    out["cost_label"] = label
    out["spread_multiplier"] = spread_multiplier
    out["commission_pips"] = commission_pips
    out["slippage_min_r"] = slippage_min_r
    out["slippage_max_r"] = slippage_max_r
    out["spread_r"] = spread_r if adjusted else 0.0
    out["commission_r"] = commission_r if adjusted else 0.0
    out["slippage_r"] = slippage_r
    out["adjusted_R"] = pd.to_numeric(out["gross_r"], errors="coerce").fillna(0.0) - out["spread_r"] - out["commission_r"] - out["slippage_r"]
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["year"] = out["timestamp"].dt.year.astype(str)
    out["quarter"] = out["timestamp"].dt.to_period("Q").astype(str)
    out["is_2026q2"] = out["timestamp"].between(pd.Timestamp("2026-04-01 00:00:00", tz="UTC"), pd.Timestamp("2026-04-14 23:59:59", tz="UTC"))
    return out


def append_all(
    summary_rows: list[dict[str, Any]],
    temporal_rows: list[dict[str, Any]],
    direction_rows: list[dict[str, Any]],
    frame: pd.DataFrame,
    scenario_id: str,
    label: str,
) -> None:
    test = frame[frame["split"].eq("test")].copy()
    summary_rows.append(metric_row(scenario_id, label, "test", "ALL", test, len(test)))
    q2 = frame[frame["is_2026q2"]].copy()
    summary_rows.append(metric_row(scenario_id, label, "special", "2026Q2", q2, len(test)))

    for direction in ["ENTER_BUY", "ENTER_SELL"]:
        part = test[test["prediction"].eq(direction)]
        direction_rows.append(metric_row(scenario_id, label, "direction", direction, part, len(test)))

    for year, part in test.groupby("year", dropna=False):
        temporal_rows.append(metric_row(scenario_id, label, "year", str(year), part, len(test)))
    for quarter, part in test.groupby("quarter", dropna=False):
        temporal_rows.append(metric_row(scenario_id, label, "quarter", str(quarter), part, len(test)))
    temporal_rows.append(metric_row(scenario_id, label, "special", "2026Q2", q2, len(test)))


def metric_row(scenario_id: str, label: str, segment_type: str, segment: str, frame: pd.DataFrame, denominator: int) -> dict[str, Any]:
    metrics = trade_metrics(frame)
    return {
        "cost_scenario": scenario_id,
        "label": label,
        "source_scenario": SCENARIO_C,
        "min_score": MIN_SCORE if "0_20" in scenario_id or scenario_id in {c["scenario_id"] for c in COST_SCENARIOS} else (0.0 if "0_00" in scenario_id else None),
        "segment_type": segment_type,
        "segment": segment,
        "trades": metrics["trades"],
        "coverage": round_float(float(metrics["trades"] / denominator) if denominator else 0.0),
        "profit_factor": metrics["profit_factor"],
        "avg_r": metrics["avg_r"],
        "max_drawdown_r": metrics["max_drawdown_r"],
        "total_r": metrics["total_r"],
        "win_rate": metrics["win_rate"],
    }


def trade_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    r = pd.to_numeric(frame.get("adjusted_R", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    trades = int(len(r))
    wins = r[r > 0]
    losses = r[r < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (math.inf if gross_profit > 0 else 0.0)
    return {
        "trades": trades,
        "avg_r": round_float(float(r.mean()) if trades else 0.0),
        "total_r": round_float(float(r.sum())),
        "profit_factor": round_float(pf),
        "max_drawdown_r": round_float(max_drawdown(r)),
        "win_rate": round_float(float((r > 0).mean()) if trades else 0.0),
    }


def markdown_summary(summary: pd.DataFrame, temporal: pd.DataFrame, direction: pd.DataFrame) -> str:
    test = summary[summary["segment"].eq("ALL")].copy()
    q2 = summary[summary["segment"].eq("2026Q2")].copy()
    lines = [
        "# Online Priority Cost Validation",
        "",
        "## Scope",
        "",
        f"- Source scenario: `{SCENARIO_C}`.",
        f"- Policy: scoring online causal with min_score `{MIN_SCORE:.2f}` for cost scenarios.",
        "- Formula de score sin cambios.",
        "- Sin entrenamiento de modelos.",
        "- Comparisons marked `no_costs` use gross R with no spread, commission or slippage deduction.",
        "",
        "## Test Summary",
        "",
        table(test),
        "",
        "## 2026Q2",
        "",
        table(q2),
        "",
        "## BUY vs SELL",
        "",
        table(direction),
        "",
        "## Temporal",
        "",
        table(temporal),
        "",
        "## Conclusion Obligatoria",
        "",
        conclusion_text(summary),
    ]
    return "\n".join(lines) + "\n"


def table(frame: pd.DataFrame) -> str:
    rows = [
        "| Scenario | Segment type | Segment | Trades | Coverage | PF | Avg R | DD | Total R | Win rate |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['cost_scenario']}` | {row['segment_type']} | {row['segment']} | {int(row['trades']):,} | "
            f"{row['coverage']:.2%} | {row['profit_factor']:.4f} | {row['avg_r']:.4f} | "
            f"{row['max_drawdown_r']:.2f} | {row['total_r']:.2f} | {row['win_rate']:.2%} |"
        )
    return "\n".join(rows)


def conclusion_text(summary: pd.DataFrame) -> str:
    test = summary[summary["segment"].eq("ALL")].set_index("cost_scenario")
    medium = test.loc["medium_costs"]
    high = test.loc["high_costs_stress"]
    no_cost = test.loc["comparison_score_0_20_no_costs"]
    if medium["profit_factor"] > 1 and medium["avg_r"] > 0 and high["profit_factor"] > 1:
        verdict = "sigue siendo candidato operativo incluso bajo stress alto"
    elif medium["profit_factor"] > 1 and medium["avg_r"] > 0:
        verdict = "sigue siendo candidato operativo bajo costos realistas, pero queda sensible al stress alto"
    else:
        verdict = "no sostiene suficiente edge bajo costos realistas"
    return (
        f"min_score 0.20 sin costos tiene PF `{no_cost['profit_factor']:.4f}` y Avg R `{no_cost['avg_r']:.4f}`. "
        f"Con costos medios queda en PF `{medium['profit_factor']:.4f}`, Avg R `{medium['avg_r']:.4f}`, "
        f"Total R `{medium['total_r']:.2f}`. Bajo stress alto queda en PF `{high['profit_factor']:.4f}`, "
        f"Avg R `{high['avg_r']:.4f}`, Total R `{high['total_r']:.2f}`. "
        f"Conclusion: min_score 0.20 {verdict}. No es regla final; requiere paper/live y stress adicional por liquidez."
    )


if __name__ == "__main__":
    raise SystemExit(main())
