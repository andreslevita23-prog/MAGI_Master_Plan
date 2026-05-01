from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_SELECTED_TRADES = Path("data/output/magi_v2/gaspar_v2_dataset_full/gaspar_v2_dataset_full.parquet")
DEFAULT_V21_REFERENCE = Path(
    "data/output/magi_v2/gaspar_v2_1_regime_dataset/gaspar_v2_1_regime_dataset.parquet"
)
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/gaspar_v2_1b_regime_dataset")
DEFAULT_DOC = Path("docs/gaspar_v2_1b_regime_dataset.md")

MIN_SAMPLE_SIZES = [25, 40, 50]
RECOMMENDED_MIN_SAMPLE = 25
GROUP_COLUMNS = [
    "split",
    "hour_bucket",
    "daily_range_bucket",
    "atr_bucket",
    "h4_market_structure",
    "predicted_direction",
]
TARGET = "context_block_rr2"
SELL_TARGET = "sell_risk_context"


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source = read_selected_trades(Path(args.selected_trades))
    configs: dict[str, pd.DataFrame] = {}
    summaries: dict[str, Any] = {}
    for min_sample in MIN_SAMPLE_SIZES:
        contexts = build_context_dataset(source, min_sample)
        key = str(min_sample)
        configs[key] = contexts
        summaries[key] = summarize_config(contexts, source, min_sample)

    recommended = configs[str(RECOMMENDED_MIN_SAMPLE)].copy()
    recommended.to_parquet(output_dir / "gaspar_v2_1b_regime_dataset.parquet", index=False)

    summary = build_summary(source, summaries, args)
    (output_dir / "gaspar_v2_1b_regime_dataset_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown = markdown_summary(summary)
    (output_dir / "gaspar_v2_1b_regime_dataset_summary.md").write_text(markdown, encoding="utf-8")
    Path(args.doc).write_text(markdown, encoding="utf-8")

    print(f"recommended_min_sample={RECOMMENDED_MIN_SAMPLE}")
    for key, item in summaries.items():
        print(f"min_sample={key} contexts={item['contexts']} labels={item['label_distribution']}")
        print(f"  train={item['label_distribution_by_split'].get('train', {})}")
        print(f"  sell_train={item['sell_risk_distribution_by_split'].get('train', {})}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gaspar v2.1b coarse regime dataset with SELL risk labels.")
    parser.add_argument("--selected-trades", default=str(DEFAULT_SELECTED_TRADES))
    parser.add_argument("--v21-reference", default=str(DEFAULT_V21_REFERENCE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def read_selected_trades(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df[df["split"].isin(["train", "validation", "test"])].copy()
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce").fillna(0.0)
    df["predicted_direction"] = df["prediction"].map(
        {"ENTER_BUY": "BUY", "ENTER_SELL": "SELL", "BUY": "BUY", "SELL": "SELL"}
    ).fillna("NONE")
    add_buckets(df)
    return df


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


def build_context_dataset(source: pd.DataFrame, min_sample: int) -> pd.DataFrame:
    rows = []
    for keys, group in source.groupby(GROUP_COLUMNS, dropna=False, sort=True):
        row = dict(zip(GROUP_COLUMNS, keys, strict=False))
        metrics = aggregate_metrics(group)
        row.update(
            {
                "min_sample_size": min_sample,
                "sample_size": metrics["trades"],
                "avg_r": metrics["avg_r"],
                "total_r": metrics["total_r"],
                "profit_factor": metrics["profit_factor"],
                "win_rate": metrics["win_rate"],
                "max_drawdown_r": metrics["max_drawdown_r"],
            }
        )
        row[TARGET] = label_context(row, min_sample)
        row["regime_quality_bucket"] = regime_quality(row, min_sample)
        row[SELL_TARGET] = sell_risk_context(row, min_sample)
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


def label_context(row: dict[str, Any], min_sample: int) -> str:
    if int(row["sample_size"]) < min_sample:
        return "NEUTRAL"
    avg_r = float(row["avg_r"])
    pf = float(row["profit_factor"])
    if avg_r < 0 or pf < 1.0:
        return "BLOCK"
    if avg_r > 0 and pf >= 1.0:
        return "ALLOW"
    return "NEUTRAL"


def regime_quality(row: dict[str, Any], min_sample: int) -> str:
    if int(row["sample_size"]) < min_sample:
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


def sell_risk_context(row: dict[str, Any], min_sample: int) -> str:
    if row["predicted_direction"] != "SELL":
        return "NOT_SELL"
    if int(row["sample_size"]) < min_sample:
        return "SELL_RISK_NEUTRAL"
    avg_r = float(row["avg_r"])
    pf = float(row["profit_factor"])
    if avg_r < 0 or pf < 1.0:
        return "SELL_RISK_HIGH"
    if pf >= 1.10 and avg_r > 0:
        return "SELL_RISK_LOW"
    return "SELL_RISK_NEUTRAL"


def summarize_config(contexts: pd.DataFrame, source: pd.DataFrame, min_sample: int) -> dict[str, Any]:
    q2 = source[source["quarter"].eq("2026Q2")].copy()
    q2_contexts = build_context_dataset(q2, min_sample) if not q2.empty else pd.DataFrame()
    return {
        "min_sample_size": min_sample,
        "contexts": int(len(contexts)),
        "label_distribution": value_counts(contexts[TARGET]),
        "label_distribution_by_split": {
            split: value_counts(part[TARGET])
            for split, part in contexts.groupby("split", dropna=False)
        },
        "sell_risk_distribution": value_counts(contexts[SELL_TARGET]),
        "sell_risk_distribution_by_split": {
            split: value_counts(part[SELL_TARGET])
            for split, part in contexts.groupby("split", dropna=False)
        },
        "bad_sell_examples": top_examples(
            contexts[contexts["predicted_direction"].eq("SELL")],
            label_column=SELL_TARGET,
            label_value="SELL_RISK_HIGH",
            ascending=True,
        ),
        "allow_examples": top_examples(contexts, TARGET, "ALLOW", ascending=False),
        "block_examples": top_examples(contexts, TARGET, "BLOCK", ascending=True),
        "q2_worst_examples": top_any_examples(q2_contexts, ascending=True) if not q2_contexts.empty else [],
        "q2_similarity_to_train": q2_similarity_to_train(contexts, q2_contexts) if not q2_contexts.empty else {},
        "has_sufficient_train_block": int(
            contexts[contexts["split"].eq("train") & contexts[TARGET].eq("BLOCK")].shape[0]
        )
        >= 20,
    }


def q2_similarity_to_train(contexts: pd.DataFrame, q2_contexts: pd.DataFrame) -> dict[str, Any]:
    train_keys = set(context_key_rows(contexts[contexts["split"].eq("train")]))
    q2_keys = context_key_rows(q2_contexts)
    matches = [key in train_keys for key in q2_keys]
    return {
        "q2_contexts": len(q2_keys),
        "matched_in_train": int(sum(matches)),
        "match_rate": round_float(sum(matches) / len(q2_keys)) if q2_keys else 0.0,
    }


def context_key_rows(df: pd.DataFrame) -> list[tuple[Any, ...]]:
    key_columns = [c for c in GROUP_COLUMNS if c != "split"]
    return [tuple(row) for row in df[key_columns].itertuples(index=False, name=None)]


def build_summary(source: pd.DataFrame, configs: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    recommended = configs[str(RECOMMENDED_MIN_SAMPLE)]
    return {
        "schema_version": "gaspar_v2_1b_regime_dataset_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_selected_trades": str(args.selected_trades),
        "v21_reference": str(args.v21_reference),
        "recommended_min_sample_size": RECOMMENDED_MIN_SAMPLE,
        "group_columns": GROUP_COLUMNS,
        "source_trade_rows": int(len(source)),
        "configs": configs,
        "recommendation": {
            "train_block_contexts": recommended["label_distribution_by_split"].get("train", {}).get("BLOCK", 0),
            "train_sell_risk_high": recommended["sell_risk_distribution_by_split"].get("train", {}).get(
                "SELL_RISK_HIGH", 0
            ),
            "trainable": bool(recommended["has_sufficient_train_block"]),
            "reason": (
                "min_sample=25 gives the best balance between coarse context coverage and enough BLOCK/SELL_RISK_HIGH "
                "examples in train among the tested settings."
            ),
        },
        "technical_warnings": [
            "Rows are aggregated contexts, not individual trades.",
            "d1_market_structure is intentionally excluded to reduce granularity.",
            "Labels are computed independently within split, so this is suitable for dataset diagnostics; a production model should use causal rolling context labels.",
            "Aggregate R/PF/DD columns are diagnostics and label construction fields, not future model features unless rebuilt causally.",
            "No model is trained in this script.",
        ],
    }


def top_examples(contexts: pd.DataFrame, label_column: str, label_value: str, ascending: bool) -> list[dict[str, Any]]:
    if contexts.empty or label_column not in contexts:
        return []
    part = contexts[contexts[label_column].eq(label_value)].copy()
    if part.empty:
        return []
    return format_examples(part.sort_values(["avg_r", "sample_size"], ascending=[ascending, False]).head(8))


def top_any_examples(contexts: pd.DataFrame, ascending: bool) -> list[dict[str, Any]]:
    if contexts.empty:
        return []
    return format_examples(contexts.sort_values(["avg_r", "sample_size"], ascending=[ascending, False]).head(8))


def format_examples(df: pd.DataFrame) -> list[dict[str, Any]]:
    columns = [
        *GROUP_COLUMNS,
        "sample_size",
        "avg_r",
        "profit_factor",
        "win_rate",
        "max_drawdown_r",
        TARGET,
        SELL_TARGET,
    ]
    return df[[c for c in columns if c in df.columns]].to_dict(orient="records")


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Gaspar v2.1b Regime Dataset",
        "",
        "## Scope",
        "",
        "This version reduces context granularity by excluding `d1_market_structure` and adds explicit SELL risk labels.",
        "",
        f"- Source trades: `{summary['source_trade_rows']:,}`",
        f"- Recommended min sample: `{summary['recommended_min_sample_size']}`",
        "",
        "## Grouping",
        "",
        ", ".join(f"`{column}`" for column in summary["group_columns"]),
        "",
        "## Configuration Comparison",
        "",
    ]
    for key, config in summary["configs"].items():
        lines.extend(
            [
                f"### MIN_SAMPLE_SIZE = {key}",
                "",
                f"- Contexts: `{config['contexts']:,}`",
                f"- Has sufficient train BLOCK: `{config['has_sufficient_train_block']}`",
                f"- Q2 train context match rate: `{config['q2_similarity_to_train'].get('match_rate', 0):.2%}`",
                "",
                "Context label distribution by split:",
                "",
                split_table(config["label_distribution_by_split"]),
                "",
                "SELL risk distribution by split:",
                "",
                split_table(config["sell_risk_distribution_by_split"]),
                "",
            ]
        )
    recommended = summary["configs"][str(summary["recommended_min_sample_size"])]
    lines.extend(
        [
            "## Recommended Configuration",
            "",
            f"`MIN_SAMPLE_SIZE = {summary['recommended_min_sample_size']}`",
            "",
            f"- Train BLOCK contexts: `{summary['recommendation']['train_block_contexts']}`",
            f"- Train SELL_RISK_HIGH contexts: `{summary['recommendation']['train_sell_risk_high']}`",
            f"- Trainable: `{summary['recommendation']['trainable']}`",
            f"- Reason: {summary['recommendation']['reason']}",
            "",
            "## Bad SELL Examples",
            "",
            examples_table(recommended["bad_sell_examples"]),
            "",
            "## BLOCK Examples",
            "",
            examples_table(recommended["block_examples"]),
            "",
            "## ALLOW Examples",
            "",
            examples_table(recommended["allow_examples"]),
            "",
            "## 2026Q2 Worst Context Examples",
            "",
            examples_table(recommended["q2_worst_examples"]),
            "",
            "## Technical Warnings",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["technical_warnings"])
    return "\n".join(lines) + "\n"


def split_table(distribution: dict[str, dict[str, int]]) -> str:
    labels = sorted({label for split_dist in distribution.values() for label in split_dist})
    rows = ["| Split | " + " | ".join(labels) + " |", "| --- | " + " | ".join(["---:"] * len(labels)) + " |"]
    for split, split_dist in sorted(distribution.items()):
        rows.append("| " + split + " | " + " | ".join(f"{split_dist.get(label, 0):,}" for label in labels) + " |")
    return "\n".join(rows)


def examples_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No examples._"
    headers = [
        "split",
        "hour_bucket",
        "daily_range_bucket",
        "atr_bucket",
        "h4_market_structure",
        "predicted_direction",
        "sample_size",
        "avg_r",
        "PF",
        "DD",
        TARGET,
        SELL_TARGET,
    ]
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append(
            "| "
            + " | ".join(
                [
                    str(row.get("split")),
                    str(row.get("hour_bucket")),
                    str(row.get("daily_range_bucket")),
                    str(row.get("atr_bucket")),
                    str(row.get("h4_market_structure")),
                    str(row.get("predicted_direction")),
                    f"{int(row.get('sample_size', 0)):,}",
                    f"{float(row.get('avg_r', 0)):.4f}",
                    f"{float(row.get('profit_factor', 0)):.4f}",
                    f"{float(row.get('max_drawdown_r', 0)):.2f}",
                    str(row.get(TARGET)),
                    str(row.get(SELL_TARGET)),
                ]
            )
            + " |"
        )
    return "\n".join(out)


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
