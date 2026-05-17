from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from validate_scenario_c_realistic import (
    BAR_MINUTES,
    COMMISSION_PIPS_ROUND_TURN,
    DEFAULT_TIMEOUT_BARS,
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
SUMMARY_CSV = OUTPUT_DIR / "scenario_c_robustness_summary.csv"
SUMMARY_MD = OUTPUT_DIR / "scenario_c_robustness_summary.md"
DISTRIBUTION_PNG = OUTPUT_DIR / "scenario_c_robustness_distribution.png"
RUNS = 50


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = load_scenario_c_candidates()
    executable = select_non_overlapping_trades(candidates)

    rows = []
    for run_id in range(1, RUNS + 1):
        seed = RANDOM_SEED + run_id
        executed = apply_slippage_with_seed(executable, seed)
        test = executed[executed["split"].eq("test")].copy()
        metrics = trade_metrics(test, "adjusted_R")
        rows.append(
            {
                "run_id": run_id,
                "seed": seed,
                "scenario": SCENARIO_C,
                "split": "test",
                "trades": metrics["trades"],
                "avg_r": metrics["avg_r"],
                "total_r": metrics["total_r"],
                "profit_factor": metrics["profit_factor"],
                "max_drawdown_r": metrics["max_drawdown_r"],
                "win_rate": metrics["win_rate"],
                "mean_slippage_r": round_float(float(test["slippage_r"].mean()) if len(test) else 0.0),
                "candidate_trades_before_no_overlap": int(executable.attrs["candidate_trades_before_no_overlap"]),
                "skipped_by_no_overlap": int(executable.attrs["skipped_by_no_overlap"]),
            }
        )

    runs = pd.DataFrame(rows)
    stats = build_summary_stats(runs)

    output = runs.merge(stats, how="cross")
    output.to_csv(SUMMARY_CSV, index=False)
    SUMMARY_MD.write_text(markdown_summary(runs, stats), encoding="utf-8")
    write_distribution_chart(runs)

    print(f"output_csv={SUMMARY_CSV}")
    print(f"output_md={SUMMARY_MD}")
    print(f"output_png={DISTRIBUTION_PNG}")
    print(stats.to_string(index=False))
    return 0


def select_non_overlapping_trades(candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    active_until: pd.Timestamp | None = None
    skipped_overlap = 0

    for _, row in candidates.iterrows():
        timestamp = row["timestamp"]
        if active_until is not None and timestamp < active_until:
            skipped_overlap += 1
            continue

        out = row.copy()
        out["exit_timestamp"] = row["exit_timestamp_raw"]
        rows.append(out)
        active_until = row["exit_timestamp_raw"]

    executed = pd.DataFrame(rows)
    if executed.empty:
        raise ValueError("No scenario C trades remained after no-overlap execution.")
    executed.attrs["candidate_trades_before_no_overlap"] = int(len(candidates))
    executed.attrs["skipped_by_no_overlap"] = int(skipped_overlap)
    return executed.reset_index(drop=True)


def apply_slippage_with_seed(executable: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    executed = executable.copy()
    spread_pips = pd.to_numeric(executed["spread_pips"], errors="coerce").fillna(1.0)
    executed["spread_r"] = spread_pips / SL_PIPS
    executed["commission_r"] = COMMISSION_PIPS_ROUND_TURN / SL_PIPS
    executed["slippage_r"] = rng.uniform(SLIPPAGE_MIN_R, SLIPPAGE_MAX_R, size=len(executed))
    executed["adjusted_R"] = (
        pd.to_numeric(executed["gross_r"], errors="coerce").fillna(0.0)
        - executed["spread_r"]
        - executed["commission_r"]
        - executed["slippage_r"]
    )
    executed["execution_model"] = "robustness_spread+commission+adverse_slippage+bid_ask+no_overlap+timeout"
    return executed


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


def build_summary_stats(runs: pd.DataFrame) -> pd.DataFrame:
    metrics = ["profit_factor", "avg_r", "max_drawdown_r", "total_r", "trades"]
    data: dict[str, float] = {
        "runs": float(len(runs)),
        "pf_gt_1_pct": round_float(float((runs["profit_factor"] > 1.0).mean() * 100.0)),
        "avg_r_gt_0_pct": round_float(float((runs["avg_r"] > 0.0).mean() * 100.0)),
    }
    for metric in metrics:
        values = pd.to_numeric(runs[metric], errors="coerce")
        data[f"{metric}_mean"] = round_float(float(values.mean()))
        data[f"{metric}_median"] = round_float(float(values.median()))
        data[f"{metric}_p05"] = round_float(float(values.quantile(0.05)))
        data[f"{metric}_p95"] = round_float(float(values.quantile(0.95)))
    return pd.DataFrame([data])


def markdown_summary(runs: pd.DataFrame, stats: pd.DataFrame) -> str:
    s = stats.iloc[0]
    lines = [
        "# Scenario C Realistic Robustness Test",
        "",
        "## Scope",
        "",
        f"- Runs: `{RUNS}`.",
        f"- Scenario: `{SCENARIO_C}`.",
        f"- Slippage: adverso aleatorio entre `{SLIPPAGE_MIN_R:.2f}R` y `{SLIPPAGE_MAX_R:.2f}R`.",
        f"- Costos constantes: spread histórico, comisión `{COMMISSION_PIPS_ROUND_TURN:.2f}` pips, SL `{SL_PIPS:.1f}` pips.",
        "- Reglas y modelos: sin cambios.",
        "- No solapamiento: un solo trade activo global.",
        f"- Timeout: `{DEFAULT_TIMEOUT_BARS}` barras M5 o `bars_to_exit` del label.",
        "",
        "## Distribución Test",
        "",
        "| Métrica | Promedio | Mediana | P05 | P95 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for metric, label in [
        ("profit_factor", "PF"),
        ("avg_r", "Avg R"),
        ("max_drawdown_r", "Max DD"),
        ("total_r", "Total R"),
        ("trades", "Trades"),
    ]:
        lines.append(
            f"| {label} | {s[f'{metric}_mean']:.6f} | {s[f'{metric}_median']:.6f} | "
            f"{s[f'{metric}_p05']:.6f} | {s[f'{metric}_p95']:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Supervivencia del edge",
            "",
            f"- Corridas con PF > 1: `{s['pf_gt_1_pct']:.2f}%`.",
            f"- Corridas con Avg R > 0: `{s['avg_r_gt_0_pct']:.2f}%`.",
            "",
            "## Conclusión",
            "",
            conclusion_text(s),
            "",
            "## Primeras 10 corridas",
            "",
            runs_table(runs.head(10)),
        ]
    )
    return "\n".join(lines) + "\n"


def runs_table(frame: pd.DataFrame) -> str:
    rows = [
        "| Run | PF | Avg R | Max DD | Total R | Trades |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        rows.append(
            f"| {int(row['run_id'])} | {row['profit_factor']:.6f} | {row['avg_r']:.6f} | "
            f"{row['max_drawdown_r']:.6f} | {row['total_r']:.6f} | {int(row['trades'])} |"
        )
    return "\n".join(rows)


def conclusion_text(stats: pd.Series) -> str:
    pf_survival = float(stats["pf_gt_1_pct"])
    avg_survival = float(stats["avg_r_gt_0_pct"])
    pf_p05 = float(stats["profit_factor_p05"])
    avg_p05 = float(stats["avg_r_p05"])
    if pf_survival == 100.0 and avg_survival == 100.0 and pf_p05 > 1.0 and avg_p05 > 0.0:
        return (
            "El edge realista luce robusto frente a esta variación de slippage: incluso el percentil 5 "
            "mantiene PF > 1 y Avg R positivo."
        )
    if pf_survival >= 90.0 and avg_survival >= 90.0:
        return (
            "El edge realista sobrevive, pero con margen moderado. No parece roto por el slippage aleatorio, "
            "aunque conviene seguir probando comisiones y spreads más duros."
        )
    return (
        "El edge realista luce frágil: una parte relevante de las corridas pierde PF > 1 o Avg R positivo. "
        "Antes de considerarlo estable haría falta endurecer reglas de ejecución o reducir sensibilidad a costos."
    )


def write_distribution_chart(runs: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), dpi=150)
    chart_specs = [
        ("profit_factor", "PF"),
        ("avg_r", "Avg R"),
        ("max_drawdown_r", "Max DD"),
        ("total_r", "Total R"),
    ]
    for ax, (column, title) in zip(axes.flatten(), chart_specs):
        ax.hist(runs[column], bins=12, color="#2F6F4E", alpha=0.82, edgecolor="white")
        ax.axvline(runs[column].mean(), color="#243B53", linestyle="--", linewidth=1.2, label="media")
        if column == "profit_factor":
            ax.axvline(1.0, color="#B42318", linestyle=":", linewidth=1.4, label="PF=1")
        if column == "avg_r":
            ax.axvline(0.0, color="#B42318", linestyle=":", linewidth=1.4, label="Avg R=0")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
        ax.legend()
    fig.suptitle("Scenario C realistic robustness distribution", fontsize=14)
    fig.tight_layout()
    fig.savefig(DISTRIBUTION_PNG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
