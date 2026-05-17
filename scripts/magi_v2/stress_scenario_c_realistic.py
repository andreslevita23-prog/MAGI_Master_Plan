from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from validate_scenario_c_realistic import (
    RANDOM_SEED,
    SCENARIO_C,
    SL_PIPS,
    load_scenario_c_candidates,
    max_drawdown,
    round_float,
)
from robustness_scenario_c_realistic import select_non_overlapping_trades


OUTPUT_DIR = Path("artifacts/magi_validation")
SUMMARY_CSV = OUTPUT_DIR / "scenario_c_stress_summary.csv"
SUMMARY_MD = OUTPUT_DIR / "scenario_c_stress_summary.md"


STRESS_SCENARIOS = [
    {
        "scenario_id": "base",
        "label": "Comision base / slippage base",
        "commission_pips": 0.70,
        "slippage_min_r": 0.10,
        "slippage_max_r": 0.30,
        "spread_multiplier": 1.0,
    },
    {
        "scenario_id": "high_commission_slippage",
        "label": "Comision alta / slippage alto",
        "commission_pips": 1.00,
        "slippage_min_r": 0.20,
        "slippage_max_r": 0.40,
        "spread_multiplier": 1.0,
    },
    {
        "scenario_id": "extreme_commission_slippage",
        "label": "Comision extrema / slippage extremo",
        "commission_pips": 1.50,
        "slippage_min_r": 0.30,
        "slippage_max_r": 0.50,
        "spread_multiplier": 1.0,
    },
    {
        "scenario_id": "spread_x1_5",
        "label": "Spread x1.5",
        "commission_pips": 0.70,
        "slippage_min_r": 0.10,
        "slippage_max_r": 0.30,
        "spread_multiplier": 1.5,
    },
    {
        "scenario_id": "spread_x2_0",
        "label": "Spread x2.0",
        "commission_pips": 0.70,
        "slippage_min_r": 0.10,
        "slippage_max_r": 0.30,
        "spread_multiplier": 2.0,
    },
]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = load_scenario_c_candidates()
    executable = select_non_overlapping_trades(candidates)

    rows = []
    for index, config in enumerate(STRESS_SCENARIOS, start=1):
        executed = apply_stress_execution(executable, config, RANDOM_SEED + 1000 + index)
        test = executed[executed["split"].eq("test")].copy()
        metrics = trade_metrics(test, "adjusted_R")
        rows.append(
            {
                "scenario_id": config["scenario_id"],
                "label": config["label"],
                "source_scenario": SCENARIO_C,
                "split": "test",
                "commission_pips": config["commission_pips"],
                "slippage_min_r": config["slippage_min_r"],
                "slippage_max_r": config["slippage_max_r"],
                "spread_multiplier": config["spread_multiplier"],
                "trades": metrics["trades"],
                "avg_r": metrics["avg_r"],
                "total_r": metrics["total_r"],
                "profit_factor": metrics["profit_factor"],
                "max_drawdown_r": metrics["max_drawdown_r"],
                "win_rate": metrics["win_rate"],
                "pf_gt_1": bool(metrics["profit_factor"] > 1.0),
                "avg_r_gt_0": bool(metrics["avg_r"] > 0.0),
                "candidate_trades_before_no_overlap": int(executable.attrs["candidate_trades_before_no_overlap"]),
                "skipped_by_no_overlap": int(executable.attrs["skipped_by_no_overlap"]),
            }
        )

    summary = pd.DataFrame(rows)
    summary.to_csv(SUMMARY_CSV, index=False)
    SUMMARY_MD.write_text(markdown_summary(summary), encoding="utf-8")

    print(f"output_csv={SUMMARY_CSV}")
    print(f"output_md={SUMMARY_MD}")
    print(summary[["scenario_id", "profit_factor", "avg_r", "max_drawdown_r", "total_r", "trades", "pf_gt_1"]].to_string(index=False))
    return 0


def apply_stress_execution(executable: pd.DataFrame, config: dict[str, float | str], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = executable.copy()
    spread_pips = pd.to_numeric(out["spread_pips"], errors="coerce").fillna(1.0)
    out["spread_r"] = spread_pips * float(config["spread_multiplier"]) / SL_PIPS
    out["commission_r"] = float(config["commission_pips"]) / SL_PIPS
    out["slippage_r"] = rng.uniform(float(config["slippage_min_r"]), float(config["slippage_max_r"]), size=len(out))
    out["adjusted_R"] = (
        pd.to_numeric(out["gross_r"], errors="coerce").fillna(0.0)
        - out["spread_r"]
        - out["commission_r"]
        - out["slippage_r"]
    )
    return out


def trade_metrics(frame: pd.DataFrame, column: str) -> dict[str, float | int]:
    r = pd.to_numeric(frame.get(column, pd.Series(dtype=float)), errors="coerce").fillna(0.0)
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


def markdown_summary(summary: pd.DataFrame) -> str:
    lines = [
        "# Scenario C Realistic Severe Stress Test",
        "",
        "## Scope",
        "",
        f"- Source scenario: `{SCENARIO_C}`.",
        "- Reglas y modelos: sin cambios.",
        "- No solapamiento: un solo trade activo global.",
        "- Split reportado: `test`.",
        "",
        "## Resultados",
        "",
        "| Escenario | Comisión pips | Slippage R | Spread mult | Trades | PF | Avg R | Max DD | Total R | PF > 1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['label']} | {row['commission_pips']:.2f} | "
            f"{row['slippage_min_r']:.2f}-{row['slippage_max_r']:.2f} | "
            f"{row['spread_multiplier']:.1f} | {int(row['trades']):,} | "
            f"{row['profit_factor']:.4f} | {row['avg_r']:.4f} | "
            f"{row['max_drawdown_r']:.2f} | {row['total_r']:.2f} | "
            f"{'SI' if row['pf_gt_1'] else 'NO'} |"
        )
    lines.extend(["", "## Conclusión", "", conclusion_text(summary)])
    return "\n".join(lines) + "\n"


def conclusion_text(summary: pd.DataFrame) -> str:
    survived = int(summary["pf_gt_1"].sum())
    total = int(len(summary))
    worst = summary.sort_values("profit_factor", ascending=True).iloc[0]
    if survived == total:
        return (
            "MAGI escenario C sobrevive todos los escenarios severos probados con PF > 1. "
            f"El peor caso fue `{worst['label']}` con PF `{worst['profit_factor']:.4f}` y Avg R `{worst['avg_r']:.4f}`. "
            "El edge luce resistente, aunque el margen se comprime en condiciones extremas."
        )
    if survived >= math.ceil(total * 0.6):
        return (
            f"MAGI escenario C sobrevive {survived}/{total} escenarios. "
            f"El peor caso fue `{worst['label']}` con PF `{worst['profit_factor']:.4f}`. "
            "El edge existe, pero es sensible a condiciones severas y debe tratarse como moderadamente frágil."
        )
    return (
        f"MAGI escenario C solo sobrevive {survived}/{total} escenarios con PF > 1. "
        f"El peor caso fue `{worst['label']}` con PF `{worst['profit_factor']:.4f}`. "
        "El edge luce frágil bajo estrés severo."
    )


if __name__ == "__main__":
    raise SystemExit(main())
