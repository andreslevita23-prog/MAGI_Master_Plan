from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_ROLLING = Path("data/output/magi_v2/gaspar_v2_1c_rolling_dataset/gaspar_v2_1c_rolling_dataset.parquet")
DEFAULT_INTEGRATED = Path("data/output/magi_v2/baltasar_gaspar_v2_integration/integrated_trades.csv")
DEFAULT_Q2_ANALYSIS = Path("data/output/magi_v2/2026q2_regime_analysis/2026q2_regime_analysis.json")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/melchor_v2_risk_dataset")
DEFAULT_DOC = Path("docs/melchor_v2_risk_dataset.md")

PRIMARY_FUTURE_WINDOW = 50
MIN_FUTURE_TRADES = 20
Q2_START = pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
Q2_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")

REQUESTED_FEATURES = [
    "rolling_pf_20",
    "rolling_pf_50",
    "rolling_pf_100",
    "rolling_avg_R_20",
    "rolling_avg_R_50",
    "rolling_avg_R_100",
    "rolling_drawdown_50",
    "rolling_drawdown_100",
    "rolling_win_rate_20",
    "rolling_win_rate_50",
    "rolling_win_rate_100",
    "rolling_unfavorable_rate_50",
    "rolling_unfavorable_rate_100",
    "rolling_sell_pf_20",
    "rolling_sell_pf_50",
    "rolling_sell_pf_100",
    "rolling_sell_avg_R_20",
    "rolling_sell_avg_R_50",
    "rolling_sell_avg_R_100",
    "recent_loss_streak",
    "recent_sell_loss_streak",
    "spread_pips",
    "volatility_12",
    "daily_range_position",
    "close_to_ema200",
    "ema_20_50_distance",
    "ema_50_200_distance",
    "predicted_direction",
]

