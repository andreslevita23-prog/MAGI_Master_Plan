from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


DEFAULT_POLICY_METRICS = Path(
    "data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/policy_medium_r_metrics.json"
)
DEFAULT_GASPAR_MODEL = Path("data/output/magi_v2/gaspar_v2_1c_rolling_classifier/gaspar_v2_1c_model.joblib")
DEFAULT_ROLLING_DATASET = Path("data/output/magi_v2/gaspar_v2_1c_rolling_dataset/gaspar_v2_1c_rolling_dataset.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/baltasar_gaspar_v2_integration")
DEFAULT_DOC = Path("docs/baltasar_gaspar_v2_integration.md")

GASPAR_BLOCK_THRESHOLD = 0.50
Q2_START = pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
Q2_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    policy_metrics = json.loads(Path(args.policy_metrics).read_text(encoding="utf-8"))
    gaspar_payload = joblib.load(args.gaspar_model)
    df = read_dataset(Path(args.rolling_dataset))
    features = list(gaspar_payload["features"])
    pipeline = gaspar_payload["pipeline"]

    proba = pipeline.predict_proba(df[features])
    classes = list(pipeline.named_steps["model"].classes_)
    deteriorating_idx = classes.index("DETERIORATING")
    df["gaspar_p_deteriorating"] = proba[:, deteriorating_idx]
    df["gaspar_block"] = df["gaspar_p_deteriorating"] >= GASPAR_BLOCK_THRESHOLD
    df["system"] = "baltasar_v2_gaspar_v21c"
    integrated = df[~df["gaspar_block"]].copy()

    df.to_csv(output_dir / "integrated_trades.csv", index=False)

    by_year = grouped_metrics(df, integrated, "year")
    by_quarter = grouped_metrics(df, integrated, "quarter")
    by_month = grouped_metrics(df, integrated, "month")
    by_direction = direction_metrics(df, integrated)
    pd.DataFrame(by_year).to_csv(output_dir / "metrics_by_year.csv", index=False)
    pd.DataFrame(by_quarter).to_csv(output_dir / "metrics_by_quarter.csv", index=False)
    pd.DataFrame(by_month).to_csv(output_dir / "metrics_by_month.csv", index=False)
    pd.DataFrame(by_direction).to_csv(output_dir / "metrics_by_direction.csv", index=False)

    metrics = {
        "schema_version": "baltasar_gaspar_v2_integration_v0.1",
        "generated_at": utc_now(),
        "gaspar_block_threshold": GASPAR_BLOCK_THRESHOLD,
        "inputs": {
            "policy_metrics": str(args.policy_metrics),
            "gaspar_model": str(args.gaspar_model),
            "rolling_dataset": str(args.rolling_dataset),
        },
        "validation": split_comparison(df, integrated, "validation"),
        "test": split_comparison(df, integrated, "test"),
        "q2_2026": q2_diagnostic(df, integrated),
        "temporal": {
            "year": by_year,
            "quarter": by_quarter,
            "month": by_month,
            "direction": by_direction,
        },
        "baltasar_v1_baseline": extract_baltasar_v1(policy_metrics),
        "baltasar_v2_solo_from_policy_metrics": extract_baltasar_v2_medium(policy_metrics),
        "technical_decisions": [
            "No models are trained in this integration evaluation.",
            "Baltasar v2 rich_policy_medium threshold 0.40 is represented by the full rolling dataset rows.",
            "Gaspar v2.1c blocks when P(DETERIORATING) >= 0.50.",
            "Integrated trades CSV contains both blocked and retained trades with gaspar_block flag.",
        ],
    }

    (output_dir / "integration_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = markdown_summary(metrics)
    (output_dir / "integration_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(summary, encoding="utf-8")

    print(f"output_dir={output_dir}")
    print(f"validation={metrics['validation']['integrated']['avg_r']} pf={metrics['validation']['integrated']['profit_factor']}")
    print(f"test={metrics['test']['integrated']['avg_r']} pf={metrics['test']['integrated']['profit_factor']}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Baltasar v2 + Gaspar v2.1c integration.")
    parser.add_argument("--policy-metrics", default=str(DEFAULT_POLICY_METRICS))
    parser.add_argument("--gaspar-model", default=str(DEFAULT_GASPAR_MODEL))
    parser.add_argument("--rolling-dataset", default=str(DEFAULT_ROLLING_DATASET))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan)
    df["year"] = df["timestamp"].dt.year.astype(str)
    naive = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
    df["quarter"] = naive.dt.to_period("Q").astype(str)
    df["month"] = naive.dt.to_period("M").astype(str)
    return df.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)


