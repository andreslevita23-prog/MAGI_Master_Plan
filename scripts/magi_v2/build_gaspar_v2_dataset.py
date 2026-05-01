from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_TRADES_040 = Path(
    "data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_040.csv"
)
DEFAULT_TRADES_050 = Path(
    "data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation/simulated_trades_050.csv"
)
DEFAULT_RICH_FEATURES = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/gaspar_v2_dataset")
DEFAULT_DOC = Path("docs/gaspar_v2_plan.md")

TARGET = "context_quality_rr2"
NEUTRAL_R_BAND = 0.10
TIMING_FEATURE_EXCLUSIONS = {"hour", "weekday", "session"}
FORBIDDEN_FEATURES = {
    "tradeable_direction_rr2_first_touch",
    "buy_R",
    "sell_R",
    "buy_first_touch",
    "sell_first_touch",
    "buy_bars_to_exit",
    "sell_bars_to_exit",
    "same_bar_ambiguous_flag",
    "prediction",
    "variant",
    "threshold",
    "realized_R",
    TARGET,
}


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trades_040 = read_trades(Path(args.trades_040), "040")
    trades_050 = read_trades(Path(args.trades_050), "050")
    rich = read_rich_features(Path(args.rich_features))

    dataset, feature_columns, join_stats = build_dataset(trades_040, trades_050, rich)
    dataset.to_parquet(output_dir / "gaspar_v2_dataset.parquet", index=False)

    summary = build_summary(dataset, feature_columns, join_stats, args)
    (output_dir / "gaspar_v2_dataset_summary.md").write_text(summary, encoding="utf-8")
    Path(args.doc).write_text(build_plan_doc(summary), encoding="utf-8")

    print(f"rows={len(dataset)}")
    print(f"columns={len(dataset.columns)}")
    print(f"label_distribution={dataset[TARGET].value_counts().to_dict()}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gaspar v2 context/regime dataset from Baltasar v2 policy trades.")
    parser.add_argument("--trades-040", default=str(DEFAULT_TRADES_040))
    parser.add_argument("--trades-050", default=str(DEFAULT_TRADES_050))
    parser.add_argument("--rich-features", default=str(DEFAULT_RICH_FEATURES))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def read_trades(path: Path, threshold_key: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["policy_threshold"] = threshold_key
    df["symbol"] = df["symbol"].astype(str)
    df["prediction"] = df["prediction"].astype(str)
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce")
    return df


def read_rich_features(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["symbol"] = df["symbol"].astype(str)
    return df


def build_dataset(
    trades_040: pd.DataFrame,
    trades_050: pd.DataFrame,
    rich: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    selected_050_keys = set(make_trade_key(trades_050))
    trades = trades_040.copy()
    trades["trade_key"] = make_trade_key(trades)
    trades["selected_at_050"] = trades["trade_key"].isin(selected_050_keys)

    rich_feature_columns = choose_feature_columns(rich)
    rich_keep = [
        "timestamp",
        "symbol",
        "snapshot_id",
        "anchor_bar_timestamp",
        "same_bar_ambiguous_flag",
        "buy_first_touch",
        "sell_first_touch",
        "buy_R",
        "sell_R",
    ]
    rich_keep = [c for c in rich_keep if c in rich.columns] + rich_feature_columns
    rich_subset = rich[dedupe_preserve_order(rich_keep)].copy()

    joined = trades.merge(
        rich_subset,
        on=["timestamp", "symbol"],
        how="left",
        suffixes=("", "_rich"),
        indicator=True,
    )
    joined["rich_feature_match"] = joined["_merge"].eq("both")
    joined = joined.drop(columns=["_merge"])

    joined[TARGET] = joined.apply(label_context_quality, axis=1)
    joined["abs_realized_R"] = joined["realized_R"].abs()
    joined["year"] = joined["timestamp"].dt.year.astype(str)
    joined["quarter"] = joined["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("Q").astype(str)
    joined["month"] = joined["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M").astype(str)

    diagnostic_columns = [
        "timestamp",
        "symbol",
        "split",
        "year",
        "quarter",
        "month",
        "prediction",
        "realized_R",
        "abs_realized_R",
        "policy_threshold",
        "selected_at_050",
        "tradeable_direction_rr2_first_touch",
        "buy_R",
        "sell_R",
        "buy_first_touch",
        "sell_first_touch",
        "same_bar_ambiguous_flag",
        "session",
        "hour",
        "weekday",
        "rich_feature_match",
        "trade_key",
    ]
    columns = [c for c in diagnostic_columns if c in joined.columns] + [TARGET] + rich_feature_columns
    dataset = joined[dedupe_preserve_order(columns)].copy()

    join_stats = {
        "source_trades_040": int(len(trades_040)),
        "source_trades_050": int(len(trades_050)),
        "rows": int(len(dataset)),
        "rich_feature_matches": int(dataset["rich_feature_match"].sum()),
        "rich_feature_match_rate": float(dataset["rich_feature_match"].mean()),
        "selected_at_050": int(dataset["selected_at_050"].sum()),
        "selected_at_050_rate": float(dataset["selected_at_050"].mean()),
        "neutral_r_band": NEUTRAL_R_BAND,
    }
    return dataset, rich_feature_columns, join_stats


def choose_feature_columns(rich: pd.DataFrame) -> list[str]:
    preferred = [
        "spread_pips",
        "atr",
        "daily_range_position",
        "regime",
        "anchor_open",
        "anchor_high",
        "anchor_low",
        "anchor_close",
        "candle_body_pct",
        "upper_wick_pct",
        "lower_wick_pct",
        "returns_1",
        "returns_3",
        "returns_6",
        "volatility_12",
        "recent_range",
        "ema_20",
        "ema_50",
        "ema_200",
        "ema_20_50_distance",
        "ema_50_200_distance",
        "close_to_ema20",
        "close_to_ema50",
        "close_to_ema200",
        "ema_20_slope",
        "ema_50_slope",
        "rsi_14",
        "momentum",
        "market_structure",
        "structure_direction",
        "support_distance_pips",
        "resistance_distance_pips",
        "mtf_alignment_status",
        "htf_directional_alignment",
        "htf_h4_structure",
        "htf_d1_structure",
    ]
    for prefix in ["m15", "h1", "h4", "d1"]:
        preferred.extend(
            [
                f"{prefix}_ema_20",
                f"{prefix}_ema_50",
                f"{prefix}_ema_200",
                f"{prefix}_rsi_14",
                f"{prefix}_market_structure",
                f"{prefix}_structure_direction",
                f"{prefix}_recent_range",
                f"{prefix}_candle_pattern",
            ]
        )
    columns = [
        c
        for c in preferred
        if c in rich.columns and c not in TIMING_FEATURE_EXCLUSIONS and c not in FORBIDDEN_FEATURES
    ]
    return dedupe_preserve_order(columns)


def make_trade_key(df: pd.DataFrame) -> pd.Series:
    return (
        df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        + "|"
        + df["symbol"].astype(str)
        + "|"
        + df["prediction"].astype(str)
    )


def label_context_quality(row: pd.Series) -> str:
    ambiguous_value = row.get("same_bar_ambiguous_flag", False)
    ambiguous = False if pd.isna(ambiguous_value) else bool(ambiguous_value)
    realized_r = row.get("realized_R")
    if pd.isna(realized_r) or ambiguous or abs(float(realized_r)) <= NEUTRAL_R_BAND:
        return "NEUTRAL"
    if float(realized_r) > NEUTRAL_R_BAND:
        return "FAVORABLE"
    return "UNFAVORABLE"


def build_summary(
    dataset: pd.DataFrame,
    feature_columns: list[str],
    join_stats: dict[str, Any],
    args: argparse.Namespace,
) -> str:
    label_dist = dataset[TARGET].value_counts().to_dict()
    split_dist = crosstab_markdown(dataset, "split", TARGET)
    direction_dist = crosstab_markdown(dataset, "prediction", TARGET)
    q2 = dataset[dataset["quarter"].eq("2026Q2")]
    favorable_examples = segment_examples(dataset, "FAVORABLE")
    unfavorable_examples = segment_examples(dataset, "UNFAVORABLE")
    nulls = dataset[feature_columns].isna().sum().sort_values(ascending=False).head(15)

    lines = [
        "# Gaspar v2 context dataset",
        "",
        "## Purpose",
        "",
        "Builds the first Gaspar v2 dataset to learn whether market context favors or hurts trades selected by `Baltasar v2 rich_policy_medium`.",
        "",
        "Gaspar v2 is not a directional model. It should learn context quality and later help CEO-MAGI block, caution, or reinforce Baltasar trades.",
        "",
        "## Inputs",
        "",
        f"- `simulated_trades_040.csv`: `{args.trades_040}`",
        f"- `simulated_trades_050.csv`: `{args.trades_050}`",
        f"- `baltasar_v2_rich_features.parquet`: `{args.rich_features}`",
        "",
        "## Output",
        "",
        f"- Rows: `{len(dataset):,}`",
        f"- Columns: `{len(dataset.columns):,}`",
        f"- Feature columns: `{len(feature_columns):,}`",
        f"- Rich feature match rate: `{join_stats['rich_feature_match_rate']:.2%}`",
        f"- Selected at threshold 0.50: `{join_stats['selected_at_050']:,}` (`{join_stats['selected_at_050_rate']:.2%}`)",
        "",
        "## Label",
        "",
        "`context_quality_rr2`:",
        "",
        "- `FAVORABLE`: selected trade ended with `R > +0.10`.",
        "- `UNFAVORABLE`: selected trade ended with `R < -0.10`.",
        "- `NEUTRAL`: absolute R near zero, missing R, or same-bar ambiguous.",
        "",
        "## Label distribution",
        "",
        "| Label | Rows | Share |",
        "| --- | ---: | ---: |",
    ]
    for label, count in label_dist.items():
        lines.append(f"| {label} | {count:,} | {count / len(dataset):.2%} |")

    lines.extend(["", "## Distribution by split", "", split_dist])
    lines.extend(["", "## Distribution by predicted direction", "", direction_dist])
    lines.extend(
        [
            "",
            "## 2026Q2 diagnostic",
            "",
            f"- Rows: `{len(q2):,}`",
            f"- Avg R: `{q2['realized_R'].mean():.4f}`" if not q2.empty else "- Avg R: `n/a`",
            f"- Label distribution: `{q2[TARGET].value_counts().to_dict()}`",
            "",
            "## Favorable context examples",
            "",
            favorable_examples,
            "",
            "## Unfavorable context examples",
            "",
            unfavorable_examples,
            "",
            "## Feature columns",
            "",
            ", ".join(f"`{c}`" for c in feature_columns),
            "",
            "## Main feature nulls",
            "",
            "| Column | Nulls |",
            "| --- | ---: |",
        ]
    )
    for column, count in nulls.items():
        lines.append(f"| `{column}` | {int(count):,} |")
    lines.extend(
        [
            "",
            "## Technical decisions",
            "",
            "- The principal universe is threshold `0.40`; threshold `0.50` is stored only as diagnostic `selected_at_050` to avoid duplicate context rows.",
            "- Exact `hour`, `weekday`, and `session` are kept only as diagnostics, not as Gaspar feature columns.",
            "- Policy decisions such as threshold, variant, prediction confidence, and selected-at-threshold are not feature columns.",
            "- Baltasar labels and first-touch/R diagnostics are not Gaspar features.",
            "- `regime` is retained as a market-context feature, but should be reviewed before training if it encodes time/session directly.",
            "",
            "## Next step",
            "",
            "Train a first Gaspar v2 context classifier using only the listed feature columns, then evaluate whether it can identify high-loss SELL contexts and the 2026Q2 regime deterioration before CEO-MAGI uses it as a blocking/caution signal.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_plan_doc(summary: str) -> str:
    header = [
        "# Gaspar v2 plan",
        "",
        "## Role in MAGI",
        "",
        "Gaspar v2 will be the context and regime specialist. Its job is not to predict direction and not to replace Baltasar. Gaspar should evaluate whether current market structure, volatility, range position, support/resistance context, and multi-timeframe alignment make a Baltasar trade favorable, dangerous, or neutral.",
        "",
        "## Relationship with Baltasar",
        "",
        "Baltasar v2 remains the directional candidate. Gaspar v2 should sit beside it as a quality gate: reinforce favorable contexts, warn on neutral contexts, and block or downgrade unfavorable contexts. This directly targets the current weaknesses: SELL fragility and regime degradation such as 2026Q2.",
        "",
        "## Future CEO usage",
        "",
        "CEO-MAGI v3 should consume Baltasar direction/probability plus Gaspar context quality and Melchor risk state. The CEO output remains `ENTER_BUY`, `ENTER_SELL`, or `DO_NOTHING`; Gaspar contributes context, not direction.",
        "",
        "---",
        "",
    ]
    return "\n".join(header) + summary


def crosstab_markdown(df: pd.DataFrame, index: str, columns: str) -> str:
    table = pd.crosstab(df[index].fillna("NULL"), df[columns].fillna("NULL"))
    table["TOTAL"] = table.sum(axis=1)
    lines = ["| " + index + " | " + " | ".join(map(str, table.columns)) + " |"]
    lines.append("| --- | " + " | ".join(["---:"] * len(table.columns)) + " |")
    for idx, row in table.iterrows():
        values = " | ".join(f"{int(v):,}" for v in row.values)
        lines.append(f"| {idx} | {values} |")
    return "\n".join(lines)


def segment_examples(dataset: pd.DataFrame, label: str) -> str:
    cols = [c for c in ["prediction", "regime", "market_structure", "structure_direction", "mtf_alignment_status"] if c in dataset.columns]
    if not cols:
        return "_No segment columns available._"
    part = dataset[dataset[TARGET].eq(label)].copy()
    if part.empty:
        return "_No rows._"
    grouped = (
        part.groupby(cols, dropna=False)
        .agg(rows=(TARGET, "size"), avg_r=("realized_R", "mean"))
        .reset_index()
        .sort_values(["rows", "avg_r"], ascending=[False, False])
        .head(8)
    )
    lines = ["| " + " | ".join(cols + ["rows", "avg_r"]) + " |"]
    lines.append("| " + " | ".join(["---"] * len(cols) + ["---:", "---:"]) + " |")
    for _, row in grouped.iterrows():
        values = [str(row[c]) for c in cols] + [f"{int(row['rows']):,}", f"{row['avg_r']:.4f}"]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
