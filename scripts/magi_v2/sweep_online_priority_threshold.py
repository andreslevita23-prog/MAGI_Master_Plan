from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from priority_scenario_c_realistic import apply_realistic_costs, enrich_candidates, trade_metrics
from validate_scenario_c_realistic import RANDOM_SEED, SCENARIO_C, load_scenario_c_candidates, round_float


OUTPUT_DIR = Path("artifacts/magi_validation")
REFERENCE_TRADES = OUTPUT_DIR / "online_priority_scoring_trades.csv"
SUMMARY_MD = OUTPUT_DIR / "online_priority_threshold_sweep.md"
SUMMARY_CSV = OUTPUT_DIR / "online_priority_threshold_sweep.csv"
TEMPORAL_CSV = OUTPUT_DIR / "online_priority_threshold_temporal.csv"

THRESHOLDS = [0.00, 0.10, 0.20, 0.30, 0.35, 0.40, 0.45, 0.50]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reference = load_reference()
    candidates = enrich_candidates(load_scenario_c_candidates())

    frames = {}
    for threshold in THRESHOLDS:
        selected = select_online_scoring_fast(candidates, threshold)
        frames[threshold] = apply_realistic_costs(selected, RANDOM_SEED)

    baseline_test_trades = len(frames[0.0][frames[0.0]["split"].eq("test")])
    summary = build_summary(frames, baseline_test_trades)
    temporal = build_temporal(frames)

    summary.to_csv(SUMMARY_CSV, index=False)
    temporal.to_csv(TEMPORAL_CSV, index=False)
    SUMMARY_MD.write_text(markdown_summary(summary, temporal, reference), encoding="utf-8")

    print(f"output_md={SUMMARY_MD}")
    print(f"output_csv={SUMMARY_CSV}")
    print(f"output_temporal={TEMPORAL_CSV}")
    print(summary.to_string(index=False))
    return 0


def select_online_scoring_fast(candidates: pd.DataFrame, min_score: float) -> pd.DataFrame:
    ordered = candidates.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)
    ts = pd.to_datetime(ordered["timestamp"], utc=True, errors="coerce")
    ts_ns = ts.astype("int64").to_numpy()
    exit_ns = pd.to_datetime(ordered["exit_timestamp_raw"], utc=True, errors="coerce").astype("int64").to_numpy()
    scores = pd.to_numeric(ordered["priority_score"], errors="coerce").fillna(float("-inf")).to_numpy()
    change_points = np.flatnonzero(np.diff(ts_ns) != 0) + 1
    starts = np.r_[0, change_points]
    ends = np.r_[change_points, len(ordered)]

    selected_indices: list[int] = []
    group_pos = 0
    while group_pos < len(starts):
        start = int(starts[group_pos])
        end = int(ends[group_pos])
        group_scores = scores[start:end]
        eligible = group_scores >= min_score
        if eligible.any():
            local_positions = np.where(eligible)[0]
            best_local = int(local_positions[np.argmax(group_scores[local_positions])])
            best_idx = start + best_local
            selected_indices.append(best_idx)
            next_i = int(np.searchsorted(ts_ns, exit_ns[best_idx], side="left"))
            group_pos = int(np.searchsorted(starts, next_i, side="left"))
        else:
            group_pos += 1

    selected = ordered.iloc[selected_indices].copy().reset_index(drop=True)
    selected["priority_strategy"] = "C_scoring_online_causal"
    selected["online_decision_reason"] = f"score_gte_{min_score:.4f}"
    selected.attrs["candidate_trades_before_priority"] = int(len(candidates))
    selected.attrs["min_score"] = float(min_score)
    return selected


def load_reference() -> pd.DataFrame:
    if not REFERENCE_TRADES.exists():
        raise FileNotFoundError(f"Missing reference trades: {REFERENCE_TRADES}")
    ref = pd.read_csv(REFERENCE_TRADES)
    return ref[ref["priority_strategy"].eq("C_scoring_online_causal")].copy()


