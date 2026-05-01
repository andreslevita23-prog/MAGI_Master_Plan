from __future__ import annotations

import argparse
import json
import math
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_INPUT = Path("data/output/magi_v2/gaspar_v2_dataset_full/gaspar_v2_dataset_full.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/gaspar_v2_1c_rolling_dataset")
DEFAULT_DOC = Path("docs/gaspar_v2_1c_rolling_dataset.md")

WINDOWS = [20, 50, 100]
PRIMARY_WINDOW = 50
MIN_LABEL_FUTURE = {20: 10, 50: 20, 100: 40}
TARGET_REGIME = "regime_deteriorating_rr2"
TARGET_SELL = "sell_risk_next_window"


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = read_input(Path(args.input))
    rolling = build_rolling_dataset(df)
    rolling.to_parquet(output_dir / "gaspar_v2_1c_rolling_dataset.parquet", index=False)

    summary = build_summary(rolling, args)
    (output_dir / "gaspar_v2_1c_rolling_dataset_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown = markdown_summary(summary)
    (output_dir / "gaspar_v2_1c_rolling_dataset_summary.md").write_text(markdown, encoding="utf-8")
    Path(args.doc).write_text(markdown, encoding="utf-8")

    print(f"rows={len(rolling)}")
    print(f"regime_by_split={summary['label_distribution_by_split'][TARGET_REGIME]}")
    print(f"sell_by_split={summary['label_distribution_by_split'][TARGET_SELL]}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gaspar v2.1c rolling causal regime dataset.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def read_input(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df[df["split"].isin(["train", "validation", "test"])].copy()
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce").fillna(0.0)
    df["prediction"] = df["prediction"].astype(str)
    df = df.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)
    return df


def build_rolling_dataset(df: pd.DataFrame) -> pd.DataFrame:
    result = df[
        [
            "timestamp",
            "symbol",
            "split",
            "prediction",
            "realized_R",
            "context_quality_rr2",
            "regime",
            "market_structure",
            "h4_market_structure",
            "d1_market_structure",
            "daily_range_position",
            "atr",
        ]
    ].copy()

    past_all = {window: deque(maxlen=window) for window in WINDOWS}
    past_buy = {window: deque(maxlen=window) for window in WINDOWS}
    past_sell = {window: deque(maxlen=window) for window in WINDOWS}
    loss_streak = 0
    sell_loss_streak = 0

    feature_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        features: dict[str, Any] = {
            "recent_loss_streak": loss_streak,
            "recent_sell_loss_streak": sell_loss_streak,
        }
        for window in WINDOWS:
            all_values = list(past_all[window])
            buy_values = list(past_buy[window])
            sell_values = list(past_sell[window])
            features.update(prefix_metrics(f"rolling", window, all_values))
            features.update(prefix_metrics(f"rolling_buy", window, buy_values))
            features.update(prefix_metrics(f"rolling_sell", window, sell_values))
            features[f"rolling_unfavorable_rate_{window}"] = unfavorable_rate(all_values)
        features["rolling_drawdown_50"] = max_drawdown_series(list(past_all[50]))
        features["rolling_drawdown_100"] = max_drawdown_series(list(past_all[100]))
        features["rolling_2026q2_like_proxy"] = q2_like_proxy(features)
        feature_rows.append(features)

        value = float(row["realized_R"])
        direction = str(row["prediction"])
        for window in WINDOWS:
            past_all[window].append(value)
            if direction == "ENTER_BUY":
                past_buy[window].append(value)
            elif direction == "ENTER_SELL":
                past_sell[window].append(value)
        loss_streak = loss_streak + 1 if value < 0 else 0
        if direction == "ENTER_SELL":
            sell_loss_streak = sell_loss_streak + 1 if value < 0 else 0

    features_df = pd.DataFrame(feature_rows)
    labels_df = build_future_labels(df)
    return pd.concat([result, features_df, labels_df], axis=1)


def build_future_labels(df: pd.DataFrame) -> pd.DataFrame:
    r_values = df["realized_R"].astype(float).to_numpy()
    directions = df["prediction"].astype(str).to_numpy()
    rows = []
    for idx in range(len(df)):
        payload: dict[str, Any] = {}
        for window in WINDOWS:
            future = r_values[idx + 1 : idx + 1 + window]
            payload[f"regime_deteriorating_rr2_{window}"] = label_regime_future(future, window)
            sell_future = []
            j = idx + 1
            while j < len(df) and len(sell_future) < window:
                if directions[j] == "ENTER_SELL":
                    sell_future.append(float(r_values[j]))
                j += 1
            payload[f"sell_risk_next_window_{window}"] = label_sell_future(sell_future, window)
        payload[TARGET_REGIME] = payload[f"regime_deteriorating_rr2_{PRIMARY_WINDOW}"]
        payload[TARGET_SELL] = payload[f"sell_risk_next_window_{PRIMARY_WINDOW}"]
        rows.append(payload)
    return pd.DataFrame(rows)


def label_regime_future(values: np.ndarray, window: int) -> str:
    if len(values) < MIN_LABEL_FUTURE[window]:
        return "NEUTRAL"
    avg_r = float(np.mean(values))
    pf = profit_factor(values)
    if avg_r < 0 or pf < 1.0:
        return "DETERIORATING"
    return "STABLE"


def label_sell_future(values: list[float], window: int) -> str:
    if len(values) < MIN_LABEL_FUTURE[window]:
        return "NEUTRAL"
    avg_r = float(np.mean(values))
    pf = profit_factor(values)
    if avg_r < 0 or pf < 1.0:
        return "HIGH"
    if avg_r > 0 and pf >= 1.0:
        return "LOW"
    return "NEUTRAL"


def prefix_metrics(prefix: str, window: int, values: list[float]) -> dict[str, Any]:
    return {
        f"{prefix}_avg_R_{window}": mean_or_nan(values),
        f"{prefix}_pf_{window}": profit_factor(values),
        f"{prefix}_win_rate_{window}": win_rate(values),
        f"{prefix}_sample_size_{window}": len(values),
    }


def mean_or_nan(values: list[float]) -> float:
    return round_float(float(np.mean(values))) if values else math.nan


def win_rate(values: list[float]) -> float:
    return round_float(sum(1 for value in values if value > 0) / len(values)) if values else math.nan


def unfavorable_rate(values: list[float]) -> float:
    return round_float(sum(1 for value in values if value < -0.10) / len(values)) if values else math.nan


def profit_factor(values: Any) -> float:
    arr = np.array(values, dtype=float)
    if arr.size == 0:
        return math.nan
    wins = arr[arr > 0].sum()
    losses = arr[arr < 0].sum()
    if losses < 0:
        return round_float(float(wins / abs(losses)))
    if wins > 0:
        return math.inf
    return 0.0


def max_drawdown_series(values: list[float]) -> float:
    if not values:
        return math.nan
    equity = pd.Series(values, dtype=float).cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return round_float(float((peak - equity).max()))


def q2_like_proxy(features: dict[str, Any]) -> int:
    pf_50 = features.get("rolling_pf_50")
    sell_pf_50 = features.get("rolling_sell_pf_50")
    drawdown_50 = features.get("rolling_drawdown_50")
    unfavorable_50 = features.get("rolling_unfavorable_rate_50")
    if any(pd.isna(v) for v in [pf_50, sell_pf_50, drawdown_50, unfavorable_50]):
        return 0
    return int(float(pf_50) < 1.0 and float(sell_pf_50) < 1.0 and float(unfavorable_50) > 0.45 and float(drawdown_50) > 20)


def build_summary(df: pd.DataFrame, args: argparse.Namespace) -> dict[str, Any]:
    rolling_columns = [column for column in df.columns if column.startswith("rolling_") or column.startswith("recent_")]
    q2 = df[(df["timestamp"] >= pd.Timestamp("2026-04-01", tz="UTC")) & (df["timestamp"] <= pd.Timestamp("2026-04-14 23:59:59", tz="UTC"))]
    return {
        "schema_version": "gaspar_v2_1c_rolling_dataset_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input": str(args.input),
        "rows": int(len(df)),
        "split_rows": df.groupby("split").size().astype(int).to_dict(),
        "windows": WINDOWS,
        "primary_window": PRIMARY_WINDOW,
        "feature_columns": rolling_columns,
        "label_columns": [
            TARGET_REGIME,
            TARGET_SELL,
            *[f"regime_deteriorating_rr2_{window}" for window in WINDOWS],
            *[f"sell_risk_next_window_{window}" for window in WINDOWS],
        ],
        "label_distribution_by_split": {
            TARGET_REGIME: distribution_by_split(df, TARGET_REGIME),
            TARGET_SELL: distribution_by_split(df, TARGET_SELL),
        },
        "window_label_distribution": {
            f"regime_deteriorating_rr2_{window}": distribution_by_split(df, f"regime_deteriorating_rr2_{window}")
            for window in WINDOWS
        }
        | {
            f"sell_risk_next_window_{window}": distribution_by_split(df, f"sell_risk_next_window_{window}")
            for window in WINDOWS
        },
        "rolling_nulls": {column: int(df[column].isna().sum()) for column in rolling_columns},
        "deterioration_examples": examples(df, TARGET_REGIME, "DETERIORATING"),
        "sell_high_examples": examples(df, TARGET_SELL, "HIGH"),
        "q2_capture": {
            "rows": int(len(q2)),
            "regime_distribution": value_counts(q2[TARGET_REGIME]) if not q2.empty else {},
            "sell_distribution": value_counts(q2[TARGET_SELL]) if not q2.empty else {},
            "q2_like_proxy_rate": round_float(float(q2["rolling_2026q2_like_proxy"].mean())) if not q2.empty else None,
        },
        "causal_controls": [
            "All rolling feature columns use only previous trades and are shifted by construction.",
            "Future windows are used only to build target labels.",
            "No date, month or quarter is used as a predictive feature.",
            "The 2026Q2-like proxy uses only past rolling PF, sell PF, drawdown and unfavorable rate.",
        ],
    }


def distribution_by_split(df: pd.DataFrame, column: str) -> dict[str, dict[str, int]]:
    return {split: value_counts(part[column]) for split, part in df.groupby("split", dropna=False)}


def examples(df: pd.DataFrame, column: str, label: str) -> list[dict[str, Any]]:
    part = df[df[column].eq(label)].copy()
    if part.empty:
        return []
    keep = [
        "timestamp",
        "split",
        "prediction",
        "realized_R",
        "rolling_avg_R_50",
        "rolling_pf_50",
        "rolling_sell_avg_R_50",
        "rolling_sell_pf_50",
        "rolling_drawdown_50",
        "recent_loss_streak",
        "recent_sell_loss_streak",
        TARGET_REGIME,
        TARGET_SELL,
    ]
    return part.head(10)[keep].assign(timestamp=lambda x: x["timestamp"].astype(str)).to_dict(orient="records")


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Gaspar v2.1c Rolling Causal Dataset",
        "",
        "## Scope",
        "",
        "Each row is a selected Baltasar v2 trade with rolling system-state features computed only from previous trades.",
        "",
        "Targets use future windows and are labels only, never features.",
        "",
        "## Dataset Size",
        "",
        f"- Rows: `{summary['rows']:,}`",
        f"- Windows: `{summary['windows']}`",
        f"- Primary target window: `{summary['primary_window']}` trades",
        "",
        "## Split Rows",
        "",
        "| Split | Rows |",
        "| --- | ---: |",
    ]
    for split, rows in summary["split_rows"].items():
        lines.append(f"| {split} | {rows:,} |")
    lines.extend(
        [
            "",
            f"## `{TARGET_REGIME}` Distribution",
            "",
            split_distribution_table(summary["label_distribution_by_split"][TARGET_REGIME]),
            "",
            f"## `{TARGET_SELL}` Distribution",
            "",
            split_distribution_table(summary["label_distribution_by_split"][TARGET_SELL]),
            "",
            "## Rolling Nulls",
            "",
            null_table(summary["rolling_nulls"]),
            "",
            "## Deterioration Examples",
            "",
            examples_table(summary["deterioration_examples"]),
            "",
            "## SELL High Risk Examples",
            "",
            examples_table(summary["sell_high_examples"]),
            "",
            "## 2026Q2 Capture",
            "",
            f"- Rows: `{summary['q2_capture']['rows']:,}`",
            f"- Regime distribution: `{summary['q2_capture']['regime_distribution']}`",
            f"- SELL distribution: `{summary['q2_capture']['sell_distribution']}`",
            f"- 2026Q2-like proxy rate: `{summary['q2_capture']['q2_like_proxy_rate']}`",
            "",
            "## Causal Controls",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["causal_controls"])
    return "\n".join(lines) + "\n"


def split_distribution_table(distribution: dict[str, dict[str, int]]) -> str:
    labels = sorted({label for item in distribution.values() for label in item})
    rows = ["| Split | " + " | ".join(labels) + " |", "| --- | " + " | ".join(["---:"] * len(labels)) + " |"]
    for split, item in sorted(distribution.items()):
        rows.append("| " + split + " | " + " | ".join(f"{item.get(label, 0):,}" for label in labels) + " |")
    return "\n".join(rows)


def null_table(nulls: dict[str, int]) -> str:
    rows = ["| Column | Nulls |", "| --- | ---: |"]
    for column, count in sorted(nulls.items(), key=lambda item: item[1], reverse=True)[:25]:
        rows.append(f"| `{column}` | {count:,} |")
    return "\n".join(rows)


def examples_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No examples._"
    headers = list(rows[0].keys())
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(header)) for header in headers) + " |")
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
