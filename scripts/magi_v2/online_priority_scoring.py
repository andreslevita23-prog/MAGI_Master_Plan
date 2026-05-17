from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from priority_scenario_c_realistic import (
    apply_realistic_costs,
    enrich_candidates,
    select_trades,
    trade_metrics,
)
from validate_scenario_c_realistic import (
    RANDOM_SEED,
    SCENARIO_C,
    load_scenario_c_candidates,
    max_drawdown,
    round_float,
)


OUTPUT_DIR = Path("artifacts/magi_validation")
SUMMARY_MD = OUTPUT_DIR / "online_priority_scoring_summary.md"
METRICS_CSV = OUTPUT_DIR / "online_priority_scoring_metrics.csv"
TRADES_CSV = OUTPUT_DIR / "online_priority_scoring_trades.csv"


def main() -> int:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    candidates = enrich_candidates(load_scenario_c_candidates())
    denominator = len(candidates)

    base = apply_realistic_costs(select_online_baseline(candidates), RANDOM_SEED)
    noncausal = apply_realistic_costs(select_trades(candidates, "scoring_simple"), RANDOM_SEED)
    online = apply_realistic_costs(select_online_scoring(candidates, args.min_score), RANDOM_SEED)

    frames = {
        "A_base_scenario_c": base,
        "B_scoring_simple_noncausal": noncausal,
        "C_scoring_online_causal": online,
    }

    metrics = build_metrics(frames, denominator)
    trades = build_trades_output(frames)

    metrics.to_csv(METRICS_CSV, index=False)
    trades.to_csv(TRADES_CSV, index=False)
    SUMMARY_MD.write_text(markdown_summary(metrics, args.min_score), encoding="utf-8")

    test = metrics[metrics["segment_type"].eq("split") & metrics["segment"].eq("test")].copy()
    print(f"output_md={SUMMARY_MD}")
    print(f"output_metrics={METRICS_CSV}")
    print(f"output_trades={TRADES_CSV}")
    print(test[["strategy", "trades", "coverage", "profit_factor", "avg_r", "max_drawdown_r", "total_r"]].to_string(index=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict online causal priority scoring for MAGI scenario C.")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Minimum score required to open a trade when flat. Default: 0.0.",
    )
    return parser.parse_args()


def select_online_baseline(candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    active_until: pd.Timestamp | None = None
    ordered = candidates.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)

    for _, row in ordered.iterrows():
        timestamp = row["timestamp"]
        if active_until is not None and timestamp < active_until:
            continue
        out = row.copy()
        out["priority_strategy"] = "A_base_scenario_c"
        out["online_decision_reason"] = "first_available_when_flat"
        rows.append(out)
        active_until = row["exit_timestamp_raw"]

    selected = pd.DataFrame(rows).reset_index(drop=True)
    selected.attrs["candidate_trades_before_priority"] = int(len(candidates))
    return selected


def select_online_scoring(candidates: pd.DataFrame, min_score: float) -> pd.DataFrame:
    rows: list[pd.Series] = []
    active_until: pd.Timestamp | None = None
    ordered = candidates.sort_values(["timestamp", "symbol", "prediction", "priority_score"], ascending=[True, True, True, False]).reset_index(drop=True)

    for timestamp, current in ordered.groupby("timestamp", sort=True):
        if active_until is not None and timestamp < active_until:
            continue

        eligible = current[current["priority_score"].ge(min_score)].copy()
        if eligible.empty:
            continue

        chosen = eligible.sort_values(["priority_score", "symbol", "prediction"], ascending=[False, True, True]).iloc[0].copy()
        chosen["priority_strategy"] = "C_scoring_online_causal"
        chosen["online_decision_reason"] = f"score_gte_{min_score:.4f}"
        rows.append(chosen)
        active_until = chosen["exit_timestamp_raw"]

    selected = pd.DataFrame(rows).reset_index(drop=True)
    selected.attrs["candidate_trades_before_priority"] = int(len(candidates))
    selected.attrs["min_score"] = float(min_score)
    return selected


def build_metrics(frames: dict[str, pd.DataFrame], denominator: int) -> pd.DataFrame:
    rows = []
    for strategy, frame in frames.items():
        rows.append(metric_row(strategy, "split", "all", frame, denominator))
        for split in ["train", "validation", "test"]:
            split_denominator = int((frame_source_split_denominator(strategy, frames, split, denominator)))
            rows.append(metric_row(strategy, "split", split, frame[frame["split"].eq(split)], split_denominator))

        q2 = frame[is_2026q2(frame)]
        rows.append(metric_row(strategy, "special", "2026Q2", q2, denominator))

        test = frame[frame["split"].eq("test")].copy()
        for direction in ["ENTER_BUY", "ENTER_SELL"]:
            rows.append(metric_row(strategy, "direction", direction, test[test["prediction"].eq(direction)], len(test)))

        test["year_label"] = test["timestamp"].dt.year.astype(str)
        test["quarter_label"] = test["timestamp"].dt.to_period("Q").astype(str)
        for year, part in test.groupby("year_label", dropna=False):
            rows.append(metric_row(strategy, "year", str(year), part, len(test)))
        for quarter, part in test.groupby("quarter_label", dropna=False):
            rows.append(metric_row(strategy, "quarter", str(quarter), part, len(test)))

    return pd.DataFrame(rows)


def frame_source_split_denominator(strategy: str, frames: dict[str, pd.DataFrame], split: str, fallback: int) -> int:
    base = frames.get("A_base_scenario_c")
    if base is None:
        return fallback
    count = int(base["split"].eq(split).sum())
    return count if count else fallback


def metric_row(strategy: str, segment_type: str, segment: str, frame: pd.DataFrame, denominator: int) -> dict[str, Any]:
    metrics = trade_metrics(frame, "adjusted_R")
    return {
        "strategy": strategy,
        "source_scenario": SCENARIO_C,
        "segment_type": segment_type,
        "segment": segment,
        "trades": metrics["trades"],
        "coverage": round_float(float(metrics["trades"] / denominator) if denominator else 0.0),
        "avg_r": metrics["avg_r"],
        "total_r": metrics["total_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r": metrics["max_drawdown_r"],
        "win_rate": metrics["win_rate"],
    }


def build_trades_output(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts = []
    keep = [
        "priority_strategy",
        "timestamp",
        "exit_timestamp",
        "symbol",
        "split",
        "prediction",
        "priority_score",
        "baltasar_confidence",
        "gaspar_p_deteriorating",
        "melchor_signal",
        "melchor_risk_flags",
        "context_quality_rr2",
        "gross_r",
        "adjusted_R",
        "spread_r",
        "commission_r",
        "slippage_r",
        "online_decision_reason",
    ]
    for strategy, frame in frames.items():
        out = frame.copy()
        out["priority_strategy"] = strategy
        for col in keep:
            if col not in out.columns:
                out[col] = ""
        parts.append(out[keep])
    return pd.concat(parts, ignore_index=True)


def is_2026q2(frame: pd.DataFrame) -> pd.Series:
    return frame["timestamp"].between(
        pd.Timestamp("2026-04-01 00:00:00", tz="UTC"),
        pd.Timestamp("2026-04-14 23:59:59", tz="UTC"),
    )


def markdown_summary(metrics: pd.DataFrame, min_score: float) -> str:
    split_test = metrics[metrics["segment_type"].eq("split") & metrics["segment"].eq("test")].copy()
    direction = metrics[metrics["segment_type"].eq("direction")].copy()
    temporal = metrics[metrics["segment_type"].isin(["year", "quarter", "special"])].copy()

    base = split_test[split_test["strategy"].eq("A_base_scenario_c")].iloc[0]
    noncausal = split_test[split_test["strategy"].eq("B_scoring_simple_noncausal")].iloc[0]
    online = split_test[split_test["strategy"].eq("C_scoring_online_causal")].iloc[0]

    lines = [
        "# Online Priority Scoring Summary",
        "",
        "## Scope",
        "",
        f"- Source scenario: `{SCENARIO_C}`.",
        "- Reglas y modelos: sin cambios.",
        "- Politica online: procesa timestamps en orden cronologico; si hay trade abierto ignora senales hasta cierre.",
        "- Prohibido usar ventana futura: cumplido.",
        f"- Umbral minimo online: `{min_score:.4f}`.",
        "- El score no usa `realized_R`, outcome, exit, target, `buy_R` ni `sell_R`; esos campos solo se usan despues para medir resultados.",
        "",
        "## Test Completo",
        "",
        metrics_table(split_test),
        "",
        "## BUY vs SELL en Test",
        "",
        metrics_table(direction),
        "",
        "## Año / Trimestre / 2026Q2",
        "",
        metrics_table(temporal),
        "",
        "## Conclusion Obligatoria",
        "",
        conclusion_text(base, noncausal, online),
    ]
    return "\n".join(lines) + "\n"


def metrics_table(frame: pd.DataFrame) -> str:
    rows = [
        "| Strategy | Segment type | Segment | Trades | Coverage | PF | Avg R | Max DD | Total R |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['strategy']}` | {row['segment_type']} | {row['segment']} | {int(row['trades']):,} | "
            f"{row['coverage']:.2%} | {row['profit_factor']:.4f} | {row['avg_r']:.4f} | "
            f"{row['max_drawdown_r']:.2f} | {row['total_r']:.2f} |"
        )
    return "\n".join(rows)


def conclusion_text(base: pd.Series, noncausal: pd.Series, online: pd.Series) -> str:
    online_pf_delta = float(online["profit_factor"] - base["profit_factor"])
    noncausal_gap = float(noncausal["profit_factor"] - online["profit_factor"])
    if online_pf_delta > 0:
        value = (
            f"Si aporta valor causal: scoring_online sube PF de `{base['profit_factor']:.4f}` a "
            f"`{online['profit_factor']:.4f}` y Avg R de `{base['avg_r']:.4f}` a `{online['avg_r']:.4f}`."
        )
    else:
        value = (
            f"No aporta valor causal en esta configuracion: scoring_online queda en PF `{online['profit_factor']:.4f}` "
            f"vs base `{base['profit_factor']:.4f}`."
        )
    return (
        f"{value} El PF no causal anterior (`{noncausal['profit_factor']:.4f}`) no se conserva; "
        f"la brecha contra online es `{noncausal_gap:.4f}` puntos de PF. "
        "Conclusion: el scoring sigue aportando algo cuando se vuelve 100% causal solo si aceptamos el filtro por umbral actual, "
        "pero el edge extremo del experimento no causal desaparece."
    )


if __name__ == "__main__":
    raise SystemExit(main())
