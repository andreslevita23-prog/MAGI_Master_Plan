from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


INTEGRATED_TRADES = Path("data/output/magi_v2/baltasar_gaspar_v2_integration/integrated_trades.csv")
RULE_TRADES = Path("data/output/magi_v2/melchor_v2_rule_layer/rule_filtered_trades.csv")
LABELS = Path("data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet")
PREVIOUS_SUMMARY = Path("artifacts/magi_validation/summary_metrics.csv")
OUTPUT_DIR = Path("artifacts/magi_realistic_scenario_c")

SCENARIO_C = "C_baltasar_gaspar_melchor_combined_block"
SL_PIPS = 10.0
BAR_MINUTES = 5
DEFAULT_TIMEOUT_BARS = 48
COMMISSION_PIPS_ROUND_TURN = 0.7
SLIPPAGE_MIN_R = 0.10
SLIPPAGE_MAX_R = 0.30
RANDOM_SEED = 20260501


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    base = load_scenario_c_candidates()
    realistic = apply_realistic_execution(base)
    previous = load_previous_metrics()

    metrics = build_metrics(realistic)
    comparison = compare_to_previous(metrics, previous)
    equity = build_equity(realistic)
    period_metrics = build_period_metrics(realistic)

    realistic.to_csv(OUTPUT_DIR / "scenario_c_realistic_trades.csv", index=False)
    equity.to_csv(OUTPUT_DIR / "scenario_c_realistic_equity_curve.csv", index=False)
    metrics.to_csv(OUTPUT_DIR / "scenario_c_realistic_metrics.csv", index=False)
    comparison.to_csv(OUTPUT_DIR / "scenario_c_realistic_comparison.csv", index=False)
    period_metrics.to_csv(OUTPUT_DIR / "scenario_c_realistic_period_metrics.csv", index=False)
    write_equity_chart(equity)
    write_report(metrics, comparison, period_metrics)
    write_metadata(realistic)

    test = metrics[metrics["split"].eq("test")].iloc[0]
    prev_test = comparison[comparison["split"].eq("test")].iloc[0]
    print(f"output_dir={OUTPUT_DIR}")
    print(f"test_pf_adjusted={test['profit_factor']:.6f}")
    print(f"test_avg_r_adjusted={test['avg_r']:.6f}")
    print(f"test_dd_adjusted={test['max_drawdown_r']:.6f}")
    print(f"test_pf_previous={prev_test['previous_profit_factor']:.6f}")
    print(f"test_trades_executed={int(test['trades'])}")
    return 0


def load_scenario_c_candidates() -> pd.DataFrame:
    integrated = pd.read_csv(INTEGRATED_TRADES)
    rules = pd.read_csv(RULE_TRADES)
    labels = pd.read_parquet(LABELS)

    assert_columns(
        integrated,
        {
            "timestamp",
            "symbol",
            "split",
            "prediction",
            "realized_R",
            "gaspar_block",
        },
        INTEGRATED_TRADES,
    )
    assert_columns(
        rules,
        {
            "timestamp",
            "symbol",
            "prediction",
            "combined_risk_rule_blocked_block",
        },
        RULE_TRADES,
    )
    assert_columns(
        labels,
        {
            "timestamp",
            "symbol",
            "entry_price",
            "buy_R",
            "sell_R",
            "buy_first_touch",
            "sell_first_touch",
            "buy_bars_to_exit",
            "sell_bars_to_exit",
            "spread_pips",
        },
        LABELS,
    )

    integrated = normalize_trade_frame(integrated)
    rules = normalize_trade_frame(rules)
    labels = normalize_label_frame(labels)

    if len(integrated) != len(rules):
        raise ValueError(f"Row mismatch: integrated={len(integrated)} rules={len(rules)}")

    key_cols = ["timestamp", "symbol", "prediction"]
    mismatch = (integrated[key_cols].reset_index(drop=True) != rules[key_cols].reset_index(drop=True)).any(axis=1)
    if bool(mismatch.any()):
        first = int(mismatch.idxmax())
        raise ValueError(f"Integrated/rule rows are not aligned at {first}")

    df = integrated.copy()
    df["combined_risk_rule_blocked_block"] = as_bool(rules["combined_risk_rule_blocked_block"])
    df = df.loc[~as_bool(df["gaspar_block"]) & ~df["combined_risk_rule_blocked_block"]].copy()

    df = df.merge(labels, how="left", on=["timestamp", "symbol"], validate="many_to_one")
    if df["entry_price"].isna().any():
        raise ValueError("Some scenario C rows could not be matched with RR2 labels.")

    is_buy = df["prediction"].eq("ENTER_BUY")
    df["gross_r"] = np.where(is_buy, df["buy_R"], df["sell_R"])
    df["first_touch"] = np.where(is_buy, df["buy_first_touch"], df["sell_first_touch"])
    df["bars_to_exit"] = np.where(is_buy, df["buy_bars_to_exit"], df["sell_bars_to_exit"])
    df["bars_to_exit"] = pd.to_numeric(df["bars_to_exit"], errors="coerce").fillna(DEFAULT_TIMEOUT_BARS).clip(lower=1)
    df["exit_timestamp_raw"] = df["timestamp"] + pd.to_timedelta(df["bars_to_exit"] * BAR_MINUTES, unit="min")
    df["is_timeout"] = df["first_touch"].astype(str).str.upper().eq("TIMEOUT")
    return df.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)


