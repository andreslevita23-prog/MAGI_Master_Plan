from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_TRADES = Path("data/output/magi_v2/melchor_v2_rule_layer/rule_filtered_trades.csv")
DEFAULT_RULE_METRICS = Path("data/output/magi_v2/melchor_v2_rule_layer/melchor_v2_rule_metrics.json")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/melchor_v2_rule_layer/stability")
DEFAULT_DOC = Path("docs/melchor_v2_rule_stability.md")

EVALUATIONS = [
    ("q2_like_proxy", "BLOCK+CAUTION"),
    ("combined_risk_rule", "BLOCK+CAUTION"),
    ("q2_like_proxy", "BLOCK"),
    ("combined_risk_rule", "BLOCK"),
]
Q2_START = pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
Q2_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trades = read_trades(Path(args.trades))
    rule_metrics = read_json(Path(args.rule_metrics))

    coverage_by_rule = build_coverage_by_rule(trades)
    coverage_by_month = build_period_coverage(trades, period="month")
    coverage_by_quarter = build_period_coverage(trades, period="quarter")

    metrics = {
        "schema_version": "melchor_v2_rule_stability_v0.1",
        "generated_at": utc_now(),
        "inputs": {
            "rule_filtered_trades": str(args.trades),
            "rule_metrics": str(args.rule_metrics),
        },
        "evaluations": [f"{rule}:{mode}" for rule, mode in EVALUATIONS],
        "baseline_original": {
            split: trade_metrics(trades[trades["split"].eq(split)])
            for split in ["validation", "test"]
        },
        "coverage_by_rule": coverage_by_rule.to_dict(orient="records"),
        "period_summary": period_summary(coverage_by_month, coverage_by_quarter),
        "q2_2026": q2_summary(trades),
        "best": best_recommendations(coverage_by_rule, coverage_by_month, coverage_by_quarter),
        "source_rule_layer_best": rule_metrics.get("best", {}),
        "technical_decisions": [
            "No model is trained.",
            "Coverage is measured as retained trades divided by original Baltasar+Gaspar candidates.",
            "Month and quarter fields are used only for reporting stability, not for triggering rules.",
            "2026Q2 is diagnostic only.",
        ],
    }

    coverage_by_rule.to_csv(output_dir / "coverage_by_rule.csv", index=False)
    coverage_by_month.to_csv(output_dir / "coverage_by_month.csv", index=False)
    coverage_by_quarter.to_csv(output_dir / "coverage_by_quarter.csv", index=False)
    (output_dir / "melchor_rule_stability_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = markdown_summary(metrics, coverage_by_rule, coverage_by_month, coverage_by_quarter)
    (output_dir / "melchor_rule_stability_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")

    rec = metrics["best"]["recommended_initial_candidate"]
    print(f"recommended_initial_candidate={rec}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Melchor v2 rule layer coverage and temporal stability.")
    parser.add_argument("--trades", default=str(DEFAULT_TRADES))
    parser.add_argument("--rule-metrics", default=str(DEFAULT_RULE_METRICS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def read_trades(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce").fillna(0.0)
    df["year"] = df["timestamp"].dt.year.astype("Int64")
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)
    df["quarter"] = df["timestamp"].dt.to_period("Q").astype(str)
    for col in df.columns:
        if col.endswith("_blocked_block") or col.endswith("_blocked_caution") or col.endswith("_blocked_block_plus_caution"):
            df[col] = df[col].astype(str).str.lower().eq("true")
    return df


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_coverage_by_rule(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split in ["validation", "test"]:
        split_df = trades[trades["split"].eq(split)]
        baseline = trade_metrics(split_df)
        for rule, mode in EVALUATIONS:
            blocked = blocked_mask(split_df, rule, mode)
            kept = split_df.loc[~blocked]
            item = trade_metrics(kept)
            buy = kept[kept["prediction"].eq("ENTER_BUY")]
            sell = kept[kept["prediction"].eq("ENTER_SELL")]
            rows.append(
                {
                    "split": split,
                    "rule": rule,
                    "mode": mode,
                    "trades_original": len(split_df),
                    "trades_blocked": int(blocked.sum()),
                    "trades_remaining": len(kept),
                    "coverage_retained": safe_div(len(kept), len(split_df)),
                    "avg_r_original": baseline["avg_r"],
                    "avg_r": item["avg_r"],
                    "total_r_original": baseline["total_r"],
                    "total_r": item["total_r"],
                    "pf_original": baseline["profit_factor"],
                    "pf": item["profit_factor"],
                    "max_dd_original": baseline["max_drawdown_r"],
                    "max_dd": item["max_drawdown_r"],
                    "win_rate": item["win_rate"],
                    "buy_original": int(split_df["prediction"].eq("ENTER_BUY").sum()),
                    "buy_retained": int(len(buy)),
                    "buy_retained_share": safe_div(len(buy), int(split_df["prediction"].eq("ENTER_BUY").sum())),
                    "sell_original": int(split_df["prediction"].eq("ENTER_SELL").sum()),
                    "sell_retained": int(len(sell)),
                    "sell_retained_share": safe_div(len(sell), int(split_df["prediction"].eq("ENTER_SELL").sum())),
                }
            )
    return pd.DataFrame(rows)


def build_period_coverage(trades: pd.DataFrame, period: str) -> pd.DataFrame:
    period_col = "month" if period == "month" else "quarter"
    rows = []
    for split in ["validation", "test"]:
        split_df = trades[trades["split"].eq(split)]
        for period_value, period_df in split_df.groupby(period_col, dropna=False):
            baseline = trade_metrics(period_df)
            for rule, mode in EVALUATIONS:
                blocked = blocked_mask(period_df, rule, mode)
                kept = period_df.loc[~blocked]
                item = trade_metrics(kept)
                rows.append(
                    {
                        "split": split,
                        "period_type": period,
                        "period": str(period_value),
                        "rule": rule,
                        "mode": mode,
                        "trades_original": len(period_df),
                        "trades_blocked": int(blocked.sum()),
                        "trades_remaining": len(kept),
                        "coverage_retained": safe_div(len(kept), len(period_df)),
                        "avg_r_original": baseline["avg_r"],
                        "avg_r": item["avg_r"],
                        "total_r_original": baseline["total_r"],
                        "total_r": item["total_r"],
                        "pf_original": baseline["profit_factor"],
                        "pf": item["profit_factor"],
                        "max_dd_original": baseline["max_drawdown_r"],
                        "max_dd": item["max_drawdown_r"],
                        "win_rate": item["win_rate"],
                        "buy_retained": int(kept["prediction"].eq("ENTER_BUY").sum()),
                        "sell_retained": int(kept["prediction"].eq("ENTER_SELL").sum()),
                    }
                )
    return pd.DataFrame(rows)


def period_summary(months: pd.DataFrame, quarters: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for rule, mode in EVALUATIONS:
        key = key_for(rule, mode)
        m = months[(months["rule"].eq(rule)) & (months["mode"].eq(mode))]
        q = quarters[(quarters["rule"].eq(rule)) & (quarters["mode"].eq(mode))]
        summary[key] = {
            "months_total": int(len(m)),
            "months_without_trades": int(m["trades_remaining"].eq(0).sum()),
            "months_under_50_trades": int(m["trades_remaining"].lt(50).sum()),
            "months_under_100_trades": int(m["trades_remaining"].lt(100).sum()),
            "positive_months": int(m["total_r"].gt(0).sum()),
            "negative_months": int(m["total_r"].lt(0).sum()),
            "quarters_total": int(len(q)),
            "quarters_without_trades": int(q["trades_remaining"].eq(0).sum()),
            "quarters_under_100_trades": int(q["trades_remaining"].lt(100).sum()),
            "positive_quarters": int(q["total_r"].gt(0).sum()),
            "negative_quarters": int(q["total_r"].lt(0).sum()),
            "min_monthly_trades": int(m["trades_remaining"].min()) if len(m) else 0,
            "median_monthly_trades": round_float(float(m["trades_remaining"].median())) if len(m) else 0.0,
            "min_quarterly_trades": int(q["trades_remaining"].min()) if len(q) else 0,
            "median_quarterly_trades": round_float(float(q["trades_remaining"].median())) if len(q) else 0.0,
        }
    return summary


def q2_summary(trades: pd.DataFrame) -> dict[str, Any]:
    q2 = trades[trades["timestamp"].between(Q2_START, Q2_END)].copy()
    baseline = trade_metrics(q2)
    out = {"original": baseline}
    for rule, mode in EVALUATIONS:
        blocked = blocked_mask(q2, rule, mode)
        kept = q2.loc[~blocked]
        item = trade_metrics(kept)
        out[key_for(rule, mode)] = {
            "trades_original": len(q2),
            "trades_blocked": int(blocked.sum()),
            "trades_remaining": len(kept),
            "coverage_retained": safe_div(len(kept), len(q2)),
            "filtered": item,
            "avg_r_delta": round_float(item["avg_r"] - baseline["avg_r"]),
            "pf_delta": round_float(item["profit_factor"] - baseline["profit_factor"]),
            "dd_delta": round_float(baseline["max_drawdown_r"] - item["max_drawdown_r"]),
        }
    return out


def best_recommendations(coverage_by_rule: pd.DataFrame, months: pd.DataFrame, quarters: pd.DataFrame) -> dict[str, Any]:
    test = coverage_by_rule[coverage_by_rule["split"].eq("test")].copy()
    test["score"] = (
        test["pf"].rank(pct=True)
        + test["avg_r"].rank(pct=True)
        + (1.0 - test["max_dd"].rank(pct=True))
        + test["coverage_retained"].rank(pct=True)
    )
    best_balanced = test.sort_values("score", ascending=False).iloc[0]
    viable = test[test["coverage_retained"].ge(0.40)].copy()
    best_viable = viable.sort_values(["pf", "avg_r", "coverage_retained"], ascending=False).iloc[0] if len(viable) else best_balanced
    aggressive = test.sort_values(["pf", "avg_r"], ascending=False).iloc[0]
    return {
        "recommended_initial_candidate": key_for(str(best_viable["rule"]), str(best_viable["mode"])),
        "best_balanced": row_to_dict(best_balanced),
        "best_with_min_40pct_coverage": row_to_dict(best_viable),
        "best_aggressive": row_to_dict(aggressive),
        "combined_is_aggressive": bool(
            test[test["rule"].eq("combined_risk_rule") & test["mode"].eq("BLOCK+CAUTION")]["coverage_retained"].iloc[0] < 0.35
        ),
    }


def blocked_mask(df: pd.DataFrame, rule: str, mode: str) -> pd.Series:
    if mode == "BLOCK":
        return df[f"{rule}_blocked_block"].fillna(False)
    if mode == "BLOCK+CAUTION":
        return df[f"{rule}_blocked_block_plus_caution"].fillna(False)
    raise ValueError(f"Unsupported mode for stability validation: {mode}")


def key_for(rule: str, mode: str) -> str:
    return f"{rule}__{mode.lower().replace('+', '_plus_')}"


def row_to_dict(row: pd.Series) -> dict[str, Any]:
    return {k: normalize_value(v) for k, v in row.to_dict().items()}


def normalize_value(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return round_float(float(value))
    if isinstance(value, float):
        return round_float(value)
    return value


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


def markdown_summary(
    metrics: dict[str, Any],
    coverage_by_rule: pd.DataFrame,
    coverage_by_month: pd.DataFrame,
    coverage_by_quarter: pd.DataFrame,
) -> str:
    lines = [
        "# Melchor v2 Rule Stability",
        "",
        "## Scope",
        "",
        "- No model is trained.",
        "- This validates coverage, frequency and temporal stability for candidate Melchor v2 rules.",
        "- Compared rules: `q2_like_proxy` and `combined_risk_rule`, each in `BLOCK` and `BLOCK+CAUTION` modes.",
        "",
        "## Overall Coverage",
        "",
        coverage_table(coverage_by_rule),
        "",
        "## Temporal Stability",
        "",
        stability_table(metrics["period_summary"]),
        "",
        "## 2026Q2",
        "",
        q2_table(metrics["q2_2026"]),
        "",
        "## Recommendation",
        "",
        recommendation_text(metrics),
    ]
    return "\n".join(lines) + "\n"


def coverage_table(frame: pd.DataFrame) -> str:
    rows = [
        "| Split | Rule | Mode | Retained | Coverage | Avg R | Total R | PF | DD | BUY retained | SELL retained |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.sort_values(["split", "rule", "mode"]).iterrows():
        rows.append(
            f"| {row['split']} | `{row['rule']}` | {row['mode']} | {int(row['trades_remaining']):,} | "
            f"{row['coverage_retained']:.2%} | {row['avg_r']:.4f} | {row['total_r']:.2f} | "
            f"{row['pf']:.4f} | {row['max_dd']:.2f} | {int(row['buy_retained']):,} | {int(row['sell_retained']):,} |"
        )
    return "\n".join(rows)


def stability_table(summary: dict[str, Any]) -> str:
    rows = [
        "| Candidate | Months no trades | Months <50 | Median monthly trades | Negative months | Quarters no trades | Quarters <100 | Median quarterly trades | Negative quarters |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, item in summary.items():
        rows.append(
            f"| `{key}` | {item['months_without_trades']} | {item['months_under_50_trades']} | "
            f"{item['median_monthly_trades']:.1f} | {item['negative_months']} | "
            f"{item['quarters_without_trades']} | {item['quarters_under_100_trades']} | "
            f"{item['median_quarterly_trades']:.1f} | {item['negative_quarters']} |"
        )
    return "\n".join(rows)


def q2_table(q2: dict[str, Any]) -> str:
    rows = [
        "| Candidate | Retained | Coverage | Avg R | PF | DD | Avg R delta | PF delta | DD delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, item in q2.items():
        if key == "original":
            continue
        f = item["filtered"]
        rows.append(
            f"| `{key}` | {item['trades_remaining']:,} | {item['coverage_retained']:.2%} | "
            f"{f['avg_r']:.4f} | {f['profit_factor']:.4f} | {f['max_drawdown_r']:.2f} | "
            f"{item['avg_r_delta']:.4f} | {item['pf_delta']:.4f} | {item['dd_delta']:.2f} |"
        )
    return "\n".join(rows)


def recommendation_text(metrics: dict[str, Any]) -> str:
    best = metrics["best"]
    return (
        f"Recommended initial candidate: `{best['recommended_initial_candidate']}`. "
        f"The aggressive benchmark is `{key_for(best['best_aggressive']['rule'], best['best_aggressive']['mode'])}`, "
        "but coverage must be treated as a first-class risk control. "
        f"`combined_risk_rule` in `BLOCK+CAUTION` is marked aggressive: `{best['combined_is_aggressive']}`."
    )


def safe_div(num: float, den: float) -> float:
    return round_float(float(num) / float(den)) if den else 0.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def round_float(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