def build_summary(frames: dict[float, pd.DataFrame], baseline_test_trades: int) -> pd.DataFrame:
    rows = []
    for threshold, frame in frames.items():
        test = frame[frame["split"].eq("test")].copy()
        row = metric_row(threshold, "test", "ALL", test, baseline_test_trades)
        q2 = frame[is_2026q2(frame)]
        q2_metrics = trade_metrics(q2, "adjusted_R")
        row.update(
            {
                "q2_trades": q2_metrics["trades"],
                "q2_profit_factor": q2_metrics["profit_factor"],
                "q2_avg_r": q2_metrics["avg_r"],
                "q2_total_r": q2_metrics["total_r"],
                "q2_max_drawdown_r": q2_metrics["max_drawdown_r"],
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_temporal(frames: dict[float, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for threshold, frame in frames.items():
        test = frame[frame["split"].eq("test")].copy()
        test["year"] = test["timestamp"].dt.year.astype(str)
        test["quarter"] = test["timestamp"].dt.to_period("Q").astype(str)
        for direction in ["ENTER_BUY", "ENTER_SELL"]:
            part = test[test["prediction"].eq(direction)]
            rows.append(metric_row(threshold, "direction", direction, part, len(test)))
        for year, part in test.groupby("year", dropna=False):
            rows.append(metric_row(threshold, "year", str(year), part, len(test)))
        for quarter, part in test.groupby("quarter", dropna=False):
            rows.append(metric_row(threshold, "quarter", str(quarter), part, len(test)))
        q2 = frame[is_2026q2(frame)]
        rows.append(metric_row(threshold, "special", "2026Q2", q2, len(test)))
    return pd.DataFrame(rows)


def metric_row(threshold: float, segment_type: str, segment: str, frame: pd.DataFrame, denominator: int) -> dict[str, Any]:
    metrics = trade_metrics(frame, "adjusted_R")
    return {
        "min_score": threshold,
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


def is_2026q2(frame: pd.DataFrame) -> pd.Series:
    return frame["timestamp"].between(
        pd.Timestamp("2026-04-01 00:00:00", tz="UTC"),
        pd.Timestamp("2026-04-14 23:59:59", tz="UTC"),
    )


def markdown_summary(summary: pd.DataFrame, temporal: pd.DataFrame, reference: pd.DataFrame) -> str:
    recommendation = choose_recommendation(summary)
    lines = [
        "# Online Priority Threshold Sweep",
        "",
        "## Scope",
        "",
        f"- Source scenario: `{SCENARIO_C}`.",
        f"- Reference input checked: `{REFERENCE_TRADES}` with `{len(reference):,}` online causal rows.",
        "- Formula de score sin cambios.",
        "- Sin entrenamiento de modelos.",
        "- Cada umbral se re-simula online: si una señal no supera umbral, el sistema queda libre para señales futuras.",
        "",
        "## Test Summary",
        "",
        summary_table(summary),
        "",
        "## BUY vs SELL",
        "",
        temporal_table(temporal[temporal["segment_type"].eq("direction")]),
        "",
        "## Por Año",
        "",
        temporal_table(temporal[temporal["segment_type"].eq("year")]),
        "",
        "## Por Trimestre",
        "",
        temporal_table(temporal[temporal["segment_type"].eq("quarter")]),
        "",
        "## 2026Q2",
        "",
        temporal_table(temporal[temporal["segment_type"].eq("special")]),
        "",
        "## Recomendación",
        "",
        recommendation_text(recommendation, summary),
    ]
    return "\n".join(lines) + "\n"


def choose_recommendation(summary: pd.DataFrame) -> pd.Series:
    viable = summary[
        (summary["profit_factor"] > 1.0)
        & (summary["avg_r"] > 0.0)
        & (summary["coverage"] >= 0.45)
    ].copy()
    if viable.empty:
        viable = summary[(summary["profit_factor"] > 1.0) & (summary["avg_r"] > 0.0)].copy()
    if viable.empty:
        return summary.sort_values(["profit_factor", "avg_r"], ascending=False).iloc[0]
    viable["utility"] = viable["profit_factor"] * 0.55 + viable["avg_r"] * 0.35 + viable["coverage"] * 0.10
    return viable.sort_values(["utility", "coverage"], ascending=False).iloc[0]


def summary_table(frame: pd.DataFrame) -> str:
    rows = [
        "| Min score | Trades | Coverage | PF | Avg R | DD | Total R | Q2 PF | Q2 Avg R |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        rows.append(
            f"| {row['min_score']:.2f} | {int(row['trades']):,} | {row['coverage']:.2%} | "
            f"{row['profit_factor']:.4f} | {row['avg_r']:.4f} | {row['max_drawdown_r']:.2f} | "
            f"{row['total_r']:.2f} | {row['q2_profit_factor']:.4f} | {row['q2_avg_r']:.4f} |"
        )
    return "\n".join(rows)


def temporal_table(frame: pd.DataFrame) -> str:
    rows = [
        "| Min score | Segment | Trades | Coverage | PF | Avg R | DD | Total R |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        rows.append(
            f"| {row['min_score']:.2f} | `{row['segment']}` | {int(row['trades']):,} | {row['coverage']:.2%} | "
            f"{row['profit_factor']:.4f} | {row['avg_r']:.4f} | {row['max_drawdown_r']:.2f} | {row['total_r']:.2f} |"
        )
    return "\n".join(rows)


def recommendation_text(recommendation: pd.Series, summary: pd.DataFrame) -> str:
    base = summary[summary["min_score"].eq(0.0)].iloc[0]
    return (
        f"Umbral operativo candidato para CEO-MAGI v3: `{recommendation['min_score']:.2f}`. "
        f"Produce PF `{recommendation['profit_factor']:.4f}`, Avg R `{recommendation['avg_r']:.4f}`, "
        f"DD `{recommendation['max_drawdown_r']:.2f}`, Total R `{recommendation['total_r']:.2f}` y "
        f"mantiene coverage `{recommendation['coverage']:.2%}` vs el online causal sin filtro adicional. "
        f"Frente a min_score 0.00, el PF cambia de `{base['profit_factor']:.4f}` a "
        f"`{recommendation['profit_factor']:.4f}` y los trades de `{int(base['trades'])}` a `{int(recommendation['trades'])}`. "
        "Es un candidato operativo, no una regla final; debe pasar stress severo y validación live/paper antes de fijarse."
    )


if __name__ == "__main__":
    raise SystemExit(main())
