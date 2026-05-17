from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from validate_scenario_c_realistic import (
    COMMISSION_PIPS_ROUND_TURN,
    LABELS,
    RANDOM_SEED,
    SCENARIO_C,
    SLIPPAGE_MAX_R,
    SLIPPAGE_MIN_R,
    SL_PIPS,
    load_scenario_c_candidates,
    max_drawdown,
    round_float,
)


OUTPUT_DIR = Path("artifacts/magi_validation")
SUMMARY_CSV = OUTPUT_DIR / "priority_comparison.csv"
SUMMARY_MD = OUTPUT_DIR / "priority_comparison.md"
PRIORITY_WINDOW_MINUTES = 15


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = enrich_candidates(load_scenario_c_candidates())
    conflict_stats = identify_conflicts(candidates)

    rows = []
    for strategy in ["baseline", "heuristic", "scoring_simple"]:
        selected = select_trades(candidates, strategy)
        executed = apply_realistic_costs(selected, RANDOM_SEED)
        for split in ["all", "train", "validation", "test", "2026Q2"]:
            part = split_frame(executed, split)
            metrics = trade_metrics(part, "adjusted_R")
            rows.append(
                {
                    "strategy": strategy,
                    "split": split,
                    "priority_window_minutes": PRIORITY_WINDOW_MINUTES,
                    "trades": metrics["trades"],
                    "avg_r": metrics["avg_r"],
                    "total_r": metrics["total_r"],
                    "profit_factor": metrics["profit_factor"],
                    "max_drawdown_r": metrics["max_drawdown_r"],
                    "win_rate": metrics["win_rate"],
                    "gross_avg_r": trade_metrics(part, "gross_r")["avg_r"],
                    "mean_priority_score": round_float(float(part["priority_score"].mean()) if len(part) else 0.0),
                }
            )

    summary = pd.DataFrame(rows)
    summary.to_csv(SUMMARY_CSV, index=False)
    SUMMARY_MD.write_text(markdown_summary(summary, conflict_stats), encoding="utf-8")

    test = summary[summary["split"].eq("test")].copy()
    print(f"output_csv={SUMMARY_CSV}")
    print(f"output_md={SUMMARY_MD}")
    print(test[["strategy", "trades", "profit_factor", "avg_r", "max_drawdown_r", "total_r"]].to_string(index=False))
    return 0


def enrich_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    labels = pd.read_parquet(LABELS)
    keep = [
        "timestamp",
        "symbol",
        "baltasar_confidence",
        "melchor_signal",
        "melchor_confidence",
        "melchor_risk_flags",
        "gaspar_confidence",
        "baltasar_gaspar_alignment",
        "mage_agreement",
        "session",
    ]
    labels = labels[keep].copy()
    labels["timestamp"] = pd.to_datetime(labels["timestamp"], utc=True, errors="coerce")
    labels["symbol"] = labels["symbol"].astype(str)
    labels = labels.drop_duplicates(["timestamp", "symbol"], keep="first")

    out = candidates.merge(labels, how="left", on=["timestamp", "symbol"], validate="many_to_one")
    out["baltasar_confidence"] = pd.to_numeric(out["baltasar_confidence"], errors="coerce").fillna(0.0)
    out["melchor_confidence"] = pd.to_numeric(out["melchor_confidence"], errors="coerce").fillna(0.0)
    out["gaspar_confidence"] = pd.to_numeric(out["gaspar_confidence"], errors="coerce").fillna(0.0)
    out["gaspar_p_deteriorating"] = pd.to_numeric(out["gaspar_p_deteriorating"], errors="coerce").fillna(0.0)
    out["rolling_pf_50"] = pd.to_numeric(out["rolling_pf_50"], errors="coerce").fillna(1.0)
    out["rolling_drawdown_50"] = pd.to_numeric(out["rolling_drawdown_50"], errors="coerce").fillna(0.0)
    out["rolling_unfavorable_rate_50"] = pd.to_numeric(out["rolling_unfavorable_rate_50"], errors="coerce").fillna(0.0)
    out["melchor_signal"] = out["melchor_signal"].fillna("UNKNOWN").astype(str)
    out["melchor_risk_flags"] = out["melchor_risk_flags"].fillna("UNKNOWN").astype(str)
    out["context_quality_rr2"] = out["context_quality_rr2"].fillna("UNKNOWN").astype(str)
    out["baltasar_gaspar_alignment"] = out["baltasar_gaspar_alignment"].fillna("UNKNOWN").astype(str)
    out["priority_score"] = score_candidates(out)
    return out.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)


