from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_SELECTED_TRADES = Path("data/output/magi_v2/gaspar_v2_dataset_full/gaspar_v2_dataset_full.parquet")
DEFAULT_RICH_FEATURES = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet")
DEFAULT_RR2_LABELS = Path("data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet")
DEFAULT_OPTIONAL_REFERENCE = Path(
    "data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_040.csv"
)
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/gaspar_v2_1_regime_dataset")
DEFAULT_DOC = Path("docs/gaspar_v2_1_regime_dataset.md")

TARGET = "context_block_rr2"
MIN_SAMPLE_SIZE = 50
GROUP_COLUMNS = [
    "split",
    "hour_bucket",
    "daily_range_bucket",
    "atr_bucket",
    "h4_market_structure",
    "d1_market_structure",
    "predicted_direction",
]


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source = read_selected_trades(Path(args.selected_trades))
    verify_source_inputs(Path(args.rich_features), Path(args.rr2_labels))
    contexts = build_context_dataset(source)

    contexts.to_parquet(output_dir / "gaspar_v2_1_regime_dataset.parquet", index=False)
    summary = build_summary(contexts, source, args)
    (output_dir / "gaspar_v2_1_regime_dataset_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown = markdown_summary(summary)
    (output_dir / "gaspar_v2_1_regime_dataset_summary.md").write_text(markdown, encoding="utf-8")
    Path(args.doc).write_text(markdown, encoding="utf-8")

    print(f"contexts={len(contexts)}")
    print(f"label_distribution={contexts[TARGET].value_counts().to_dict()}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gaspar v2.1 aggregated regime/context dataset.")
    parser.add_argument("--selected-trades", default=str(DEFAULT_SELECTED_TRADES))
    parser.add_argument("--rich-features", default=str(DEFAULT_RICH_FEATURES))
    parser.add_argument("--rr2-labels", default=str(DEFAULT_RR2_LABELS))
    parser.add_argument("--optional-reference", default=str(DEFAULT_OPTIONAL_REFERENCE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def read_selected_trades(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df[df["split"].isin(["train", "validation", "test"])].copy()
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce").fillna(0.0)
    df["predicted_direction"] = df["prediction"].map(
        {"ENTER_BUY": "BUY", "ENTER_SELL": "SELL"}
    ).fillna("NONE")
    add_buckets(df)
    return df


def verify_source_inputs(rich_features: Path, rr2_labels: Path) -> None:
    missing = [str(path) for path in [rich_features, rr2_labels] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required base inputs: {missing}")


def add_buckets(df: pd.DataFrame) -> None:
    df["hour_bucket"] = pd.to_numeric(df["hour"], errors="coerce").apply(hour_bucket)
    daily_range = pd.to_numeric(df["daily_range_position"], errors="coerce")
    df["daily_range_bucket"] = pd.cut(
        daily_range,
        bins=[-math.inf, 0.15, 0.35, 0.65, 0.85, math.inf],
        labels=["low", "mid_low", "mid", "mid_high", "extreme_high"],
    ).astype(str)
    atr = pd.to_numeric(df["atr"], errors="coerce")
    train_atr = atr[df["split"].eq("train")].dropna()
    if train_atr.empty:
        df["atr_bucket"] = "unknown"
    else:
        q1, q2, q3 = train_atr.quantile([0.25, 0.50, 0.75]).tolist()
        df["atr_bucket"] = atr.apply(lambda value: atr_bucket(value, q1, q2, q3))


def hour_bucket(value: Any) -> str:
    if pd.isna(value):
        return "unknown"
    hour = int(value)
    if 0 <= hour <= 5:
        return "asia_core"
    if 6 <= hour <= 8:
        return "london_open"
    if 9 <= hour <= 11:
        return "london_mid"
    if 12 <= hour <= 14:
        return "overlap"
    if 15 <= hour <= 17:
        return "new_york_mid"
    if 18 <= hour <= 20:
        return "late_us"
    return "inactive"


def atr_bucket(value: Any, q1: float, q2: float, q3: float) -> str:
    if pd.isna(value):
        return "unknown"
    value = float(value)
    if value <= q1:
        return "atr_low"
    if value <= q2:
        return "atr_mid_low"
    if value <= q3:
        return "atr_mid_high"
    return "atr_high"


def build_context_dataset(source: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in source.groupby(GROUP_COLUMNS, dropna=False, sort=True):
        payload = dict(zip(GROUP_COLUMNS, keys, strict=False))
        metrics = aggregate_metrics(group)
        buy_metrics = aggregate_metrics(group[group["predicted_direction"].eq("BUY")])
        sell_metrics = aggregate_metrics(group[group["predicted_direction"].eq("SELL")])
        row = {
            **payload,
            "sample_size": metrics["trades"],
            "avg_r": metrics["avg_r"],
            "total_r": metrics["total_r"],
            "profit_factor": metrics["profit_factor"],
            "win_rate": metrics["win_rate"],
            "max_drawdown_r": metrics["max_drawdown_r"],
            "buy_sample_size": buy_metrics["trades"],
            "buy_avg_r": buy_metrics["avg_r"],
            "buy_profit_factor": buy_metrics["profit_factor"],
            "buy_max_drawdown_r": buy_metrics["max_drawdown_r"],
            "sell_sample_size": sell_metrics["trades"],
            "sell_avg_r": sell_metrics["avg_r"],
            "sell_profit_factor": sell_metrics["profit_factor"],
            "sell_max_drawdown_r": sell_metrics["max_drawdown_r"],
        }
        row[TARGET] = label_context(row)
        row["regime_quality_bucket"] = regime_quality(row)
        row["sell_risk_context"] = sell_risk(row)
        rows.append(row)
    return pd.DataFrame(rows).sort_values(GROUP_COLUMNS).reset_index(drop=True)


def aggregate_metrics(df: pd.DataFrame) -> dict[str, Any]:
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
        "win_rate": round_float(float((r > 0).mean()) if trades else 0.0),
        "max_drawdown_r": round_float(max_drawdown(r)),
    }


def max_drawdown(r: pd.Series) -> float:
    if r.empty:
        return 0.0
    equity = r.cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return float((peak - equity).max())


def label_context(row: dict[str, Any]) -> str:
    if int(row["sample_size"]) < MIN_SAMPLE_SIZE:
        return "NEUTRAL"
    avg_r = float(row["avg_r"])
    pf = float(row["profit_factor"])
    if avg_r < 0 or pf < 1.0:
        return "BLOCK"
    if avg_r > 0 and pf >= 1.0:
        return "ALLOW"
    return "NEUTRAL"


def regime_quality(row: dict[str, Any]) -> str:
    if int(row["sample_size"]) < MIN_SAMPLE_SIZE:
        return "LOW_SAMPLE"
    avg_r = float(row["avg_r"])
    pf = float(row["profit_factor"])
    if pf >= 1.20 and avg_r >= 0.10:
        return "STRONG_POSITIVE"
    if pf >= 1.05 and avg_r > 0:
        return "POSITIVE"
    if pf < 0.85 and avg_r < 0:
        return "DANGEROUS"
    if pf < 0.95 or avg_r < 0:
        return "NEGATIVE"
    return "MIXED"


def sell_risk(row: dict[str, Any]) -> str:
    if row["predicted_direction"] != "SELL":
        return "NOT_SELL"
    if int(row["sell_sample_size"]) < MIN_SAMPLE_SIZE:
        return "SELL_CAUTION"
    avg_r = float(row["sell_avg_r"])
    pf = float(row["sell_profit_factor"])
    if avg_r < 0 or pf < 1.0:
        return "SELL_BLOCK"
    if pf < 1.10:
        return "SELL_CAUTION"
    return "SELL_OK"


def build_summary(contexts: pd.DataFrame, source: pd.DataFrame, args: argparse.Namespace) -> dict[str, Any]:
    q2 = source[source["quarter"].eq("2026Q2")].copy()
    q2_contexts = build_context_dataset(q2) if not q2.empty else pd.DataFrame()
    return {
        "schema_version": "gaspar_v2_1_regime_dataset_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_selected_trades": str(args.selected_trades),
        "base_inputs": {
            "rich_features": str(args.rich_features),
            "rr2_first_touch_labels": str(args.rr2_labels),
            "optional_policy_reference": str(args.optional_reference),
        },
        "rows": int(len(contexts)),
        "source_trade_rows": int(len(source)),
        "target": TARGET,
        "group_columns": GROUP_COLUMNS,
        "min_sample_size": MIN_SAMPLE_SIZE,
        "label_distribution": value_counts(contexts[TARGET]),
        "label_distribution_by_split": {
            split: value_counts(part[TARGET])
            for split, part in contexts.groupby("split", dropna=False)
        },
        "coverage_by_split": source.groupby("split").size().astype(int).to_dict(),
        "context_count_by_split": contexts.groupby("split").size().astype(int).to_dict(),
        "block_examples": top_examples(contexts, "BLOCK", ascending=True),
        "allow_examples": top_examples(contexts, "ALLOW", ascending=False),
        "q2_block_examples": top_examples(q2_contexts, "BLOCK", ascending=True) if not q2_contexts.empty else [],
        "q2_worst_examples": top_any_examples(q2_contexts, ascending=True) if not q2_contexts.empty else [],
        "technical_warnings": [
            "Rows are aggregated contexts, not individual trades.",
            "Labels are computed independently within train, validation and test splits to avoid mixing future outcome periods.",
            "Aggregated outcome metrics are stored for diagnostics and label construction; they should not be used as predictive features without a causal redesign.",
            "ATR buckets use train-period quartiles, then apply those thresholds to validation/test.",
            "No gaspar_training_v1 data is used.",
        ],
    }


def top_examples(contexts: pd.DataFrame, label: str, ascending: bool) -> list[dict[str, Any]]:
    if contexts.empty or TARGET not in contexts:
        return []
    part = contexts[contexts[TARGET].eq(label)].copy()
    if part.empty:
        return []
    return (
        part.sort_values(["avg_r", "sample_size"], ascending=[ascending, False])
        .head(8)[
            [
                *GROUP_COLUMNS,
                "sample_size",
                "avg_r",
                "profit_factor",
                "win_rate",
                "max_drawdown_r",
                TARGET,
            ]
        ]
        .to_dict(orient="records")
    )


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Gaspar v2.1 Regime Dataset",
        "",
        "## Scope",
        "",
        "Each row is an aggregated context, not an individual trade.",
        "",
        "The dataset groups Baltasar v2 `rich_policy_medium 0.40` trades by context buckets and assigns a regime/blocking label from aggregate RR 1:2 first-touch performance.",
        "",
        "## Inputs",
        "",
        f"- Selected full trades source: `{summary['source_selected_trades']}`",
        f"- Rich features base: `{summary['base_inputs']['rich_features']}`",
        f"- RR2 labels base: `{summary['base_inputs']['rr2_first_touch_labels']}`",
        f"- Optional policy reference: `{summary['base_inputs']['optional_policy_reference']}`",
        "",
        "## Context Definition",
        "",
        ", ".join(f"`{column}`" for column in summary["group_columns"]),
        "",
        "## Label Rule",
        "",
        f"- `NEUTRAL`: sample size < `{summary['min_sample_size']}` or mixed/ambiguous context.",
        "- `BLOCK`: avg R < 0 or PF < 1.",
        "- `ALLOW`: avg R > 0 and PF >= 1.",
        "",
        "## Dataset Size",
        "",
        f"- Contexts: `{summary['rows']:,}`",
        f"- Source trades covered: `{summary['source_trade_rows']:,}`",
        "",
        "## Label Distribution",
        "",
        "| Label | Contexts |",
        "| --- | ---: |",
    ]
    for label, count in summary["label_distribution"].items():
        lines.append(f"| {label} | {count:,} |")
    lines.extend(["", "## Label Distribution by Split", ""])
    for split, dist in summary["label_distribution_by_split"].items():
        lines.extend([f"### {split}", "", "| Label | Contexts |", "| --- | ---: |"])
        for label, count in dist.items():
            lines.append(f"| {label} | {count:,} |")
        lines.append("")
    lines.extend(["## BLOCK Examples", "", examples_table(summary["block_examples"])])
    lines.extend(["", "## ALLOW Examples", "", examples_table(summary["allow_examples"])])
    lines.extend(["", "## 2026Q2 BLOCK Examples", "", examples_table(summary["q2_block_examples"])])
    lines.extend(
        [
            "",
            "## 2026Q2 Worst Context Examples",
            "",
            "These are diagnostic examples even when the formal label is `NEUTRAL` because the 2026Q2 sample is small after granular grouping.",
            "",
            examples_table(summary["q2_worst_examples"]),
        ]
    )
    lines.extend(["", "## Technical Warnings", ""])
    lines.extend(f"- {item}" for item in summary["technical_warnings"])
    lines.extend(
        [
            "",
            "## CEO Usage",
            "",
            "Gaspar v2.1 should later map context outputs to `ALLOW`, `CAUTION`, or `BLOCK` signals for CEO-MAGI. It should not vote direction.",
            "",
            "## Limitations",
            "",
            "- This first version uses split-local aggregate labels, not causal rolling labels.",
            "- Aggregate outcome metrics are diagnostics; do not feed them as model features unless they are rebuilt causally from past-only data.",
            "- Context granularity may create low-sample contexts, intentionally labelled `NEUTRAL`.",
        ]
    )
    return "\n".join(lines) + "\n"


def examples_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No examples._"
    headers = [
        "split",
        "hour_bucket",
        "daily_range_bucket",
        "atr_bucket",
        "h4_market_structure",
        "d1_market_structure",
        "predicted_direction",
        "sample_size",
        "avg_r",
        "PF",
        "DD",
    ]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("split")),
                    str(row.get("hour_bucket")),
                    str(row.get("daily_range_bucket")),
                    str(row.get("atr_bucket")),
                    str(row.get("h4_market_structure")),
                    str(row.get("d1_market_structure")),
                    str(row.get("predicted_direction")),
                    f"{int(row.get('sample_size', 0)):,}",
                    f"{float(row.get('avg_r', 0)):.4f}",
                    f"{float(row.get('profit_factor', 0)):.4f}",
                    f"{float(row.get('max_drawdown_r', 0)):.2f}",
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def top_any_examples(contexts: pd.DataFrame, ascending: bool) -> list[dict[str, Any]]:
    if contexts.empty:
        return []
    return (
        contexts.sort_values(["avg_r", "sample_size"], ascending=[ascending, False])
        .head(8)[
            [
                *GROUP_COLUMNS,
                "sample_size",
                "avg_r",
                "profit_factor",
                "win_rate",
                "max_drawdown_r",
                TARGET,
            ]
        ]
        .to_dict(orient="records")
    )


def value_counts(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.fillna("NULL").value_counts(dropna=False).to_dict().items()}


def round_float(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


if __name__ == "__main__":
    raise SystemExit(main())