FORBIDDEN_FEATURES = {
    "realized_R",
    "risk_block_rr2",
    "risk_block_rr2_strict",
    "risk_block_rr2_soft",
    "future_avg_R_50",
    "future_pf_50",
    "future_drawdown_50",
    "future_sell_avg_R_50",
    "future_sell_pf_50",
    "future_sell_drawdown_50",
    "timestamp",
    "year",
    "quarter",
    "month",
}


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rolling = read_rolling(Path(args.rolling_dataset))
    integrated = read_integrated(Path(args.integrated_trades))
    q2_analysis = read_json(Path(args.q2_analysis))
    df = merge_inputs(rolling, integrated)
    dataset = build_dataset(df)

    dataset.to_parquet(output_dir / "melchor_v2_risk_dataset.parquet", index=False)
    summary = build_summary(dataset, q2_analysis, args)
    (output_dir / "melchor_v2_risk_dataset_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown = markdown_summary(summary)
    (output_dir / "melchor_v2_risk_dataset_summary.md").write_text(markdown, encoding="utf-8")
    Path(args.doc).write_text(markdown, encoding="utf-8")

    print(f"rows={len(dataset)}")
    print(f"risk_block_rr2={dataset['risk_block_rr2'].value_counts().to_dict()}")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Melchor v2 accumulated risk dataset.")
    parser.add_argument("--rolling-dataset", default=str(DEFAULT_ROLLING))
    parser.add_argument("--integrated-trades", default=str(DEFAULT_INTEGRATED))
    parser.add_argument("--q2-analysis", default=str(DEFAULT_Q2_ANALYSIS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def read_rolling(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)


def read_integrated(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        usecols=lambda c: c
        in {
            "timestamp",
            "symbol",
            "prediction",
            "gaspar_p_deteriorating",
            "gaspar_block",
        },
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df.drop_duplicates(["timestamp", "symbol", "prediction"])


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def merge_inputs(rolling: pd.DataFrame, integrated: pd.DataFrame) -> pd.DataFrame:
    df = rolling.merge(integrated, on=["timestamp", "symbol", "prediction"], how="left")
    df["gaspar_p_deteriorating"] = pd.to_numeric(df["gaspar_p_deteriorating"], errors="coerce")
    df["gaspar_block"] = df["gaspar_block"].fillna(False).astype(bool)
    df["predicted_direction"] = df["prediction"].map({"ENTER_BUY": "BUY", "ENTER_SELL": "SELL"}).fillna("NONE")
    return df.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)


def build_dataset(df: pd.DataFrame) -> pd.DataFrame:
    feature_columns = [column for column in REQUESTED_FEATURES if column in df.columns]
    keep = [
        "timestamp",
        "symbol",
        "split",
        "prediction",
        "realized_R",
        "gaspar_p_deteriorating",
        "gaspar_block",
        *feature_columns,
    ]
    out = df[keep].copy()
    future = future_metrics(df)
    out = pd.concat([out, future], axis=1)
    out["risk_block_rr2_strict"] = out.apply(label_strict, axis=1)
    out["risk_block_rr2_soft"] = out.apply(label_soft, axis=1)
    out["risk_block_rr2"] = out["risk_block_rr2_soft"]
    out["is_2026q2"] = out["timestamp"].between(Q2_START, Q2_END)
    return out


def future_metrics(df: pd.DataFrame) -> pd.DataFrame:
    r = df["realized_R"].astype(float).to_numpy()
    direction = df["predicted_direction"].astype(str).to_numpy()
    rows = []
    for idx in range(len(df)):
        future = r[idx + 1 : idx + 1 + PRIMARY_FUTURE_WINDOW]
        future_sell = []
        j = idx + 1
        while j < len(df) and len(future_sell) < PRIMARY_FUTURE_WINDOW:
            if direction[j] == "SELL":
                future_sell.append(float(r[j]))
            j += 1
        rows.append(
            {
                "future_sample_size_50": int(len(future)),
                "future_avg_R_50": mean_or_nan(future),
                "future_pf_50": profit_factor(future),
                "future_drawdown_50": max_drawdown(future),
                "future_sell_sample_size_50": int(len(future_sell)),
                "future_sell_avg_R_50": mean_or_nan(future_sell),
                "future_sell_pf_50": profit_factor(future_sell),
                "future_sell_drawdown_50": max_drawdown(future_sell),
            }
        )
    return pd.DataFrame(rows)


def label_soft(row: pd.Series) -> str:
    if row["future_sample_size_50"] < MIN_FUTURE_TRADES:
        return "CAUTION"
    avg_r = as_float(row["future_avg_R_50"])
    pf = as_float(row["future_pf_50"])
    dd = as_float(row["future_drawdown_50"])
    sell_avg = as_float(row["future_sell_avg_R_50"])
    sell_pf = as_float(row["future_sell_pf_50"])
    if avg_r < 0 or pf < 1.0 or dd >= 30 or (sell_avg < 0 and sell_pf < 1.0):
        return "BLOCK"
    if avg_r > 0.03 and pf >= 1.05 and dd < 25:
        return "APPROVE"
    return "CAUTION"


def label_strict(row: pd.Series) -> str:
    if row["future_sample_size_50"] < MIN_FUTURE_TRADES:
        return "CAUTION"
    avg_r = as_float(row["future_avg_R_50"])
    pf = as_float(row["future_pf_50"])
    dd = as_float(row["future_drawdown_50"])
    sell_avg = as_float(row["future_sell_avg_R_50"])
    sell_pf = as_float(row["future_sell_pf_50"])
    if (avg_r < -0.05 and pf < 0.95) or dd >= 40 or (sell_avg < -0.05 and sell_pf < 0.95):
        return "BLOCK"
    if avg_r > 0.05 and pf >= 1.10 and dd < 25:
        return "APPROVE"
    return "CAUTION"


def build_summary(dataset: pd.DataFrame, q2_analysis: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    feature_columns = [column for column in REQUESTED_FEATURES if column in dataset.columns]
    missing_features = [column for column in REQUESTED_FEATURES if column not in dataset.columns]
    q2 = dataset[dataset["is_2026q2"]]
    summary = {
        "schema_version": "melchor_v2_risk_dataset_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "rolling_dataset": str(args.rolling_dataset),
            "integrated_trades": str(args.integrated_trades),
            "q2_analysis": str(args.q2_analysis),
        },
        "rows": int(len(dataset)),
        "feature_columns": feature_columns,
        "missing_requested_features": missing_features,
        "forbidden_feature_intersection": sorted(set(feature_columns) & FORBIDDEN_FEATURES),
        "label_distribution_by_split": {
            "risk_block_rr2": distribution_by_split(dataset, "risk_block_rr2"),
            "risk_block_rr2_strict": distribution_by_split(dataset, "risk_block_rr2_strict"),
            "risk_block_rr2_soft": distribution_by_split(dataset, "risk_block_rr2_soft"),
        },
        "train_block_count": int(
            dataset[dataset["split"].eq("train") & dataset["risk_block_rr2"].eq("BLOCK")].shape[0]
        ),
        "q2_capture": {
            "rows": int(len(q2)),
            "risk_block_rr2": value_counts(q2["risk_block_rr2"]),
            "risk_block_rr2_strict": value_counts(q2["risk_block_rr2_strict"]),
            "risk_block_rr2_soft": value_counts(q2["risk_block_rr2_soft"]),
        },
        "null_counts": {
            column: int(dataset[column].isna().sum())
            for column in feature_columns
            if int(dataset[column].isna().sum()) > 0
        },
        "q2_analysis_key_rules": [
            item.get("rule")
            for item in q2_analysis.get("candidate_rules", [])
            if item.get("rule") in {"rolling_sell_pf_below_1", "rolling_pf_below_1_and_drawdown_high", "q2_like_proxy"}
        ],
        "causal_controls": [
            "Feature columns are past rolling state or current pre-trade context only.",
            "Future R/PF/DD columns are target-construction diagnostics and must not be model features.",
            "No date, month, quarter or 2026Q2 flag is a feature.",
            "Labels use future windows by design because they are supervised targets.",
        ],
    }
    summary["ready_for_training"] = summary["train_block_count"] >= 1000 and not summary["forbidden_feature_intersection"]
    return summary


def distribution_by_split(df: pd.DataFrame, column: str) -> dict[str, dict[str, int]]:
    return {split: value_counts(part[column]) for split, part in df.groupby("split", dropna=False)}


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Melchor v2 Risk Dataset",
        "",
        "## Scope",
        "",
        "Each row is a Baltasar+Gaspar candidate trade. Melchor v2 evaluates accumulated operational risk before allowing it.",
        "",
        "## Dataset Size",
        "",
        f"- Rows: `{summary['rows']:,}`",
        f"- Feature columns available: `{len(summary['feature_columns'])}`",
        f"- Missing requested features: `{summary['missing_requested_features']}`",
        f"- Ready for training: `{summary['ready_for_training']}`",
        "",
        "## Label Distribution",
        "",
        "### risk_block_rr2",
        "",
        split_table(summary["label_distribution_by_split"]["risk_block_rr2"]),
        "",
        "### risk_block_rr2_strict",
        "",
        split_table(summary["label_distribution_by_split"]["risk_block_rr2_strict"]),
        "",
        "### risk_block_rr2_soft",
        "",
        split_table(summary["label_distribution_by_split"]["risk_block_rr2_soft"]),
        "",
        "## 2026Q2 Capture",
        "",
        f"- Rows: `{summary['q2_capture']['rows']:,}`",
        f"- Main label: `{summary['q2_capture']['risk_block_rr2']}`",
        f"- Strict: `{summary['q2_capture']['risk_block_rr2_strict']}`",
        f"- Soft: `{summary['q2_capture']['risk_block_rr2_soft']}`",
        "",
        "## Leakage Check",
        "",
        f"- Forbidden feature intersection: `{summary['forbidden_feature_intersection']}`",
        "- `realized_R`, future R/PF/DD, labels, dates and 2026Q2 flags are diagnostics/labels only, not features.",
        "",
        "## Nulls",
        "",
        null_table(summary["null_counts"]),
        "",
        "## Causal Controls",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["causal_controls"])
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "Train Melchor v2 as a three-class risk layer (`APPROVE`, `CAUTION`, `BLOCK`) if the training distribution has enough `BLOCK` examples and operational filtering improves validation/test.",
        ]
    )
    return "\n".join(lines) + "\n"


def split_table(distribution: dict[str, dict[str, int]]) -> str:
    labels = sorted({label for item in distribution.values() for label in item})
    rows = ["| Split | " + " | ".join(labels) + " |", "| --- | " + " | ".join(["---:"] * len(labels)) + " |"]
    for split, item in sorted(distribution.items()):
        rows.append("| " + split + " | " + " | ".join(f"{item.get(label, 0):,}" for label in labels) + " |")
    return "\n".join(rows)


def null_table(nulls: dict[str, int]) -> str:
    if not nulls:
        return "_No feature nulls._"
    rows = ["| Column | Nulls |", "| --- | ---: |"]
    for column, count in sorted(nulls.items(), key=lambda item: item[1], reverse=True):
        rows.append(f"| `{column}` | {count:,} |")
    return "\n".join(rows)


def mean_or_nan(values: Any) -> float:
    arr = np.array(values, dtype=float)
    return round_float(float(np.mean(arr))) if arr.size else math.nan


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


def max_drawdown(values: Any) -> float:
    arr = np.array(values, dtype=float)
    if arr.size == 0:
        return math.nan
    equity = pd.Series(arr).cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return round_float(float((peak - equity).max()))


def as_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)


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