def identify_conflicts(candidates: pd.DataFrame) -> dict[str, Any]:
    same_ts = candidates.groupby("timestamp").size()
    sorted_ts = candidates["timestamp"].sort_values().tolist()
    clusters = 0
    clustered_rows = 0
    i = 0
    while i < len(sorted_ts):
        start = sorted_ts[i]
        j = i
        while j < len(sorted_ts) and sorted_ts[j] <= start + pd.Timedelta(minutes=PRIORITY_WINDOW_MINUTES):
            j += 1
        size = j - i
        if size > 1:
            clusters += 1
            clustered_rows += size
        i = j
    return {
        "candidate_rows": int(len(candidates)),
        "same_timestamp_conflict_count": int((same_ts > 1).sum()),
        "max_same_timestamp_candidates": int(same_ts.max()) if len(same_ts) else 0,
        "near_time_window_minutes": PRIORITY_WINDOW_MINUTES,
        "near_time_cluster_count": int(clusters),
        "near_time_clustered_rows": int(clustered_rows),
    }


def select_trades(candidates: pd.DataFrame, strategy: str) -> pd.DataFrame:
    selected_indices: list[int] = []
    i = 0
    ordered = candidates.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)
    ts = pd.to_datetime(ordered["timestamp"], utc=True, errors="coerce")
    ts_ns = ts.astype("int64").to_numpy()
    exit_ns = pd.to_datetime(ordered["exit_timestamp_raw"], utc=True, errors="coerce").astype("int64").to_numpy()
    window_ns = PRIORITY_WINDOW_MINUTES * 60 * 1_000_000_000

    while i < len(ordered):
        window_end_ns = ts_ns[i] + window_ns
        j = int(np.searchsorted(ts_ns, window_end_ns, side="right"))
        chosen_pos = choose_position(ordered, i, j, strategy)
        selected_indices.append(chosen_pos)
        i = int(np.searchsorted(ts_ns, exit_ns[chosen_pos], side="left"))

    selected = ordered.iloc[selected_indices].copy().reset_index(drop=True)
    selected["priority_strategy"] = strategy
    selected["priority_pool_size"] = [
        int(np.searchsorted(ts_ns, ts_ns[idx] + window_ns, side="right") - idx)
        for idx in selected_indices
    ]
    selected["priority_window_start"] = selected["timestamp"]
    selected["priority_window_end"] = selected["timestamp"] + pd.to_timedelta(PRIORITY_WINDOW_MINUTES, unit="min")
    selected.attrs["candidate_trades_before_priority"] = int(len(candidates))
    selected.attrs["selected_trades"] = int(len(selected))
    return selected


def choose_position(ordered: pd.DataFrame, start: int, end: int, strategy: str) -> int:
    pool = ordered.iloc[start:end]
    if strategy == "baseline":
        return start
    if strategy == "heuristic":
        ranked = pool.copy()
        ranked["melchor_blockish"] = ranked["melchor_signal"].str.upper().isin(["BLOCK", "CAUTION"]).astype(int)
        ranked["risk_high"] = ranked["melchor_risk_flags"].str.upper().str.contains("HIGH", na=False).astype(int)
        return int(ranked.sort_values(
            [
                "melchor_blockish",
                "risk_high",
                "gaspar_p_deteriorating",
                "baltasar_confidence",
                "rolling_pf_50",
                "timestamp",
            ],
            ascending=[True, True, True, False, False, True],
        ).index[0])
    if strategy == "scoring_simple":
        return int(pool.sort_values(["priority_score", "timestamp"], ascending=[False, True]).index[0])
    raise ValueError(f"Unknown strategy: {strategy}")


def score_candidates(df: pd.DataFrame) -> pd.Series:
    context_bonus = df["context_quality_rr2"].str.upper().map({"FAVORABLE": 0.10, "NEUTRAL": 0.0, "UNFAVORABLE": -0.12}).fillna(0.0)
    alignment_bonus = df["baltasar_gaspar_alignment"].str.upper().map({"ALIGNED": 0.08, "BALTASAR_NEUTRAL": 0.0}).fillna(0.0)
    melchor_signal = df["melchor_signal"].str.upper()
    melchor_penalty = np.select(
        [melchor_signal.eq("BLOCK"), melchor_signal.eq("CAUTION")],
        [0.35, 0.18],
        default=0.0,
    )
    risk_high_penalty = df["melchor_risk_flags"].str.upper().str.contains("HIGH", na=False).astype(float) * 0.12
    unfavorable_penalty = pd.to_numeric(df["rolling_unfavorable_rate_50"], errors="coerce").fillna(0.0) * 0.20
    dd_penalty = (pd.to_numeric(df["rolling_drawdown_50"], errors="coerce").fillna(0.0) / 100.0).clip(0, 0.30)
    pf_bonus = ((pd.to_numeric(df["rolling_pf_50"], errors="coerce").fillna(1.0) - 1.0) * 0.08).clip(-0.10, 0.20)
    return (
        pd.to_numeric(df["baltasar_confidence"], errors="coerce").fillna(0.0) * 1.00
        - pd.to_numeric(df["gaspar_p_deteriorating"], errors="coerce").fillna(0.0) * 0.75
        - melchor_penalty
        - risk_high_penalty
        - unfavorable_penalty
        - dd_penalty
        + pf_bonus
        + context_bonus
        + alignment_bonus
    )