def split_comparison(original: pd.DataFrame, integrated: pd.DataFrame, split: str) -> dict[str, Any]:
    base = original[original["split"].eq(split)]
    kept = integrated[integrated["split"].eq(split)]
    blocked = base[base["gaspar_block"]]
    return {
        "baltasar_v2_solo": trade_metrics(base),
        "integrated": trade_metrics(kept),
        "blocked": trade_metrics(blocked),
        "blocked_trades": int(len(blocked)),
        "blocked_share": round_float(len(blocked) / len(base)) if len(base) else 0.0,
        "direction": {
            "BUY": {
                "solo": trade_metrics(base[base["prediction"].eq("ENTER_BUY")]),
                "integrated": trade_metrics(kept[kept["prediction"].eq("ENTER_BUY")]),
                "blocked": int(base[base["prediction"].eq("ENTER_BUY")]["gaspar_block"].sum()),
            },
            "SELL": {
                "solo": trade_metrics(base[base["prediction"].eq("ENTER_SELL")]),
                "integrated": trade_metrics(kept[kept["prediction"].eq("ENTER_SELL")]),
                "blocked": int(base[base["prediction"].eq("ENTER_SELL")]["gaspar_block"].sum()),
            },
        },
    }


def q2_diagnostic(original: pd.DataFrame, integrated: pd.DataFrame) -> dict[str, Any]:
    base = original[original["timestamp"].between(Q2_START, Q2_END)]
    kept = integrated[integrated["timestamp"].between(Q2_START, Q2_END)]
    blocked = base[base["gaspar_block"]]
    return {
        "baltasar_v2_solo": trade_metrics(base),
        "integrated": trade_metrics(kept),
        "blocked": trade_metrics(blocked),
        "blocked_trades": int(len(blocked)),
        "blocked_share": round_float(len(blocked) / len(base)) if len(base) else 0.0,
    }


def grouped_metrics(original: pd.DataFrame, integrated: pd.DataFrame, group: str) -> list[dict[str, Any]]:
    rows = []
    for split in ["validation", "test"]:
        base_split = original[original["split"].eq(split)]
        kept_split = integrated[integrated["split"].eq(split)]
        for value in sorted(base_split[group].astype(str).unique()):
            base = base_split[base_split[group].astype(str).eq(value)]
            kept = kept_split[kept_split[group].astype(str).eq(value)]
            row = {
                "split": split,
                group: value,
                "blocked_trades": int(base["gaspar_block"].sum()),
                "blocked_share": round_float(base["gaspar_block"].mean()) if len(base) else 0.0,
            }
            row.update(prefix_metrics("solo", trade_metrics(base)))
            row.update(prefix_metrics("integrated", trade_metrics(kept)))
            rows.append(row)
    return rows


