from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


INTEGRATED_TRADES = Path("data/output/magi_v2/baltasar_gaspar_v2_integration/integrated_trades.csv")
RULE_TRADES = Path("data/output/magi_v2/melchor_v2_rule_layer/rule_filtered_trades.csv")
OUTPUT_DIR = Path("artifacts/magi_validation")

SCENARIOS = {
    "A_baltasar_only": "Baltasar solo",
    "B_baltasar_gaspar": "Baltasar + Gaspar",
    "C_baltasar_gaspar_melchor_combined_block": "Baltasar + Gaspar + Melchor combined_risk_rule BLOCK",
    "D_baltasar_gaspar_melchor_q2_proxy_block_caution": "Baltasar + Gaspar + Melchor q2_like_proxy BLOCK+CAUTION",
}


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = load_and_merge()
    scenario_frames = build_scenarios(base)

    summary = build_summary(scenario_frames, base)
    temporal = build_temporal_breakdown(scenario_frames, base)
    equity = build_equity_curves(scenario_frames)

    summary.to_csv(OUTPUT_DIR / "summary_metrics.csv", index=False)
    temporal.to_csv(OUTPUT_DIR / "temporal_breakdown.csv", index=False)
    equity.to_csv(OUTPUT_DIR / "equity_curves.csv", index=False)
    (OUTPUT_DIR / "summary_metrics.md").write_text(markdown_summary(summary, temporal), encoding="utf-8")

    print(f"output_dir={OUTPUT_DIR}")
    print(summary[["scenario", "split", "trades", "coverage", "avg_r", "profit_factor", "max_drawdown_r"]].to_string(index=False))
    return 0


def load_and_merge() -> pd.DataFrame:
    if not INTEGRATED_TRADES.exists():
        raise FileNotFoundError(f"Missing integrated trades: {INTEGRATED_TRADES}")
    if not RULE_TRADES.exists():
        raise FileNotFoundError(f"Missing rule trades: {RULE_TRADES}")

    integrated = pd.read_csv(INTEGRATED_TRADES)
    rules = pd.read_csv(RULE_TRADES)
    required_integrated = {"timestamp", "symbol", "prediction", "realized_R", "split", "gaspar_block"}
    required_rules = {
        "timestamp",
        "symbol",
        "prediction",
        "realized_R",
        "combined_risk_rule_blocked_block",
        "q2_like_proxy_blocked_block_plus_caution",
    }
    missing_integrated = required_integrated - set(integrated.columns)
    missing_rules = required_rules - set(rules.columns)
    if missing_integrated:
        raise ValueError(f"Integrated trades missing columns: {sorted(missing_integrated)}")
    if missing_rules:
        raise ValueError(f"Rule trades missing columns: {sorted(missing_rules)}")

    integrated["timestamp"] = pd.to_datetime(integrated["timestamp"], utc=True, errors="coerce")
    rules["timestamp"] = pd.to_datetime(rules["timestamp"], utc=True, errors="coerce")
    integrated["realized_R"] = pd.to_numeric(integrated["realized_R"], errors="coerce").fillna(0.0)
    rules["realized_R"] = pd.to_numeric(rules["realized_R"], errors="coerce").fillna(0.0)
    integrated["row_id"] = np.arange(len(integrated))
    rules["row_id"] = np.arange(len(rules))

    if len(integrated) != len(rules):
        raise ValueError(f"Row count mismatch: integrated={len(integrated)} rules={len(rules)}")

    key_cols = ["timestamp", "symbol", "prediction", "realized_R"]
    mismatch = (integrated[key_cols].reset_index(drop=True) != rules[key_cols].reset_index(drop=True)).any(axis=1)
    if bool(mismatch.any()):
        first = int(mismatch.idxmax())
        raise ValueError(
            "Integrated trades and rule trades are not row-aligned at row "
            f"{first}: integrated={integrated.loc[first, key_cols].to_dict()} rules={rules.loc[first, key_cols].to_dict()}"
        )

    merged = integrated.copy()
    for column in [
        "combined_risk_rule_blocked_block",
        "q2_like_proxy_blocked_block_plus_caution",
        "combined_risk_rule_signal",
        "q2_like_proxy_signal",
    ]:
        merged[column] = rules[column]
    merged["gaspar_block"] = as_bool(merged["gaspar_block"])
    merged["combined_risk_rule_blocked_block"] = as_bool(merged["combined_risk_rule_blocked_block"])
    merged["q2_like_proxy_blocked_block_plus_caution"] = as_bool(merged["q2_like_proxy_blocked_block_plus_caution"])
    merged["timestamp"] = pd.to_datetime(merged["timestamp"], utc=True, errors="coerce")
    merged["year"] = merged["timestamp"].dt.year.astype("Int64")
    merged["quarter"] = merged["timestamp"].dt.to_period("Q").astype(str)
    merged["month"] = merged["timestamp"].dt.to_period("M").astype(str)
    merged["is_2026q2"] = merged["timestamp"].between(
        pd.Timestamp("2026-04-01 00:00:00", tz="UTC"),
        pd.Timestamp("2026-04-14 23:59:59", tz="UTC"),
    )
    return merged