def normalize_trade_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["symbol"] = out["symbol"].astype(str)
    out["prediction"] = out["prediction"].astype(str)
    out["realized_R"] = pd.to_numeric(out.get("realized_R"), errors="coerce").fillna(0.0)
    return out


def normalize_label_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out["symbol"] = out["symbol"].astype(str)
    for col in ["entry_price", "buy_R", "sell_R", "buy_bars_to_exit", "sell_bars_to_exit", "spread_pips"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    keep = [
        "timestamp",
        "symbol",
        "entry_price",
        "buy_R",
        "sell_R",
        "buy_first_touch",
        "sell_first_touch",
        "buy_bars_to_exit",
        "sell_bars_to_exit",
        "spread_pips",
    ]
    return out[keep].drop_duplicates(["timestamp", "symbol"], keep="first")


def apply_realistic_execution(candidates: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    rows: list[pd.Series] = []
    active_until: pd.Timestamp | None = None
    skipped_overlap = 0

    for _, row in candidates.iterrows():
        timestamp = row["timestamp"]
        if active_until is not None and timestamp < active_until:
            skipped_overlap += 1
            continue

        gross_r = float(row["gross_r"])
        spread_pips = float(row["spread_pips"]) if pd.notna(row["spread_pips"]) else 1.0
        spread_r = spread_pips / SL_PIPS
        commission_r = COMMISSION_PIPS_ROUND_TURN / SL_PIPS
        slippage_r = float(rng.uniform(SLIPPAGE_MIN_R, SLIPPAGE_MAX_R))
        adjusted_r = gross_r - spread_r - commission_r - slippage_r

        out = row.copy()
        out["spread_r"] = spread_r
        out["commission_r"] = commission_r
        out["slippage_r"] = slippage_r
        out["adjusted_R"] = adjusted_r
        out["exit_timestamp"] = row["exit_timestamp_raw"]
        out["execution_model"] = "spread+commission+adverse_slippage+bid_ask+no_overlap+timeout"
        rows.append(out)
        active_until = row["exit_timestamp_raw"]

    executed = pd.DataFrame(rows)
    if executed.empty:
        raise ValueError("No scenario C trades remained after no-overlap execution.")
    executed.attrs["candidate_trades_before_no_overlap"] = int(len(candidates))
    executed.attrs["skipped_by_no_overlap"] = int(skipped_overlap)
    executed["year"] = executed["timestamp"].dt.year.astype("Int64")
    executed["quarter"] = executed["timestamp"].dt.to_period("Q").astype(str)
    executed["month"] = executed["timestamp"].dt.to_period("M").astype(str)
    executed["is_2026q2"] = executed["timestamp"].between(
        pd.Timestamp("2026-04-01 00:00:00", tz="UTC"),
        pd.Timestamp("2026-04-14 23:59:59", tz="UTC"),
    )
    return executed.reset_index(drop=True)


def load_previous_metrics() -> pd.DataFrame:
    previous = pd.read_csv(PREVIOUS_SUMMARY)
    return previous[
        previous["scenario"].eq(SCENARIO_C)
        & previous["direction"].eq("ALL")
        & previous["split"].isin(["all", "train", "validation", "test", "2026Q2"])
    ].copy()


def build_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in ["all", "train", "validation", "test"]:
        part = df if split == "all" else df[df["split"].eq(split)]
        rows.append(metric_row(split, part))
    rows.append(metric_row("2026Q2", df[df["is_2026q2"]]))
    return pd.DataFrame(rows)


def build_period_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period_type, column in [("year", "year"), ("quarter", "quarter"), ("month", "month")]:
        for period, part in df.groupby(column, dropna=False):
            row = metric_row(str(period), part)
            row["period_type"] = period_type
            row["period"] = str(period)
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["period_type", "period"]).reset_index(drop=True)


def metric_row(split: str, part: pd.DataFrame) -> dict[str, Any]:
    adjusted = trade_metrics(part, "adjusted_R")
    gross = trade_metrics(part, "gross_r")
    return {
        "scenario": SCENARIO_C,
        "split": split,
        "trades": adjusted["trades"],
        "avg_r": adjusted["avg_r"],
        "total_r": adjusted["total_r"],
        "profit_factor": adjusted["profit_factor"],
        "max_drawdown_r": adjusted["max_drawdown_r"],
        "win_rate": adjusted["win_rate"],
        "gross_avg_r": gross["avg_r"],
        "gross_profit_factor": gross["profit_factor"],
        "gross_max_drawdown_r": gross["max_drawdown_r"],
        "mean_spread_r": round_float(float(part["spread_r"].mean()) if len(part) else 0.0),
        "mean_commission_r": round_float(float(part["commission_r"].mean()) if len(part) else 0.0),
        "mean_slippage_r": round_float(float(part["slippage_r"].mean()) if len(part) else 0.0),
        "timeout_share": round_float(float(part["is_timeout"].mean()) if len(part) else 0.0),
    }


def compare_to_previous(metrics: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    prev = previous.rename(
        columns={
            "trades": "previous_trades",
            "avg_r": "previous_avg_r",
            "profit_factor": "previous_profit_factor",
            "max_drawdown_r": "previous_max_drawdown_r",
            "total_r": "previous_total_r",
            "win_rate": "previous_win_rate",
        }
    )
    cols = [
        "split",
        "previous_trades",
        "previous_avg_r",
        "previous_profit_factor",
        "previous_max_drawdown_r",
        "previous_total_r",
        "previous_win_rate",
    ]
    out = metrics.merge(prev[cols], on="split", how="left")
    out["trade_delta"] = out["trades"] - out["previous_trades"]
    out["avg_r_delta"] = out["avg_r"] - out["previous_avg_r"]
    out["pf_delta"] = out["profit_factor"] - out["previous_profit_factor"]
    out["dd_delta"] = out["max_drawdown_r"] - out["previous_max_drawdown_r"]
    out["total_r_delta"] = out["total_r"] - out["previous_total_r"]
    for col in ["avg_r_delta", "pf_delta", "dd_delta", "total_r_delta"]:
        out[col] = out[col].map(round_float)
    return out


def build_equity(df: pd.DataFrame) -> pd.DataFrame:
    part = df.sort_values(["timestamp", "symbol", "prediction"]).copy()
    part["trade_index"] = np.arange(1, len(part) + 1)
    part["equity_r_adjusted"] = part["adjusted_R"].cumsum()
    part["equity_r_gross"] = part["gross_r"].cumsum()
    part["running_peak_adjusted"] = part["equity_r_adjusted"].cummax().clip(lower=0.0)
    part["drawdown_r_adjusted"] = part["running_peak_adjusted"] - part["equity_r_adjusted"]
    return part[
        [
            "trade_index",
            "timestamp",
            "exit_timestamp",
            "symbol",
            "split",
            "prediction",
            "gross_r",
            "adjusted_R",
            "equity_r_gross",
            "equity_r_adjusted",
            "drawdown_r_adjusted",
            "first_touch",
            "is_timeout",
            "spread_r",
            "commission_r",
            "slippage_r",
        ]
    ].copy()


def write_equity_chart(equity: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(11, 5.6), dpi=150)
    plt.plot(equity["trade_index"], equity["equity_r_gross"], label="Escenario C bruto", linewidth=1.1, alpha=0.75)
    plt.plot(equity["trade_index"], equity["equity_r_adjusted"], label="Escenario C realista", linewidth=1.4)
    plt.title("MAGI escenario C - equity curve realista")
    plt.xlabel("Trade ejecutado")
    plt.ylabel("R acumulado")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "scenario_c_realistic_equity_curve.png", bbox_inches="tight")
    plt.close()


def write_report(metrics: pd.DataFrame, comparison: pd.DataFrame, period_metrics: pd.DataFrame) -> None:
    lines = [
        "# MAGI Escenario C - Validacion Realista",
        "",
        "## Supuestos aplicados",
        "",
        f"- Fuente de trades: `{SCENARIO_C}`.",
        f"- SL usado para convertir costos a R: `{SL_PIPS:.1f}` pips.",
        "- Spread: `spread_pips` histórico del dataset RR2, convertido a R.",
        f"- Comisión round-turn: `{COMMISSION_PIPS_ROUND_TURN:.2f}` pips por trade.",
        f"- Slippage adverso aleatorio: `{SLIPPAGE_MIN_R:.2f}` a `{SLIPPAGE_MAX_R:.2f}` R, seed `{RANDOM_SEED}`.",
        "- Bid/Ask: se penaliza la ejecución con spread realista por trade.",
        "- No solapamiento: un solo trade activo global; se descartan señales hasta el cierre.",
        f"- Timeout: si no hay TP/SL, se usa cierre a `{DEFAULT_TIMEOUT_BARS}` barras M5 o `bars_to_exit` del label.",
        "",
        "## Métricas ajustadas",
        "",
        table(metrics),
        "",
        "## Comparación vs resultados anteriores",
        "",
        comparison_table(comparison),
        "",
        "## Peores periodos por DD ajustado",
        "",
        table(period_metrics[period_metrics["period_type"].eq("quarter")].sort_values("max_drawdown_r", ascending=False).head(10)),
        "",
        "## Lectura",
        "",
        interpretation(comparison),
        "",
    ]
    (OUTPUT_DIR / "scenario_c_realistic_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_metadata(df: pd.DataFrame) -> None:
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "integrated_trades": str(INTEGRATED_TRADES),
            "rule_trades": str(RULE_TRADES),
            "labels": str(LABELS),
            "previous_summary": str(PREVIOUS_SUMMARY),
        },
        "assumptions": {
            "sl_pips": SL_PIPS,
            "commission_pips_round_turn": COMMISSION_PIPS_ROUND_TURN,
            "slippage_min_r": SLIPPAGE_MIN_R,
            "slippage_max_r": SLIPPAGE_MAX_R,
            "random_seed": RANDOM_SEED,
            "bar_minutes": BAR_MINUTES,
            "timeout_bars_default": DEFAULT_TIMEOUT_BARS,
            "no_overlap": "one active trade globally",
        },
        "rows": {
            "candidate_trades_before_no_overlap": int(df.attrs.get("candidate_trades_before_no_overlap", len(df))),
            "executed_trades": int(len(df)),
            "skipped_by_no_overlap": int(df.attrs.get("skipped_by_no_overlap", 0)),
            "timeouts": int(df["is_timeout"].sum()),
        },
    }
    (OUTPUT_DIR / "scenario_c_realistic_metadata.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def table(frame: pd.DataFrame) -> str:
    rows = ["| Split | Trades | Avg R | PF | DD | Win rate | Total R |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for _, row in frame.iterrows():
        label = row.get("split", row.get("period", ""))
        rows.append(
            f"| {label} | {int(row['trades']):,} | {row['avg_r']:.4f} | {row['profit_factor']:.4f} | "
            f"{row['max_drawdown_r']:.2f} | {row['win_rate']:.2%} | {row['total_r']:.2f} |"
        )
    return "\n".join(rows)


def comparison_table(frame: pd.DataFrame) -> str:
    rows = [
        "| Split | Prev trades | Real trades | Prev PF | Real PF | Prev Avg R | Real Avg R | Prev DD | Real DD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        rows.append(
            f"| {row['split']} | {int(row['previous_trades']):,} | {int(row['trades']):,} | "
            f"{row['previous_profit_factor']:.4f} | {row['profit_factor']:.4f} | "
            f"{row['previous_avg_r']:.4f} | {row['avg_r']:.4f} | "
            f"{row['previous_max_drawdown_r']:.2f} | {row['max_drawdown_r']:.2f} |"
        )
    return "\n".join(rows)


def interpretation(comparison: pd.DataFrame) -> str:
    test = comparison[comparison["split"].eq("test")].iloc[0]
    return (
        f"En test, el escenario C pasa de PF `{test['previous_profit_factor']:.4f}` a "
        f"`{test['profit_factor']:.4f}` después de costos, slippage y no solapamiento. "
        f"El Avg R cambia de `{test['previous_avg_r']:.4f}` a `{test['avg_r']:.4f}` y el DD de "
        f"`{test['previous_max_drawdown_r']:.2f}` a `{test['max_drawdown_r']:.2f}`. "
        "Esta lectura es más cercana a ejecución real, pero sigue siendo backtest: no incluye latencia, rechazos de orden ni cambios dinámicos de liquidez."
    )


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


def max_drawdown(r: pd.Series) -> float:
    if r.empty:
        return 0.0
    equity = r.cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return float((peak - equity).max())


def assert_columns(df: pd.DataFrame, required: set[str], path: Path) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")


def as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def round_float(value: float) -> float:
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