def direction_metrics(original: pd.DataFrame, integrated: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for split in ["validation", "test"]:
        for direction in ["ENTER_BUY", "ENTER_SELL"]:
            base = original[original["split"].eq(split) & original["prediction"].eq(direction)]
            kept = integrated[integrated["split"].eq(split) & integrated["prediction"].eq(direction)]
            row = {
                "split": split,
                "direction": direction,
                "blocked_trades": int(base["gaspar_block"].sum()),
                "blocked_share": round_float(base["gaspar_block"].mean()) if len(base) else 0.0,
            }
            row.update(prefix_metrics("solo", trade_metrics(base)))
            row.update(prefix_metrics("integrated", trade_metrics(kept)))
            rows.append(row)
    return rows


def prefix_metrics(prefix: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in metrics.items()}


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


def extract_baltasar_v1(policy_metrics: dict[str, Any]) -> dict[str, Any]:
    return policy_metrics.get("baltasar_v1_comparison", {}).get("by_split", {})


def extract_baltasar_v2_medium(policy_metrics: dict[str, Any]) -> dict[str, Any]:
    rows = policy_metrics.get("threshold_metrics", [])
    return {row.get("threshold"): row for row in rows}


def markdown_summary(metrics: dict[str, Any]) -> str:
    lines = [
        "# Baltasar v2 + Gaspar v2.1c Integration",
        "",
        "## Scope",
        "",
        "- Baltasar v2 rich_policy_medium threshold `0.40` generates trades.",
        "- Gaspar v2.1c blocks trades when `P(DETERIORATING) >= 0.50`.",
        "- No model training is performed.",
        "",
        "## Validation/Test Comparison",
        "",
        comparison_table(metrics),
        "",
        "## Direction Impact",
        "",
        direction_table(metrics),
        "",
        "## 2026Q2 Diagnostic",
        "",
        q2_table(metrics),
        "",
        "## Interpretation",
        "",
        interpretation(metrics),
    ]
    return "\n".join(lines) + "\n"


def comparison_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Split | System | Trades | Avg R | Total R | PF | Max DD | Win rate | Blocked |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ["validation", "test"]:
        item = metrics[split]
        solo = item["baltasar_v2_solo"]
        integrated = item["integrated"]
        rows.append(row_line(split, "Baltasar v2 solo", solo, 0))
        rows.append(row_line(split, "Baltasar+Gaspar", integrated, item["blocked_trades"]))
    return "\n".join(rows)


def row_line(split: str, system: str, item: dict[str, Any], blocked: int) -> str:
    return (
        f"| {split} | {system} | {item['trades']:,} | {item['avg_r']:.4f} | {item['total_r']:.2f} | "
        f"{item['profit_factor']:.4f} | {item['max_drawdown_r']:.2f} | {item['win_rate']:.4f} | {blocked:,} |"
    )


def direction_table(metrics: dict[str, Any]) -> str:
    rows = [
        "| Split | Direction | System | Trades | Avg R | PF | Max DD | Blocked |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ["validation", "test"]:
        for direction in ["BUY", "SELL"]:
            payload = metrics[split]["direction"][direction]
            rows.append(direction_line(split, direction, "solo", payload["solo"], 0))
            rows.append(direction_line(split, direction, "integrated", payload["integrated"], payload["blocked"]))
    return "\n".join(rows)


def direction_line(split: str, direction: str, system: str, item: dict[str, Any], blocked: int) -> str:
    return (
        f"| {split} | {direction} | {system} | {item['trades']:,} | {item['avg_r']:.4f} | "
        f"{item['profit_factor']:.4f} | {item['max_drawdown_r']:.2f} | {blocked:,} |"
    )


def q2_table(metrics: dict[str, Any]) -> str:
    q2 = metrics["q2_2026"]
    return "\n".join(
        [
            "| System | Trades | Avg R | Total R | PF | Max DD | Blocked |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            row_line("2026Q2", "Baltasar v2 solo", q2["baltasar_v2_solo"], 0).replace("| 2026Q2 | ", "| "),
            row_line("2026Q2", "Baltasar+Gaspar", q2["integrated"], q2["blocked_trades"]).replace("| 2026Q2 | ", "| "),
        ]
    )


def interpretation(metrics: dict[str, Any]) -> str:
    test_solo = metrics["test"]["baltasar_v2_solo"]
    test_int = metrics["test"]["integrated"]
    q2_solo = metrics["q2_2026"]["baltasar_v2_solo"]
    q2_int = metrics["q2_2026"]["integrated"]
    return (
        f"On test, integration changes Avg R from `{test_solo['avg_r']:.4f}` to `{test_int['avg_r']:.4f}`, "
        f"PF from `{test_solo['profit_factor']:.4f}` to `{test_int['profit_factor']:.4f}`, and max DD from "
        f"`{test_solo['max_drawdown_r']:.2f}` to `{test_int['max_drawdown_r']:.2f}`. In 2026Q2 it changes Avg R "
        f"from `{q2_solo['avg_r']:.4f}` to `{q2_int['avg_r']:.4f}` and blocks "
        f"`{metrics['q2_2026']['blocked_trades']}` trades."
    )


def round_float(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