def as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def build_scenarios(base: pd.DataFrame) -> dict[str, pd.DataFrame]:
    gaspar_allowed = ~base["gaspar_block"]
    return {
        "A_baltasar_only": base.copy(),
        "B_baltasar_gaspar": base.loc[gaspar_allowed].copy(),
        "C_baltasar_gaspar_melchor_combined_block": base.loc[
            gaspar_allowed & ~base["combined_risk_rule_blocked_block"]
        ].copy(),
        "D_baltasar_gaspar_melchor_q2_proxy_block_caution": base.loc[
            gaspar_allowed & ~base["q2_like_proxy_blocked_block_plus_caution"]
        ].copy(),
    }


def build_summary(scenarios: dict[str, pd.DataFrame], base: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in ["all", "train", "validation", "test"]:
        denominator = len(base if split == "all" else base[base["split"].eq(split)])
        for scenario, frame in scenarios.items():
            part = frame if split == "all" else frame[frame["split"].eq(split)]
            rows.append(summary_row(scenario, split, part, denominator))
            for direction in ["ENTER_BUY", "ENTER_SELL"]:
                direction_part = part[part["prediction"].eq(direction)]
                row = summary_row(scenario, f"{split}_{direction}", direction_part, denominator)
                row["direction"] = direction
                rows.append(row)
    q2_denominator = int(base["is_2026q2"].sum())
    for scenario, frame in scenarios.items():
        rows.append(summary_row(scenario, "2026Q2", frame[frame["is_2026q2"]], q2_denominator))
    return pd.DataFrame(rows)


def summary_row(scenario: str, split: str, frame: pd.DataFrame, denominator: int) -> dict[str, object]:
    metrics = trade_metrics(frame)
    return {
        "scenario": scenario,
        "scenario_label": SCENARIOS[scenario],
        "split": split,
        "direction": "ALL",
        "trades": metrics["trades"],
        "coverage": safe_div(metrics["trades"], denominator),
        "avg_r": metrics["avg_r"],
        "total_r": metrics["total_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r": metrics["max_drawdown_r"],
        "win_rate": metrics["win_rate"],
    }


def build_temporal_breakdown(scenarios: dict[str, pd.DataFrame], base: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period_type, column in [("year", "year"), ("quarter", "quarter")]:
        denominators = base.groupby(column).size().to_dict()
        for scenario, frame in scenarios.items():
            for period, part in frame.groupby(column, dropna=False):
                rows.append(temporal_row(scenario, period_type, str(period), part, int(denominators.get(period, 0))))
    return pd.DataFrame(rows).sort_values(["period_type", "period", "scenario"]).reset_index(drop=True)


def temporal_row(scenario: str, period_type: str, period: str, frame: pd.DataFrame, denominator: int) -> dict[str, object]:
    metrics = trade_metrics(frame)
    return {
        "scenario": scenario,
        "scenario_label": SCENARIOS[scenario],
        "period_type": period_type,
        "period": period,
        "trades": metrics["trades"],
        "coverage": safe_div(metrics["trades"], denominator),
        "avg_r": metrics["avg_r"],
        "total_r": metrics["total_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r": metrics["max_drawdown_r"],
        "win_rate": metrics["win_rate"],
        "buy_trades": int(frame["prediction"].eq("ENTER_BUY").sum()),
        "sell_trades": int(frame["prediction"].eq("ENTER_SELL").sum()),
    }


def build_equity_curves(scenarios: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for scenario, frame in scenarios.items():
        part = frame.sort_values(["timestamp", "symbol", "prediction"]).copy()
        part["scenario"] = scenario
        part["scenario_label"] = SCENARIOS[scenario]
        part["trade_index"] = np.arange(1, len(part) + 1)
        part["equity_r"] = part["realized_R"].cumsum()
        frames.append(part[["scenario", "scenario_label", "trade_index", "timestamp", "symbol", "prediction", "realized_R", "equity_r", "split", "year", "quarter", "month"]])
    return pd.concat(frames, ignore_index=True)


def trade_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    r = pd.to_numeric(frame.get("realized_R", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
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


def markdown_summary(summary: pd.DataFrame, temporal: pd.DataFrame) -> str:
    global_rows = summary[summary["split"].eq("all") & summary["direction"].eq("ALL")].copy()
    test_rows = summary[summary["split"].eq("test") & summary["direction"].eq("ALL")].copy()
    q2_rows = summary[summary["split"].eq("2026Q2")].copy()
    lines = [
        "# MAGI Integration Validation",
        "",
        "## Comparacion global",
        "",
        table(global_rows),
        "",
        "## Test split",
        "",
        table(test_rows),
        "",
        "## 2026Q2",
        "",
        table(q2_rows),
        "",
        "## Temporal breakdown",
        "",
        table(temporal[temporal["period_type"].eq("year")]),
        "",
        "## Conclusion",
        "",
        conclusion_text(test_rows, q2_rows),
    ]
    return "\n".join(lines) + "\n"


def table(frame: pd.DataFrame) -> str:
    cols = ["scenario", "trades", "coverage", "avg_r", "profit_factor", "max_drawdown_r", "win_rate", "total_r"]
    rows = ["| Scenario | Trades | Coverage | Avg R | PF | Max DD | Win rate | Total R |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for _, row in frame[cols].iterrows():
        rows.append(
            f"| `{row['scenario']}` | {int(row['trades']):,} | {row['coverage']:.2%} | "
            f"{row['avg_r']:.4f} | {row['profit_factor']:.4f} | {row['max_drawdown_r']:.2f} | "
            f"{row['win_rate']:.2%} | {row['total_r']:.2f} |"
        )
    return "\n".join(rows)


def conclusion_text(test_rows: pd.DataFrame, q2_rows: pd.DataFrame) -> str:
    best_pf = test_rows.sort_values(["profit_factor", "avg_r"], ascending=False).iloc[0]
    baltasar = test_rows[test_rows["scenario"].eq("A_baltasar_only")].iloc[0]
    improves = best_pf["profit_factor"] > baltasar["profit_factor"] and best_pf["max_drawdown_r"] < baltasar["max_drawdown_r"]
    q2_best = q2_rows.sort_values(["profit_factor", "avg_r"], ascending=False).iloc[0]
    return (
        f"Best test PF is `{best_pf['scenario']}` with PF `{best_pf['profit_factor']:.4f}`, "
        f"Avg R `{best_pf['avg_r']:.4f}` and Max DD `{best_pf['max_drawdown_r']:.2f}`. "
        f"Compared with Baltasar solo PF `{baltasar['profit_factor']:.4f}` and Max DD `{baltasar['max_drawdown_r']:.2f}`, "
        f"the integrated system {'improves' if improves else 'does not clearly improve'} the baseline. "
        f"In 2026Q2, best PF is `{q2_best['scenario']}` with PF `{q2_best['profit_factor']:.4f}`."
    )


def safe_div(num: float, den: float) -> float:
    return round_float(float(num) / float(den)) if den else 0.0


def round_float(value: float) -> float:
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
