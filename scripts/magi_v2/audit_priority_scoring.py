from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from priority_scenario_c_realistic import (
    PRIORITY_WINDOW_MINUTES,
    apply_realistic_costs,
    enrich_candidates,
    score_candidates,
    select_trades,
    split_frame,
    trade_metrics,
)
from validate_scenario_c_realistic import (
    RANDOM_SEED,
    SCENARIO_C,
    SLIPPAGE_MAX_R,
    SLIPPAGE_MIN_R,
    load_scenario_c_candidates,
    max_drawdown,
    round_float,
)


OUTPUT_DIR = Path("artifacts/magi_validation")
AUDIT_MD = OUTPUT_DIR / "priority_scoring_audit.md"
AUDIT_CSV = OUTPUT_DIR / "priority_scoring_audit.csv"
TEMPORAL_CSV = OUTPUT_DIR / "priority_scoring_temporal_breakdown.csv"
ROBUSTNESS_CSV = OUTPUT_DIR / "priority_scoring_robustness.csv"
RUNS = 50

FORBIDDEN_TERMS = [
    "realized",
    "future",
    "outcome",
    "bars_to_exit",
    "pnl",
    "target",
    "gross_r",
    "adjusted_r",
    "buy_r",
    "sell_r",
    "first_touch",
    "exit",
]

SCORING_COLUMNS = {
    "baltasar_confidence": {
        "origin": "rr2_first_touch_labels snapshot field from Baltasar signal confidence",
        "causal_status": "causal_if_snapshot_generated_pre_trade",
        "used_as": "positive signal strength",
    },
    "gaspar_p_deteriorating": {
        "origin": "integrated trades Gaspar v2.1c probability at timestamp",
        "causal_status": "causal_if_model_uses_prior/current context only",
        "used_as": "negative context risk",
    },
    "melchor_signal": {
        "origin": "rr2_first_touch_labels snapshot field from Melchor risk signal",
        "causal_status": "causal_if_snapshot_generated_pre_trade",
        "used_as": "BLOCK/CAUTION penalty",
    },
    "melchor_risk_flags": {
        "origin": "rr2_first_touch_labels snapshot field from Melchor risk flags",
        "causal_status": "causal_if_snapshot_generated_pre_trade",
        "used_as": "HIGH risk penalty",
    },
    "rolling_unfavorable_rate_50": {
        "origin": "integrated trades rolling operational metric",
        "causal_status": "causal_if shifted before current trade",
        "used_as": "risk penalty",
    },
    "rolling_drawdown_50": {
        "origin": "integrated trades rolling operational metric",
        "causal_status": "causal_if shifted before current trade",
        "used_as": "risk penalty",
    },
    "rolling_pf_50": {
        "origin": "integrated trades rolling operational metric",
        "causal_status": "causal_if shifted before current trade",
        "used_as": "small positive/negative quality adjustment",
    },
    "context_quality_rr2": {
        "origin": "integrated trades context quality label",
        "causal_status": "suspicious_name_rr2_audit_required",
        "used_as": "context bonus/penalty",
    },
    "baltasar_gaspar_alignment": {
        "origin": "rr2_first_touch_labels snapshot alignment field",
        "causal_status": "causal_if_snapshot_generated_pre_trade",
        "used_as": "alignment bonus",
    },
}


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = enrich_candidates(load_scenario_c_candidates())
    selected = {
        strategy: apply_realistic_costs(select_trades(candidates, strategy), RANDOM_SEED)
        for strategy in ["baseline", "heuristic", "scoring_simple"]
    }

    formula_audit = audit_formula_columns(candidates)
    comparison = build_comparison(selected)
    temporal = build_temporal_breakdown(selected)
    robustness = build_robustness(selected["scoring_simple"])
    concentration = build_concentration(selected["scoring_simple"])

    audit_rows = pd.concat(
        [
            formula_audit,
            comparison.assign(table="comparison"),
            concentration.assign(table="concentration"),
        ],
        ignore_index=True,
        sort=False,
    )
    audit_rows.to_csv(AUDIT_CSV, index=False)
    temporal.to_csv(TEMPORAL_CSV, index=False)
    robustness.to_csv(ROBUSTNESS_CSV, index=False)
    AUDIT_MD.write_text(markdown_report(formula_audit, comparison, temporal, robustness, concentration), encoding="utf-8")

    test = comparison[(comparison["split"].eq("test")) & (comparison["strategy"].eq("scoring_simple"))].iloc[0]
    print(f"output_md={AUDIT_MD}")
    print(f"output_csv={AUDIT_CSV}")
    print(f"output_temporal={TEMPORAL_CSV}")
    print(f"output_robustness={ROBUSTNESS_CSV}")
    print(f"scoring_test_pf={test['profit_factor']:.6f}")
    print(f"scoring_test_trades={int(test['trades'])}")
    print(f"robustness_pf_gt_1_pct={robustness.attrs['pf_gt_1_pct']:.2f}")
    return 0


