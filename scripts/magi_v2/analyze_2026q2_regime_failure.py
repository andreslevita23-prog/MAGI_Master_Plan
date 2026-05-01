from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_INTEGRATED = Path("data/output/magi_v2/baltasar_gaspar_v2_integration/integrated_trades.csv")
DEFAULT_ROLLING = Path("data/output/magi_v2/gaspar_v2_1c_rolling_dataset/gaspar_v2_1c_rolling_dataset.parquet")
DEFAULT_RICH = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/2026q2_regime_analysis")
DEFAULT_DOC = Path("docs/2026q2_regime_failure_analysis.md")

Q2_START = pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
Q2_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")
GOOD_PERIODS = {
    "2025Q4": (pd.Timestamp("2025-10-01 00:00:00", tz="UTC"), pd.Timestamp("2025-12-31 23:59:59", tz="UTC")),
    "2026Q1": (pd.Timestamp("2026-01-01 00:00:00", tz="UTC"), pd.Timestamp("2026-03-31 23:59:59", tz="UTC")),
}


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    integrated = read_integrated(Path(args.integrated_trades))
    rolling = read_rolling(Path(args.rolling_dataset))
    rich = read_rich(Path(args.rich_features))
    df = enrich_with_rich(integrated, rolling, rich)
    add_buckets(df)

    q2 = df[df["timestamp"].between(Q2_START, Q2_END)].copy()
    comparisons = {"2026Q2": period_summary(q2)}
    for name, (start, end) in GOOD_PERIODS.items():
        comparisons[name] = period_summary(df[df["timestamp"].between(start, end)].copy())

    comparison_rows = comparison_table_rows(df)
    pd.DataFrame(comparison_rows).to_csv(output_dir / "comparison_2026q2_vs_good_periods.csv", index=False)

    bad_contexts = bad_contexts_2026q2(q2)
    bad_contexts.to_csv(output_dir / "bad_contexts_2026q2.csv", index=False)

    rules = candidate_rules(df, q2)
    analysis = {
        "schema_version": "2026q2_regime_failure_analysis_v0.1",
        "generated_at": utc_now(),
        "inputs": {
            "integrated_trades": str(args.integrated_trades),
            "rolling_dataset": str(args.rolling_dataset),
            "rich_features": str(args.rich_features),
        },
        "periods": comparisons,
        "feature_comparison": comparison_rows,
        "bad_contexts_2026q2": bad_contexts.to_dict(orient="records"),
        "gaspar_probability": gaspar_probability_analysis(q2),
        "candidate_rules": rules,
        "technical_decisions": [
            "This is diagnostic only; no production rule is applied.",
            "Good periods are 2025Q4 and 2026Q1 for contrast.",
            "Rule impact is estimated on already-selected Baltasar v2 trades, not on the full market.",
        ],
    }
    (output_dir / "2026q2_regime_analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = markdown_summary(analysis)
    (output_dir / "2026q2_regime_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")

    print(f"q2_trades={len(q2)}")
    print(f"q2_avg_r={analysis['periods']['2026Q2']['avg_r']}")
    print(f"rules={len(rules)}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze 2026Q2 regime failure.")
    parser.add_argument("--integrated-trades", default=str(DEFAULT_INTEGRATED))
    parser.add_argument("--rolling-dataset", default=str(DEFAULT_ROLLING))
    parser.add_argument("--rich-features", default=str(DEFAULT_RICH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_integrated(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df


def read_rolling(path: Path) -> pd.DataFrame:
    columns = [
        "timestamp",
        "symbol",
        "prediction",
        "rolling_avg_R_50",
        "rolling_avg_R_100",
        "rolling_pf_50",
        "rolling_pf_100",
        "rolling_sell_avg_R_50",
        "rolling_sell_avg_R_100",
        "rolling_sell_pf_50",
        "rolling_sell_pf_100",
        "rolling_drawdown_50",
        "rolling_drawdown_100",
        "rolling_unfavorable_rate_50",
        "rolling_unfavorable_rate_100",
        "recent_loss_streak",
        "recent_sell_loss_streak",
        "rolling_2026q2_like_proxy",
    ]
    df = pd.read_parquet(path, columns=columns)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df.drop_duplicates(["timestamp", "symbol", "prediction"])


def read_rich(path: Path) -> pd.DataFrame:
    columns = [
        "timestamp",
        "symbol",
        "session",
        "hour",
        "atr",
        "daily_range_position",
        "regime",
        "volatility_12",
        "ema_20_50_distance",
        "ema_50_200_distance",
        "close_to_ema20",
        "close_to_ema50",
        "close_to_ema200",
        "rsi_14",
        "momentum",
        "market_structure",
        "structure_direction",
        "h4_market_structure",
        "h4_structure_direction",
        "d1_market_structure",
        "d1_structure_direction",
        "mtf_alignment_status",
        "htf_directional_alignment",
    ]
    df = pd.read_parquet(path, columns=columns)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df.drop_duplicates(["timestamp", "symbol"])


def enrich_with_rich(integrated: pd.DataFrame, rolling: pd.DataFrame, rich: pd.DataFrame) -> pd.DataFrame:
    roll_cols = [c for c in rolling.columns if c not in {"timestamp", "symbol", "prediction"}]
    rich_cols = [c for c in rich.columns if c not in {"timestamp", "symbol"}]
    df = integrated.merge(rolling, on=["timestamp", "symbol", "prediction"], how="left", suffixes=("", "_roll"))
    df = df.merge(rich, on=["timestamp", "symbol"], how="left", suffixes=("", "_rich"))
    for column in roll_cols + rich_cols:
        if column in df.columns:
            converted = pd.to_numeric(df[column], errors="coerce")
            if converted.notna().sum() > 0:
                df[column] = converted
    return df


def add_buckets(df: pd.DataFrame) -> None:
    df["direction"] = df["prediction"].map({"ENTER_BUY": "BUY", "ENTER_SELL": "SELL"}).fillna("NONE")
    df["atr_bucket"] = pd.qcut(pd.to_numeric(df["atr"], errors="coerce"), q=4, duplicates="drop").astype(str)
    df["daily_range_bucket"] = pd.cut(
        pd.to_numeric(df["daily_range_position"], errors="coerce"),
        bins=[-math.inf, 0.15, 0.35, 0.65, 0.85, math.inf],
        labels=["low", "mid_low", "mid", "mid_high", "extreme_high"],
    ).astype(str)


def period_summary(df: pd.DataFrame) -> dict[str, Any]:
    return {
        **trade_metrics(df),
        "direction_distribution": value_counts(df["direction"]),
        "session_distribution": value_counts(df.get("session", pd.Series(dtype=str))),
        "hour_distribution": value_counts(df.get("hour", pd.Series(dtype=str))),
        "daily_range_bucket_distribution": value_counts(df.get("daily_range_bucket", pd.Series(dtype=str))),
        "h4_structure_distribution": value_counts(df.get("h4_market_structure", pd.Series(dtype=str))),
        "d1_structure_distribution": value_counts(df.get("d1_market_structure", pd.Series(dtype=str))),
        "gaspar_blocked": int(df.get("gaspar_block", pd.Series(dtype=bool)).sum()),
        "gaspar_block_rate": round_float(float(df.get("gaspar_block", pd.Series(dtype=bool)).mean())) if len(df) else 0.0,
        "p_deteriorating_mean": round_float(pd.to_numeric(df.get("gaspar_p_deteriorating", pd.Series(dtype=float)), errors="coerce").mean()),
        "rolling_2026q2_like_proxy_rate": round_float(pd.to_numeric(df.get("rolling_2026q2_like_proxy", pd.Series(dtype=float)), errors="coerce").mean()),
    }


def comparison_table_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    periods = {"2026Q2": (Q2_START, Q2_END), **GOOD_PERIODS}
    numeric_features = [
        "realized_R",
        "gaspar_p_deteriorating",
        "atr",
        "daily_range_position",
        "volatility_12",
        "ema_20_50_distance",
        "ema_50_200_distance",
        "close_to_ema20",
        "close_to_ema50",
        "close_to_ema200",
        "rsi_14",
        "momentum",
        "rolling_avg_R_50",
        "rolling_pf_50",
        "rolling_sell_avg_R_50",
        "rolling_sell_pf_50",
        "rolling_drawdown_50",
        "rolling_unfavorable_rate_50",
        "recent_loss_streak",
        "recent_sell_loss_streak",
    ]
    rows = []
    for feature in numeric_features:
        row = {"feature": feature}
        for name, (start, end) in periods.items():
            part = df[df["timestamp"].between(start, end)]
            values = pd.to_numeric(part.get(feature, pd.Series(dtype=float)), errors="coerce")
            row[f"{name}_mean"] = round_float(values.mean())
            row[f"{name}_median"] = round_float(values.median())
        rows.append(row)
    return rows


def bad_contexts_2026q2(q2: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["direction", "session", "daily_range_bucket", "h4_market_structure", "d1_market_structure"]
    rows = []
    for keys, group in q2.groupby(group_cols, dropna=False):
        metrics = trade_metrics(group)
        row = dict(zip(group_cols, keys, strict=False))
        row.update(metrics)
        row["gaspar_blocked"] = int(group["gaspar_block"].sum())
        row["gaspar_block_rate"] = round_float(float(group["gaspar_block"].mean())) if len(group) else 0.0
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["avg_r", "trades"], ascending=[True, False]).head(30)


def gaspar_probability_analysis(q2: pd.DataFrame) -> dict[str, Any]:
    p = pd.to_numeric(q2.get("gaspar_p_deteriorating", pd.Series(dtype=float)), errors="coerce")
    return {
        "mean": round_float(p.mean()),
        "median": round_float(p.median()),
        "p90": round_float(p.quantile(0.90)),
        "max": round_float(p.max()),
        "share_ge_050": round_float(float((p >= 0.50).mean())) if len(p) else 0.0,
        "share_ge_040": round_float(float((p >= 0.40).mean())) if len(p) else 0.0,
        "share_ge_030": round_float(float((p >= 0.30).mean())) if len(p) else 0.0,
    }


def candidate_rules(df: pd.DataFrame, q2: pd.DataFrame) -> list[dict[str, Any]]:
    rules = {
        "q2_like_proxy": lambda x: pd.to_numeric(x["rolling_2026q2_like_proxy"], errors="coerce").fillna(0).eq(1),
        "sell_mid_high_h4_breakout_or_range": lambda x: x["direction"].eq("SELL")
        & x["daily_range_bucket"].isin(["mid", "mid_high"])
        & x["h4_market_structure"].isin(["breakout", "range"]),
        "sell_low_gaspar_prob_030": lambda x: x["direction"].eq("SELL")
        & (pd.to_numeric(x["gaspar_p_deteriorating"], errors="coerce") >= 0.30),
        "rolling_sell_pf_below_1": lambda x: pd.to_numeric(x["rolling_sell_pf_50"], errors="coerce") < 1.0,
        "rolling_pf_below_1_and_drawdown_high": lambda x: (pd.to_numeric(x["rolling_pf_50"], errors="coerce") < 1.0)
        & (pd.to_numeric(x["rolling_drawdown_50"], errors="coerce") > 20),
    }
    rows = []
    for name, fn in rules.items():
        rows.append(rule_impact(name, df, q2, fn))
    return rows


def rule_impact(name: str, df: pd.DataFrame, q2: pd.DataFrame, fn: Any) -> dict[str, Any]:
    test = df[df["split"].eq("test")]
    q2_mask = fn(q2)
    test_mask = fn(test)
    return {
        "rule": name,
        "q2_blocked": int(q2_mask.sum()),
        "q2_blocked_share": round_float(float(q2_mask.mean())) if len(q2_mask) else 0.0,
        "q2_original": trade_metrics(q2),
        "q2_filtered": trade_metrics(q2.loc[~q2_mask]),
        "test_blocked": int(test_mask.sum()),
        "test_blocked_share": round_float(float(test_mask.mean())) if len(test_mask) else 0.0,
        "test_original": trade_metrics(test),
        "test_filtered": trade_metrics(test.loc[~test_mask]),
    }


def trade_metrics(df: pd.DataFrame) -> dict[str, Any]:
    r = pd.to_numeric(df.get("realized_R", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
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


def markdown_summary(analysis: dict[str, Any]) -> str:
    lines = [
        "# 2026Q2 Regime Failure Analysis",
        "",
        "## Period Performance",
        "",
        period_table(analysis["periods"]),
        "",
        "## Gaspar Probability in 2026Q2",
        "",
        dict_table(analysis["gaspar_probability"]),
        "",
        "## Candidate Rule Impact",
        "",
        rule_table(analysis["candidate_rules"]),
        "",
        "## Worst 2026Q2 Contexts",
        "",
        bad_context_table(analysis["bad_contexts_2026q2"]),
        "",
        "## Interpretation",
        "",
        interpretation(analysis),
    ]
    return "\n".join(lines) + "\n"


def period_table(periods: dict[str, Any]) -> str:
    rows = ["| Period | Trades | Avg R | Total R | PF | Max DD | Gaspar block rate | P(det) mean | Q2-like proxy |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name, item in periods.items():
        rows.append(
            f"| {name} | {item['trades']:,} | {item['avg_r']:.4f} | {item['total_r']:.2f} | "
            f"{item['profit_factor']:.4f} | {item['max_drawdown_r']:.2f} | {item['gaspar_block_rate']:.4f} | "
            f"{item['p_deteriorating_mean']:.4f} | {item['rolling_2026q2_like_proxy_rate']:.4f} |"
        )
    return "\n".join(rows)


def dict_table(item: dict[str, Any]) -> str:
    rows = ["| Metric | Value |", "| --- | ---: |"]
    for key, value in item.items():
        rows.append(f"| {key} | {value} |")
    return "\n".join(rows)


def rule_table(rules: list[dict[str, Any]]) -> str:
    rows = [
        "| Rule | Q2 blocked | Q2 Avg R filtered | Q2 PF filtered | Test blocked | Test Avg R filtered | Test PF filtered | Test DD filtered |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rule in rules:
        rows.append(
            f"| {rule['rule']} | {rule['q2_blocked']:,} | {rule['q2_filtered']['avg_r']:.4f} | "
            f"{rule['q2_filtered']['profit_factor']:.4f} | {rule['test_blocked']:,} | "
            f"{rule['test_filtered']['avg_r']:.4f} | {rule['test_filtered']['profit_factor']:.4f} | "
            f"{rule['test_filtered']['max_drawdown_r']:.2f} |"
        )
    return "\n".join(rows)


def bad_context_table(rows_payload: list[dict[str, Any]]) -> str:
    if not rows_payload:
        return "_No bad contexts._"
    rows = [
        "| Direction | Session | Range | H4 | D1 | Trades | Avg R | PF | DD | Gaspar block rate |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in rows_payload[:12]:
        rows.append(
            f"| {item.get('direction')} | {item.get('session')} | {item.get('daily_range_bucket')} | "
            f"{item.get('h4_market_structure')} | {item.get('d1_market_structure')} | {item.get('trades')} | "
            f"{item.get('avg_r'):.4f} | {item.get('profit_factor'):.4f} | {item.get('max_drawdown_r'):.2f} | "
            f"{item.get('gaspar_block_rate'):.4f} |"
        )
    return "\n".join(rows)


def interpretation(analysis: dict[str, Any]) -> str:
    q2 = analysis["periods"]["2026Q2"]
    good_2026q1 = analysis["periods"]["2026Q1"]
    gaspar = analysis["gaspar_probability"]
    return (
        f"2026Q2 is a small but negative slice: avg R `{q2['avg_r']:.4f}` and PF `{q2['profit_factor']:.4f}`, "
        f"versus 2026Q1 avg R `{good_2026q1['avg_r']:.4f}` and PF `{good_2026q1['profit_factor']:.4f}`. "
        f"Gaspar did not block it because P(DETERIORATING) stayed low: mean `{gaspar['mean']:.4f}`, max "
        f"`{gaspar['max']:.4f}`, and share >= 0.50 `{gaspar['share_ge_050']:.4f}`. "
        "The strongest simple candidates are diagnostic only and should be tested in a dedicated detector or Melchor v2 risk layer."
    )


def value_counts(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.fillna("NULL").value_counts(dropna=False).to_dict().items()}


def round_float(value: float | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