def apply_realistic_costs(selected: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = selected.sort_values(["timestamp", "symbol", "prediction"]).copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["is_2026q2"] = out["timestamp"].between(
        pd.Timestamp("2026-04-01 00:00:00", tz="UTC"),
        pd.Timestamp("2026-04-14 23:59:59", tz="UTC"),
    )
    spread_pips = pd.to_numeric(out["spread_pips"], errors="coerce").fillna(1.0)
    out["spread_r"] = spread_pips / SL_PIPS
    out["commission_r"] = COMMISSION_PIPS_ROUND_TURN / SL_PIPS
    out["slippage_r"] = rng.uniform(SLIPPAGE_MIN_R, SLIPPAGE_MAX_R, size=len(out))
    out["adjusted_R"] = (
        pd.to_numeric(out["gross_r"], errors="coerce").fillna(0.0)
        - out["spread_r"]
        - out["commission_r"]
        - out["slippage_r"]
    )
    return out


def split_frame(df: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "all":
        return df
    if split == "2026Q2":
        return df[df["is_2026q2"]]
    return df[df["split"].eq(split)]


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


def markdown_summary(summary: pd.DataFrame, conflict_stats: dict[str, Any]) -> str:
    test = summary[summary["split"].eq("test")].copy()
    baseline = test[test["strategy"].eq("baseline")].iloc[0]
    best = test.sort_values(["profit_factor", "avg_r"], ascending=False).iloc[0]

    lines = [
        "# Scenario C Trade Priority Comparison",
        "",
        "## Scope",
        "",
        f"- Source scenario: `{SCENARIO_C}`.",
        "- Reglas y modelos: sin cambios.",
        "- Solo cambia la seleccion cuando hay senales cercanas.",
        f"- Ventana de prioridad: `{PRIORITY_WINDOW_MINUTES}` minutos.",
        "- Costos realistas: spread historico, comision base y slippage adverso 0.10R-0.30R.",
        "",
        "## Conflictos detectados",
        "",
        f"- Candidatos escenario C: `{conflict_stats['candidate_rows']:,}`.",
        f"- Conflictos exactos por timestamp: `{conflict_stats['same_timestamp_conflict_count']}`.",
        f"- Clusters cercanos en {PRIORITY_WINDOW_MINUTES} minutos: `{conflict_stats['near_time_cluster_count']:,}`.",
        f"- Filas dentro de clusters cercanos: `{conflict_stats['near_time_clustered_rows']:,}`.",
        "",
        "## Test split",
        "",
        table(test),
        "",
        "## All splits",
        "",
        table(summary),
        "",
        "## Conclusion",
        "",
        conclusion_text(baseline, best),
    ]
    return "\n".join(lines) + "\n"


def table(frame: pd.DataFrame) -> str:
    rows = [
        "| Strategy | Split | Trades | PF | Avg R | Max DD | Total R |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['strategy']}` | {row['split']} | {int(row['trades']):,} | "
            f"{row['profit_factor']:.4f} | {row['avg_r']:.4f} | "
            f"{row['max_drawdown_r']:.2f} | {row['total_r']:.2f} |"
        )
    return "\n".join(rows)


def conclusion_text(baseline: pd.Series, best: pd.Series) -> str:
    pf_delta = float(best["profit_factor"] - baseline["profit_factor"])
    avg_delta = float(best["avg_r"] - baseline["avg_r"])
    if best["strategy"] == "baseline" or pf_delta <= 0:
        return (
            f"La priorizacion no mejora el PF realista. Baseline queda en PF `{baseline['profit_factor']:.4f}` "
            f"y la mejor alternativa no lo supera de forma positiva."
        )
    return (
        f"La priorizacion mejora el PF realista: `{best['strategy']}` sube PF de "
        f"`{baseline['profit_factor']:.4f}` a `{best['profit_factor']:.4f}` "
        f"y Avg R cambia de `{baseline['avg_r']:.4f}` a `{best['avg_r']:.4f}`. "
        f"Delta PF `{pf_delta:.4f}`, delta Avg R `{avg_delta:.4f}`."
    )


if __name__ == "__main__":
    raise SystemExit(main())