def audit_formula_columns(candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column, meta in SCORING_COLUMNS.items():
        forbidden_hit = any(term in column.lower() for term in FORBIDDEN_TERMS)
        rows.append(
            {
                "table": "formula_columns",
                "column": column,
                "origin": meta["origin"],
                "causal_status": meta["causal_status"],
                "used_as": meta["used_as"],
                "exists": column in candidates.columns,
                "forbidden_name_hit": forbidden_hit,
                "non_null_rate": round_float(float(candidates[column].notna().mean()) if column in candidates.columns else 0.0),
            }
        )
    return pd.DataFrame(rows)


def build_comparison(selected: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy, frame in selected.items():
        for split in ["test", "2026Q2"]:
            part = split_frame(frame, split)
            rows.append(metric_row(strategy, split, "ALL", part))
            for direction in ["ENTER_BUY", "ENTER_SELL"]:
                direction_part = part[part["prediction"].eq(direction)]
                rows.append(metric_row(strategy, split, direction, direction_part))
        for year, part in frame[frame["split"].eq("test")].groupby(frame[frame["split"].eq("test")]["timestamp"].dt.year, dropna=False):
            rows.append(metric_row(strategy, "test_year", str(year), part))
        q = frame[frame["split"].eq("test")].copy()
        q["quarter_label"] = q["timestamp"].dt.to_period("Q").astype(str)
        for quarter, part in q.groupby("quarter_label", dropna=False):
            rows.append(metric_row(strategy, "test_quarter", str(quarter), part))
    return pd.DataFrame(rows)


def build_temporal_breakdown(selected: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for strategy, frame in selected.items():
        test = frame[frame["split"].eq("test")].copy()
        test["year_label"] = test["timestamp"].dt.year.astype(str)
        test["quarter_label"] = test["timestamp"].dt.to_period("Q").astype(str)
        test["month_label"] = test["timestamp"].dt.to_period("M").astype(str)
        for period_type, column in [("year", "year_label"), ("quarter", "quarter_label"), ("month", "month_label")]:
            for period, part in test.groupby(column, dropna=False):
                row = metric_row(strategy, period_type, str(period), part)
                rows.append(row)
        q2 = split_frame(frame, "2026Q2")
        rows.append(metric_row(strategy, "special", "2026Q2", q2))
    return pd.DataFrame(rows)


def metric_row(strategy: str, split: str, segment: str, frame: pd.DataFrame) -> dict[str, Any]:
    metrics = trade_metrics(frame, "adjusted_R")
    return {
        "strategy": strategy,
        "split": split,
        "segment": segment,
        "trades": metrics["trades"],
        "avg_r": metrics["avg_r"],
        "total_r": metrics["total_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r": metrics["max_drawdown_r"],
        "win_rate": metrics["win_rate"],
    }


def build_robustness(scoring_frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base = scoring_frame.copy()
    spread_r = pd.to_numeric(base["spread_r"], errors="coerce").fillna(0.0)
    commission_r = pd.to_numeric(base["commission_r"], errors="coerce").fillna(0.0)
    gross_r = pd.to_numeric(base["gross_r"], errors="coerce").fillna(0.0)
    test_mask = base["split"].eq("test")

    for run_id in range(1, RUNS + 1):
        rng = np.random.default_rng(RANDOM_SEED + 3000 + run_id)
        adjusted = gross_r - spread_r - commission_r - rng.uniform(SLIPPAGE_MIN_R, SLIPPAGE_MAX_R, size=len(base))
        run = base.copy()
        run["adjusted_R"] = adjusted
        metrics = trade_metrics(run[test_mask], "adjusted_R")
        rows.append(
            {
                "run_id": run_id,
                "seed": RANDOM_SEED + 3000 + run_id,
                "strategy": "scoring_simple",
                "split": "test",
                "trades": metrics["trades"],
                "avg_r": metrics["avg_r"],
                "total_r": metrics["total_r"],
                "profit_factor": metrics["profit_factor"],
                "max_drawdown_r": metrics["max_drawdown_r"],
            }
        )

    out = pd.DataFrame(rows)
    out.attrs["pf_mean"] = round_float(float(out["profit_factor"].mean()))
    out.attrs["pf_median"] = round_float(float(out["profit_factor"].median()))
    out.attrs["pf_p05"] = round_float(float(out["profit_factor"].quantile(0.05)))
    out.attrs["pf_p95"] = round_float(float(out["profit_factor"].quantile(0.95)))
    out.attrs["pf_gt_1_pct"] = round_float(float((out["profit_factor"] > 1.0).mean() * 100.0))
    return out


def build_concentration(scoring_frame: pd.DataFrame) -> pd.DataFrame:
    test = scoring_frame[scoring_frame["split"].eq("test")].copy()
    test["date"] = test["timestamp"].dt.date.astype(str)
    test["month"] = test["timestamp"].dt.to_period("M").astype(str)
    rows = []
    rows.extend(concentration_rows(test, "month", "month"))
    rows.extend(concentration_rows(test, "date", "day"))
    rows.extend(concentration_rows(test, "prediction", "direction"))
    rows.extend(concentration_rows(test, "regime", "regime"))
    return pd.DataFrame(rows)


def concentration_rows(frame: pd.DataFrame, column: str, segment_type: str) -> list[dict[str, Any]]:
    rows = []
    total = len(frame)
    grouped = frame.groupby(column, dropna=False).size().sort_values(ascending=False)
    for segment, count in grouped.head(10).items():
        rows.append(
            {
                "segment_type": segment_type,
                "segment": str(segment),
                "trades": int(count),
                "share": round_float(float(count / total) if total else 0.0),
            }
        )
    return rows


def markdown_report(
    formula_audit: pd.DataFrame,
    comparison: pd.DataFrame,
    temporal: pd.DataFrame,
    robustness: pd.DataFrame,
    concentration: pd.DataFrame,
) -> str:
    scoring_test = comparison[(comparison["strategy"].eq("scoring_simple")) & (comparison["split"].eq("test"))]
    lines = [
        "# Priority Scoring Audit",
        "",
        "## Formula Exacta",
        "",
        "```text",
        "score = baltasar_confidence",
        "      - 0.75 * gaspar_p_deteriorating",
        "      - melchor_signal_penalty(BLOCK=0.35, CAUTION=0.18)",
        "      - 0.12 if melchor_risk_flags contains HIGH",
        "      - 0.20 * rolling_unfavorable_rate_50",
        "      - clamp(rolling_drawdown_50 / 100, 0, 0.30)",
        "      + clamp((rolling_pf_50 - 1) * 0.08, -0.10, 0.20)",
        "      + context_quality_bonus(FAVORABLE=0.10, UNFAVORABLE=-0.12)",
        "      + alignment_bonus(ALIGNED=0.08)",
        "```",
        "",
        "No usa `realized_R`, returns futuros, outcome de salida, `bars_to_exit`, PnL, target, `buy_R`, `sell_R`, `first_touch` ni columnas de exit dentro de la formula.",
        "",
        "## Columnas Usadas",
        "",
        formula_table(formula_audit),
        "",
        "## Causalidad",
        "",
        causal_assessment(),
        "",
        "## Comparacion Test y Direccion",
        "",
        comparison_table(comparison[comparison["split"].isin(["test", "2026Q2"])]),
        "",
        "## Temporal Test",
        "",
        comparison_table(temporal[temporal["strategy"].eq("scoring_simple")]),
        "",
        "## Robustness Scoring Simple",
        "",
        robustness_table(robustness),
        "",
        "## Concentracion de los 80 Trades Test",
        "",
        concentration_table(concentration),
        "",
        "## Conclusion Obligatoria",
        "",
        final_conclusion(scoring_test, robustness, concentration),
    ]
    return "\n".join(lines) + "\n"


def formula_table(frame: pd.DataFrame) -> str:
    rows = ["| Columna | Origen | Estado causal | Uso | Forbidden hit |", "| --- | --- | --- | --- | --- |"]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['column']}` | {row['origin']} | {row['causal_status']} | {row['used_as']} | {row['forbidden_name_hit']} |"
        )
    return "\n".join(rows)


def causal_assessment() -> str:
    return (
        "La formula del score no contiene variables futuras directas. Sin embargo, la estrategia `scoring_simple` "
        f"selecciona el mayor score dentro de una ventana de `{PRIORITY_WINDOW_MINUTES}` minutos desde la primera senal disponible. "
        "Eso requiere conocer senales que todavia no existian al inicio de la ventana. Por tanto, la formula es mayormente causal, "
        "pero la politica de seleccion por ventana no es estrictamente causal/live. Ademas, `context_quality_rr2` merece cautela por su nombre: "
        "si fue construido con informacion de resultado RR2, debe excluirse o reemplazarse por contexto puramente observable."
    )


def comparison_table(frame: pd.DataFrame) -> str:
    rows = ["| Strategy | Split | Segment | Trades | PF | Avg R | DD | Total R |", "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['strategy']}` | {row['split']} | {row['segment']} | {int(row['trades']):,} | "
            f"{row['profit_factor']:.4f} | {row['avg_r']:.4f} | {row['max_drawdown_r']:.2f} | {row['total_r']:.2f} |"
        )
    return "\n".join(rows)


def robustness_table(frame: pd.DataFrame) -> str:
    return "\n".join(
        [
            "| Runs | PF mean | PF median | PF P05 | PF P95 | PF > 1 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
            f"| {len(frame)} | {frame.attrs['pf_mean']:.4f} | {frame.attrs['pf_median']:.4f} | "
            f"{frame.attrs['pf_p05']:.4f} | {frame.attrs['pf_p95']:.4f} | {frame.attrs['pf_gt_1_pct']:.2f}% |",
        ]
    )


def concentration_table(frame: pd.DataFrame) -> str:
    rows = ["| Tipo | Segmento | Trades | Share |", "| --- | --- | ---: | ---: |"]
    for _, row in frame.iterrows():
        rows.append(f"| {row['segment_type']} | `{row['segment']}` | {int(row['trades'])} | {row['share']:.2%} |")
    return "\n".join(rows)


def final_conclusion(scoring_test: pd.DataFrame, robustness: pd.DataFrame, concentration: pd.DataFrame) -> str:
    test = scoring_test[scoring_test["segment"].eq("ALL")].iloc[0]
    top_month_share = concentration[concentration["segment_type"].eq("month")]["share"].max()
    top_direction_share = concentration[concentration["segment_type"].eq("direction")]["share"].max()
    return (
        f"`scoring_simple` produjo PF `{test['profit_factor']:.4f}` en test con `{int(test['trades'])}` trades y "
        f"robustness PF P05 `{robustness.attrs['pf_p05']:.4f}`. La formula no usa resultados futuros directos, "
        "pero el resultado NO debe considerarse aun una senal causal y confiable: la seleccion por ventana de 15 minutos mira "
        "senales futuras dentro de la ventana, y eso puede explicar parte importante del PF extremo. "
        f"Tambien hay concentracion: el mes dominante concentra {top_month_share:.2%} y la direccion dominante {top_direction_share:.2%}. "
        "Conclusion: es un resultado experimental prometedor, pero posiblemente sobreajustado/no estrictamente causal hasta rehacerlo "
        "con una politica online que solo compare senales ya disponibles en el instante de decision."
    )


if __name__ == "__main__":
    raise SystemExit(main())
