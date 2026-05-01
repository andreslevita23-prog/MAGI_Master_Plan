from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_DATASET = Path("data/output/magi_v2/melchor_v2_risk_dataset/melchor_v2_risk_dataset.parquet")
DEFAULT_INTEGRATED = Path("data/output/magi_v2/baltasar_gaspar_v2_integration/integrated_trades.csv")
DEFAULT_Q2_ANALYSIS = Path("data/output/magi_v2/2026q2_regime_analysis/2026q2_regime_analysis.json")
DEFAULT_ML_METRICS = Path("data/output/magi_v2/melchor_v2_risk_classifier/melchor_v2_risk_metrics.json")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/melchor_v2_rule_layer")
DEFAULT_DOC = Path("docs/melchor_v2_rule_layer.md")

Q2_START = pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
Q2_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")
RULES = [
    "rolling_sell_pf_below_1",
    "rolling_pf_below_1_and_drawdown_high",
    "q2_like_proxy",
    "combined_risk_rule",
]
MODES = ["BLOCK", "CAUTION", "BLOCK+CAUTION"]


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = read_dataset(Path(args.dataset))
    thresholds = train_thresholds(df)
    q2_analysis = read_optional_json(Path(args.q2_analysis))
    ml_metrics = read_optional_json(Path(args.ml_metrics))
    integrated_rows = count_integrated_rows(Path(args.integrated_trades))

    df = apply_rules(df, thresholds)

    metrics = build_metrics(df, thresholds, q2_analysis, ml_metrics, integrated_rows)
    metrics_by_rule = metrics_by_rule_frame(metrics)
    metrics_by_quarter = metrics_by_segment(df, segment_column="quarter_label")
    metrics_by_direction = metrics_by_segment(df, segment_column="predicted_direction")

    filtered_cols = [
        "timestamp",
        "symbol",
        "split",
        "prediction",
        "predicted_direction",
        "realized_R",
        "is_2026q2",
    ]
    for rule in RULES:
        filtered_cols.extend([f"{rule}_signal", f"{rule}_blocked_block", f"{rule}_blocked_caution", f"{rule}_blocked_block_plus_caution"])
    df[filtered_cols].to_csv(output_dir / "rule_filtered_trades.csv", index=False)
    metrics_by_rule.to_csv(output_dir / "metrics_by_rule.csv", index=False)
    metrics_by_quarter.to_csv(output_dir / "metrics_by_quarter.csv", index=False)
    metrics_by_direction.to_csv(output_dir / "metrics_by_direction.csv", index=False)
    (output_dir / "melchor_v2_rule_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = markdown_summary(metrics, metrics_by_rule)
    (output_dir / "melchor_v2_rule_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")

    best = metrics["best"]["test"]
    print(f"best_test_rule={best['rule']}")
    print(f"best_test_mode={best['mode']}")
    print(f"test_avg_r={best['filtered']['avg_r']}")
    print(f"test_pf={best['filtered']['profit_factor']}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Melchor v2 rule-aware accumulated risk layer.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--integrated-trades", default=str(DEFAULT_INTEGRATED))
    parser.add_argument("--q2-analysis", default=str(DEFAULT_Q2_ANALYSIS))
    parser.add_argument("--ml-metrics", default=str(DEFAULT_ML_METRICS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def read_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan)
    df["quarter_label"] = df["timestamp"].dt.to_period("Q").astype(str)
    return df.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)


def read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_integrated_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(sum(1 for _ in path.open("r", encoding="utf-8")) - 1)
    except OSError:
        return None


def train_thresholds(df: pd.DataFrame) -> dict[str, float]:
    train = df[df["split"].eq("train")].copy()
    return {
        "rolling_drawdown_50_high": round_float(float(train["rolling_drawdown_50"].quantile(0.75))),
        "rolling_drawdown_100_high": round_float(float(train["rolling_drawdown_100"].quantile(0.75))),
        "rolling_unfavorable_rate_50_high": round_float(float(train["rolling_unfavorable_rate_50"].quantile(0.75))),
        "rolling_unfavorable_rate_100_high": round_float(float(train["rolling_unfavorable_rate_100"].quantile(0.75))),
        "recent_loss_streak_high": round_float(float(train["recent_loss_streak"].quantile(0.90))),
        "recent_sell_loss_streak_high": round_float(float(train["recent_sell_loss_streak"].quantile(0.90))),
    }


def apply_rules(df: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    out = df.copy()
    is_sell = out["predicted_direction"].eq("SELL")
    dd50 = out["rolling_drawdown_50"].ge(thresholds["rolling_drawdown_50_high"])
    dd100 = out["rolling_drawdown_100"].ge(thresholds["rolling_drawdown_100_high"])
    unfavorable50 = out["rolling_unfavorable_rate_50"].ge(thresholds["rolling_unfavorable_rate_50_high"])
    unfavorable100 = out["rolling_unfavorable_rate_100"].ge(thresholds["rolling_unfavorable_rate_100_high"])
    loss_streak = out["recent_loss_streak"].ge(thresholds["recent_loss_streak_high"])
    sell_loss_streak = out["recent_sell_loss_streak"].ge(thresholds["recent_sell_loss_streak_high"])

    rule_masks = {
        "rolling_sell_pf_below_1": {
            "BLOCK": is_sell & out["rolling_sell_pf_50"].lt(1.0),
            "CAUTION": is_sell & (out["rolling_sell_pf_100"].lt(1.0) | out["rolling_sell_avg_R_50"].lt(0.0)),
        },
        "rolling_pf_below_1_and_drawdown_high": {
            "BLOCK": out["rolling_pf_50"].lt(1.0) & dd50,
            "CAUTION": out["rolling_pf_100"].lt(1.0) & dd100,
        },
        "q2_like_proxy": {
            "BLOCK": out["rolling_pf_50"].lt(1.0) & dd50 & unfavorable50,
            "CAUTION": (out["rolling_pf_100"].lt(1.0) & dd100 & unfavorable100) | (is_sell & out["rolling_sell_pf_50"].lt(1.0) & sell_loss_streak),
        },
        "combined_risk_rule": {
            "BLOCK": (out["rolling_pf_50"].lt(1.0) & dd50)
            | (is_sell & out["rolling_sell_pf_50"].lt(1.0))
            | (unfavorable50 & loss_streak),
            "CAUTION": (out["rolling_pf_100"].lt(1.0) & dd100)
            | (is_sell & out["rolling_sell_pf_100"].lt(1.0))
            | (unfavorable100 & sell_loss_streak),
        },
    }

    for rule, masks in rule_masks.items():
        block = masks["BLOCK"].fillna(False)
        caution = masks["CAUTION"].fillna(False) & ~block
        out[f"{rule}_signal"] = np.select([block, caution], ["BLOCK", "CAUTION"], default="APPROVE")
        out[f"{rule}_blocked_block"] = block
        out[f"{rule}_blocked_caution"] = caution
        out[f"{rule}_blocked_block_plus_caution"] = block | caution
    return out


def build_metrics(
    df: pd.DataFrame,
    thresholds: dict[str, float],
    q2_analysis: dict[str, Any],
    ml_metrics: dict[str, Any],
    integrated_rows: int | None,
) -> dict[str, Any]:
    rule_results: dict[str, Any] = {}
    for split in ["validation", "test"]:
        split_df = df[df["split"].eq(split)].copy()
        rule_results[split] = {}
        for rule in RULES:
            rule_results[split][rule] = {}
            for mode in MODES:
                rule_results[split][rule][mode] = evaluate_rule(split_df, rule, mode)

    q2_df = df[df["timestamp"].between(Q2_START, Q2_END)].copy()
    q2_results = {
        rule: {mode: evaluate_rule(q2_df, rule, mode) for mode in MODES}
        for rule in RULES
    }

    return {
        "schema_version": "melchor_v2_rule_layer_v0.1",
        "generated_at": utc_now(),
        "inputs": {
            "melchor_dataset": str(DEFAULT_DATASET),
            "integrated_trades_rows": integrated_rows,
            "q2_analysis_loaded": bool(q2_analysis),
            "ml_metrics_loaded": bool(ml_metrics),
        },
        "rule_thresholds_from_train": thresholds,
        "rule_definitions": rule_definitions(thresholds),
        "rows": {
            "train": int(df["split"].eq("train").sum()),
            "validation": int(df["split"].eq("validation").sum()),
            "test": int(df["split"].eq("test").sum()),
        },
        "baseline_original": {
            "validation": trade_metrics(df[df["split"].eq("validation")]),
            "test": trade_metrics(df[df["split"].eq("test")]),
            "q2_2026": trade_metrics(q2_df),
        },
        "rules": rule_results,
        "q2_2026": q2_results,
        "best": {
            "validation": best_result(rule_results["validation"]),
            "test": best_result(rule_results["test"]),
            "q2_2026": best_result(q2_results),
        },
        "melchor_ml_baseline": compact_ml_baseline(ml_metrics),
        "technical_decisions": [
            "Rules use natural PF < 1 risk cuts and high-risk thresholds estimated from train only.",
            "No model is trained in this script.",
            "No date, month, quarter or 2026Q2 flag is used to trigger a rule.",
            "The 2026Q2 analysis is loaded for comparison only, not for rule execution.",
            "BLOCK mode blocks only strong rule hits; CAUTION blocks only warning hits; BLOCK+CAUTION blocks both.",
        ],
    }


def rule_definitions(thresholds: dict[str, float]) -> dict[str, str]:
    return {
        "rolling_sell_pf_below_1": "BLOCK when predicted_direction is SELL and rolling_sell_pf_50 < 1. CAUTION when SELL and rolling_sell_pf_100 < 1 or rolling_sell_avg_R_50 < 0.",
        "rolling_pf_below_1_and_drawdown_high": f"BLOCK when rolling_pf_50 < 1 and rolling_drawdown_50 >= {thresholds['rolling_drawdown_50_high']}. CAUTION uses rolling_pf_100 < 1 and rolling_drawdown_100 >= {thresholds['rolling_drawdown_100_high']}.",
        "q2_like_proxy": f"BLOCK when rolling_pf_50 < 1, rolling_drawdown_50 >= {thresholds['rolling_drawdown_50_high']} and rolling_unfavorable_rate_50 >= {thresholds['rolling_unfavorable_rate_50_high']}. CAUTION adds slower 100-window deterioration or SELL PF deterioration with high sell loss streak.",
        "combined_risk_rule": "BLOCK when global PF+drawdown deteriorates, or SELL PF < 1 during SELL, or unfavorable rate plus loss streak is high. CAUTION uses slower 100-window versions.",
    }


def evaluate_rule(df: pd.DataFrame, rule: str, mode: str) -> dict[str, Any]:
    if mode == "BLOCK":
        blocked = df[f"{rule}_blocked_block"].fillna(False)
    elif mode == "CAUTION":
        blocked = df[f"{rule}_blocked_caution"].fillna(False)
    elif mode == "BLOCK+CAUTION":
        blocked = df[f"{rule}_blocked_block_plus_caution"].fillna(False)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    remaining = df.loc[~blocked].copy()
    blocked_df = df.loc[blocked].copy()
    return {
        "original": trade_metrics(df),
        "trades_original": int(len(df)),
        "trades_blocked": int(blocked.sum()),
        "blocked_share": round_float(float(blocked.mean()) if len(df) else 0.0),
        "trades_remaining": int(len(remaining)),
        "filtered": trade_metrics(remaining),
        "blocked": trade_metrics(blocked_df),
        "impact_buy": direction_impact(df, remaining, "ENTER_BUY"),
        "impact_sell": direction_impact(df, remaining, "ENTER_SELL"),
    }


def best_result(results: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for rule, modes in results.items():
        for mode, item in modes.items():
            original = item["original"]
            filtered = item["filtered"]
            candidates.append(
                {
                    "rule": rule,
                    "mode": mode,
                    "avg_r_delta": round_float(filtered["avg_r"] - original["avg_r"]),
                    "pf_delta": round_float(filtered["profit_factor"] - original["profit_factor"]),
                    "dd_delta": round_float(original["max_drawdown_r"] - filtered["max_drawdown_r"]),
                    "trades_blocked": item["trades_blocked"],
                    "blocked_share": item["blocked_share"],
                    "filtered": filtered,
                    "original": original,
                }
            )
    return max(candidates, key=lambda item: (item["avg_r_delta"], item["pf_delta"], item["dd_delta"]))


def compact_ml_baseline(metrics: dict[str, Any]) -> dict[str, Any]:
    if not metrics:
        return {}
    return {
        "validation": {
            "classification": metrics.get("classification", {}).get("validation", {}),
            "filter_simulation": metrics.get("filter_simulation", {}).get("validation", {}),
        },
        "test": {
            "classification": metrics.get("classification", {}).get("test", {}),
            "filter_simulation": metrics.get("filter_simulation", {}).get("test", {}),
        },
        "q2_2026": metrics.get("q2_2026", {}),
    }


def metrics_by_rule_frame(metrics: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for split, rule_data in metrics["rules"].items():
        for rule, modes in rule_data.items():
            for mode, item in modes.items():
                rows.append(flatten_metric_row(split, rule, mode, item))
    for rule, modes in metrics["q2_2026"].items():
        for mode, item in modes.items():
            rows.append(flatten_metric_row("2026Q2", rule, mode, item))
    return pd.DataFrame(rows)


def flatten_metric_row(split: str, rule: str, mode: str, item: dict[str, Any]) -> dict[str, Any]:
    original = item["original"]
    filtered = item["filtered"]
    return {
        "split": split,
        "rule": rule,
        "mode": mode,
        "trades_original": item["trades_original"],
        "trades_blocked": item["trades_blocked"],
        "blocked_share": item["blocked_share"],
        "trades_remaining": item["trades_remaining"],
        "avg_r_original": original["avg_r"],
        "avg_r_filtered": filtered["avg_r"],
        "avg_r_delta": round_float(filtered["avg_r"] - original["avg_r"]),
        "pf_original": original["profit_factor"],
        "pf_filtered": filtered["profit_factor"],
        "pf_delta": round_float(filtered["profit_factor"] - original["profit_factor"]),
        "dd_original": original["max_drawdown_r"],
        "dd_filtered": filtered["max_drawdown_r"],
        "dd_delta": round_float(original["max_drawdown_r"] - filtered["max_drawdown_r"]),
        "total_r_original": original["total_r"],
        "total_r_filtered": filtered["total_r"],
    }


def metrics_by_segment(df: pd.DataFrame, segment_column: str) -> pd.DataFrame:
    rows = []
    for split in ["validation", "test"]:
        split_df = df[df["split"].eq(split)].copy()
        for segment_value, segment_df in split_df.groupby(segment_column, dropna=False):
            for rule in RULES:
                for mode in MODES:
                    item = evaluate_rule(segment_df, rule, mode)
                    row = flatten_metric_row(split, rule, mode, item)
                    row["segment_column"] = segment_column
                    row["segment_value"] = str(segment_value)
                    rows.append(row)
    return pd.DataFrame(rows)


def direction_impact(original: pd.DataFrame, remaining: pd.DataFrame, direction: str) -> dict[str, Any]:
    original_part = original[original["prediction"].eq(direction)]
    remaining_part = remaining[remaining["prediction"].eq(direction)]
    return {
        "original": trade_metrics(original_part),
        "filtered": trade_metrics(remaining_part),
        "blocked": int(len(original_part) - len(remaining_part)),
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


def markdown_summary(metrics: dict[str, Any], metrics_by_rule: pd.DataFrame) -> str:
    lines = [
        "# Melchor v2 Rule-Aware Risk Layer",
        "",
        "## Scope",
        "",
        "- No model is trained.",
        "- Rules use accumulated operational risk available before each trade.",
        "- Objective: compare explicit risk blocking against the Melchor v2 ML baseline.",
        "",
        "## Thresholds",
        "",
        threshold_table(metrics["rule_thresholds_from_train"]),
        "",
        "## Validation/Test Summary",
        "",
        top_rule_table(metrics_by_rule[metrics_by_rule["split"].isin(["validation", "test"])]),
        "",
        "## 2026Q2 Impact",
        "",
        top_rule_table(metrics_by_rule[metrics_by_rule["split"].eq("2026Q2")]),
        "",
        "## Best Results",
        "",
        best_table(metrics),
        "",
        "## Comparison Against ML Baseline",
        "",
        ml_comparison(metrics),
        "",
        "## Interpretation",
        "",
        interpretation(metrics),
    ]
    return "\n".join(lines) + "\n"


def threshold_table(thresholds: dict[str, float]) -> str:
    rows = ["| Threshold | Value |", "| --- | ---: |"]
    for key, value in thresholds.items():
        rows.append(f"| `{key}` | {value:.4f} |")
    return "\n".join(rows)


def top_rule_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    view = frame.sort_values(["split", "avg_r_delta", "pf_delta", "dd_delta"], ascending=[True, False, False, False]).head(16)
    rows = [
        "| Split | Rule | Mode | Blocked | Avg R | PF | DD | Avg R delta | PF delta | DD delta |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in view.iterrows():
        rows.append(
            f"| {row['split']} | `{row['rule']}` | {row['mode']} | {int(row['trades_blocked']):,} | "
            f"{row['avg_r_filtered']:.4f} | {row['pf_filtered']:.4f} | {row['dd_filtered']:.2f} | "
            f"{row['avg_r_delta']:.4f} | {row['pf_delta']:.4f} | {row['dd_delta']:.2f} |"
        )
    return "\n".join(rows)


def best_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Split | Rule | Mode | Blocked | Avg R | PF | DD | Avg R delta | PF delta | DD delta |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ["validation", "test", "q2_2026"]:
        item = metrics["best"][split]
        filtered = item["filtered"]
        rows.append(
            f"| {split} | `{item['rule']}` | {item['mode']} | {item['trades_blocked']:,} | "
            f"{filtered['avg_r']:.4f} | {filtered['profit_factor']:.4f} | {filtered['max_drawdown_r']:.2f} | "
            f"{item['avg_r_delta']:.4f} | {item['pf_delta']:.4f} | {item['dd_delta']:.2f} |"
        )
    return "\n".join(rows)


def ml_comparison(metrics: dict[str, Any]) -> str:
    ml = metrics.get("melchor_ml_baseline", {})
    if not ml:
        return "_Melchor ML metrics were not available._"
    rows = [
        "| Split | ML mode | Blocked | Avg R | PF | DD |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for split in ["validation", "test"]:
        for mode, item in ml.get(split, {}).get("filter_simulation", {}).items():
            filtered = item.get("filtered", {})
            rows.append(
                f"| {split} | {mode} | {item.get('trades_blocked', 0):,} | "
                f"{filtered.get('avg_r', 0.0):.4f} | {filtered.get('profit_factor', 0.0):.4f} | "
                f"{filtered.get('max_drawdown_r', 0.0):.2f} |"
            )
    return "\n".join(rows)


def interpretation(metrics: dict[str, Any]) -> str:
    best_test = metrics["best"]["test"]
    best_q2 = metrics["best"]["q2_2026"]
    return (
        f"Best test rule is `{best_test['rule']}` in `{best_test['mode']}` mode. "
        f"It changes test avg R by `{best_test['avg_r_delta']:.4f}`, PF by `{best_test['pf_delta']:.4f}` "
        f"and DD by `{best_test['dd_delta']:.2f}`. For 2026Q2, best rule is `{best_q2['rule']}` "
        f"in `{best_q2['mode']}` mode, changing avg R by `{best_q2['avg_r_delta']:.4f}` and PF by "
        f"`{best_q2['pf_delta']:.4f}`. Treat this as a risk-control comparison, not proof of production profitability."
    )


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
