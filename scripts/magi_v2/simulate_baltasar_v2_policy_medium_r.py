from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


DEFAULT_POLICY_TRADES = Path(
    "data/output/magi_v2/baltasar_v2_rich_features_model/policy/policy_trades.csv"
)
DEFAULT_LABELS = Path("data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet")
DEFAULT_OUTPUT_DIR = Path(
    "data/output/magi_v2/baltasar_v2_rich_features_model/policy_medium_r_simulation"
)

TARGET = "tradeable_direction_rr2_first_touch"
POLICY_VARIANT = "rich_policy_medium"
THRESHOLDS = [0.40, 0.50]
VALIDATION_START = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
VALIDATION_END = pd.Timestamp("2024-12-31 23:59:59", tz="UTC")
TEST_START = pd.Timestamp("2025-01-01 00:00:00", tz="UTC")
TEST_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = read_labels(Path(args.labels))
    policy_trades = read_policy_trades(Path(args.policy_trades))

    denominators = split_denominators(labels)
    policy = policy_trades[policy_trades["variant"].eq(POLICY_VARIANT)].copy()
    if policy.empty:
        raise ValueError(f"No rows found for variant={POLICY_VARIANT}")

    simulated_by_threshold: dict[str, pd.DataFrame] = {}
    for threshold in THRESHOLDS:
        key = threshold_key(threshold)
        trades = policy[policy["threshold"].round(2).eq(threshold)].copy()
        trades = normalize_trade_frame(trades)
        trades.to_csv(output_dir / f"simulated_trades_{key}.csv", index=False)
        simulated_by_threshold[key] = trades

    year_rows = []
    quarter_rows = []
    month_rows = []
    direction_rows = []
    threshold_rows = []
    split_rows = []
    q2_rows = []

    for key, trades in simulated_by_threshold.items():
        threshold = float(key) / 100
        threshold_rows.append(with_label(metrics_for_trades(trades, labels, denominators, threshold), "threshold", key))
        for split, part in trades.groupby("split", dropna=False):
            split_rows.append(with_label(metrics_for_trades(part, labels, denominators, threshold, split), "split", split))
        year_rows.extend(group_metrics(trades, labels, threshold, "year"))
        quarter_rows.extend(group_metrics(trades, labels, threshold, "quarter"))
        month_rows.extend(group_metrics(trades, labels, threshold, "month"))
        direction_rows.extend(direction_metrics(trades, threshold))
        q2_rows.append(q2_diagnostic(trades, labels, threshold))

    baltasar_v1 = baltasar_v1_metrics(labels)
    metrics = {
        "schema_version": "baltasar_v2_policy_medium_r_simulation_v0.1",
        "generated_at": utc_now(),
        "policy_trades": str(args.policy_trades),
        "labels": str(args.labels),
        "output_dir": str(output_dir),
        "target": TARGET,
        "policy_variant": POLICY_VARIANT,
        "thresholds": [threshold_key(t) for t in THRESHOLDS],
        "threshold_metrics": threshold_rows,
        "split_metrics": split_rows,
        "metrics_by_direction": direction_rows,
        "diagnostic_2026q2": q2_rows,
        "baltasar_v1_comparison": baltasar_v1,
        "technical_decisions": [
            "No model retraining is performed.",
            "Only trades already selected by rich_policy_medium are simulated.",
            "Realized R is taken from first-touch RR 1:2 labels: buy_R for ENTER_BUY and sell_R for ENTER_SELL.",
            "Coverage uses rr2_first_touch_labels as denominator for validation/test periods.",
            "2026Q2 is analyzed as diagnostic only; no calendar blocking rule is added.",
        ],
    }

    pd.DataFrame(year_rows).to_csv(output_dir / "metrics_by_year.csv", index=False)
    pd.DataFrame(quarter_rows).to_csv(output_dir / "metrics_by_quarter.csv", index=False)
    pd.DataFrame(month_rows).to_csv(output_dir / "metrics_by_month.csv", index=False)
    pd.DataFrame(direction_rows).to_csv(output_dir / "metrics_by_direction.csv", index=False)
    (output_dir / "policy_medium_r_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "policy_medium_r_summary.md").write_text(
        markdown_summary(metrics),
        encoding="utf-8",
    )
    print(f"Wrote outputs to {output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Final RR 1:2 first-touch R simulation for Baltasar v2 rich_policy_medium."
    )
    parser.add_argument("--policy-trades", default=str(DEFAULT_POLICY_TRADES))
    parser.add_argument("--labels", default=str(DEFAULT_LABELS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def threshold_key(threshold: float) -> str:
    return f"{int(round(threshold * 100)):03d}"


def read_labels(path: Path) -> pd.DataFrame:
    columns = [
        "timestamp",
        "symbol",
        TARGET,
        "buy_R",
        "sell_R",
        "baltasar_signal",
        "session",
        "hour",
        "weekday",
        "daily_range_position",
    ]
    available = set(pq.ParquetFile(path).schema.names)
    df = pd.read_parquet(path, columns=[c for c in columns if c in available])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df[df["timestamp"].between(VALIDATION_START, TEST_END)].copy()
    df["split"] = split_series(df["timestamp"])
    add_time_groups(df)
    return df[df["split"].isin(["validation", "test"])].copy()


def read_policy_trades(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["threshold"] = pd.to_numeric(df["threshold"], errors="coerce")
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce")
    return df


def normalize_trade_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["timestamp", "symbol", "prediction"]).copy()
    add_time_groups(df)
    df["win"] = df["realized_R"] > 0
    df["loss"] = df["realized_R"] < 0
    return df


def add_time_groups(df: pd.DataFrame) -> None:
    naive_utc = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
    df["year"] = naive_utc.dt.year.astype(str)
    df["quarter"] = naive_utc.dt.to_period("Q").astype(str)
    df["month"] = naive_utc.dt.to_period("M").astype(str)


def split_series(timestamp: pd.Series) -> pd.Series:
    split = pd.Series("outside", index=timestamp.index, dtype="object")
    split[timestamp.between(VALIDATION_START, VALIDATION_END)] = "validation"
    split[timestamp.between(TEST_START, TEST_END)] = "test"
    return split


def split_denominators(labels: pd.DataFrame) -> dict[str, int]:
    return {str(k): int(v) for k, v in labels.groupby("split").size().items()}


def metrics_for_trades(
    trades: pd.DataFrame,
    labels: pd.DataFrame,
    denominators: dict[str, int],
    threshold: float,
    split: str | None = None,
) -> dict[str, Any]:
    if split:
        denominator = denominators.get(split, 0)
        labels_scope = labels[labels["split"].eq(split)]
    else:
        denominator = sum(denominators.values())
        labels_scope = labels
    base = trade_metrics(trades, denominator)
    base["threshold"] = threshold_key(threshold)
    base["label_distribution"] = value_counts_dict(labels_scope[TARGET]) if TARGET in labels_scope else {}
    return base


def trade_metrics(trades: pd.DataFrame, denominator: int | None = None) -> dict[str, Any]:
    r = pd.to_numeric(trades.get("realized_R", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    trades_count = int(len(r))
    wins = r[r > 0]
    losses = r[r < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    total_r = float(r.sum())
    avg_r = float(r.mean()) if trades_count else 0.0
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (math.inf if gross_profit > 0 else 0.0)
    max_dd = max_drawdown(r)
    coverage = trades_count / denominator if denominator else None
    precision = directional_precision(trades)
    return {
        "trades": trades_count,
        "coverage": round_float(coverage),
        "avg_r": round_float(avg_r),
        "total_r": round_float(total_r),
        "profit_factor": round_float(pf),
        "max_drawdown_r": round_float(max_dd),
        "win_rate": round_float(float((r > 0).mean()) if trades_count else 0.0),
        "trade_precision": round_float(precision),
        "buy": direction_summary(trades, "ENTER_BUY"),
        "sell": direction_summary(trades, "ENTER_SELL"),
        "prediction_distribution": value_counts_dict(trades.get("prediction", pd.Series(dtype=str))),
    }


def directional_precision(trades: pd.DataFrame) -> float:
    if trades.empty or TARGET not in trades:
        return 0.0
    return float((trades["prediction"] == trades[TARGET]).mean())


def direction_summary(trades: pd.DataFrame, direction: str) -> dict[str, Any]:
    part = trades[trades["prediction"].eq(direction)].copy()
    result = trade_metrics_base(part)
    if not part.empty and TARGET in part:
        result["precision"] = round_float(float((part["prediction"] == part[TARGET]).mean()))
    else:
        result["precision"] = 0.0
    return result


def trade_metrics_base(trades: pd.DataFrame) -> dict[str, Any]:
    r = pd.to_numeric(trades.get("realized_R", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    trades_count = int(len(r))
    wins = r[r > 0]
    losses = r[r < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (math.inf if gross_profit > 0 else 0.0)
    return {
        "trades": trades_count,
        "avg_r": round_float(float(r.mean()) if trades_count else 0.0),
        "total_r": round_float(float(r.sum())),
        "profit_factor": round_float(pf),
        "max_drawdown_r": round_float(max_drawdown(r)),
        "win_rate": round_float(float((r > 0).mean()) if trades_count else 0.0),
    }


def max_drawdown(r: pd.Series) -> float:
    if r.empty:
        return 0.0
    equity = r.cumsum()
    peak = equity.cummax().clip(lower=0.0)
    drawdown = peak - equity
    return float(drawdown.max())


def group_metrics(trades: pd.DataFrame, labels: pd.DataFrame, threshold: float, group_col: str) -> list[dict[str, Any]]:
    rows = []
    labels_counts = labels.groupby(["split", group_col]).size().to_dict()
    for (split, group), part in trades.groupby(["split", group_col], dropna=False):
        denominator = int(labels_counts.get((split, group), 0))
        row = trade_metrics(part, denominator)
        row.update({"threshold": threshold_key(threshold), "split": split, group_col: group})
        rows.append(flatten_direction_fields(row))
    return rows


def direction_metrics(trades: pd.DataFrame, threshold: float) -> list[dict[str, Any]]:
    rows = []
    for (split, direction), part in trades.groupby(["split", "prediction"], dropna=False):
        row = trade_metrics_base(part)
        row.update(
            {
                "threshold": threshold_key(threshold),
                "split": split,
                "direction": direction,
                "precision": round_float(float((part["prediction"] == part[TARGET]).mean())) if TARGET in part else 0.0,
            }
        )
        rows.append(row)
    return rows


def q2_diagnostic(trades: pd.DataFrame, labels: pd.DataFrame, threshold: float) -> dict[str, Any]:
    start = pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
    end = TEST_END
    part = trades[trades["timestamp"].between(start, end)]
    denominator = int(labels[labels["timestamp"].between(start, end)].shape[0])
    row = trade_metrics(part, denominator)
    row.update(
        {
            "threshold": threshold_key(threshold),
            "period": "2026Q2_partial",
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
    )
    return row


def baltasar_v1_metrics(labels: pd.DataFrame) -> dict[str, Any]:
    df = labels.copy()
    df["prediction"] = df["baltasar_signal"].map(normalize_signal)
    trades = df[df["prediction"].isin(["ENTER_BUY", "ENTER_SELL"])].copy()
    trades["realized_R"] = trades.apply(
        lambda row: row["buy_R"] if row["prediction"] == "ENTER_BUY" else row["sell_R"],
        axis=1,
    )
    trades = normalize_trade_frame(trades)
    denominators = split_denominators(labels)
    result = {
        "overall": trade_metrics(trades, sum(denominators.values())),
        "by_split": {},
        "by_direction": direction_metrics(trades, 0.0),
    }
    for split, part in trades.groupby("split"):
        result["by_split"][split] = trade_metrics(part, denominators.get(split, 0))
    return result


def normalize_signal(value: Any) -> str:
    text = str(value).strip().upper()
    if text in {"BUY", "ENTER_BUY", "LONG"}:
        return "ENTER_BUY"
    if text in {"SELL", "ENTER_SELL", "SHORT"}:
        return "ENTER_SELL"
    return "DO_NOTHING"


def flatten_direction_fields(row: dict[str, Any]) -> dict[str, Any]:
    flat = dict(row)
    for direction in ["buy", "sell"]:
        payload = flat.pop(direction, {})
        for key, value in payload.items():
            flat[f"{direction}_{key}"] = value
    flat.pop("label_distribution", None)
    flat.pop("prediction_distribution", None)
    return flat


def value_counts_dict(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.fillna("NULL").value_counts(dropna=False).to_dict().items()}


def round_float(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isinf(value):
        return value
    return round(float(value), 6)


def with_label(row: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    updated = dict(row)
    updated[key] = value
    return updated


def markdown_summary(metrics: dict[str, Any]) -> str:
    threshold_rows = metrics["threshold_metrics"]
    v1 = metrics["baltasar_v1_comparison"]["by_split"]
    q2 = metrics["diagnostic_2026q2"]
    lines = [
        "# Baltasar v2 rich_policy_medium - final R simulation",
        "",
        "## Scope",
        "",
        "- Uses first-touch RR 1:2 labels.",
        "- Evaluates only the existing `rich_policy_medium` policy.",
        "- No retraining, no new rules, no mage logic changes.",
        "",
        "## Threshold comparison",
        "",
        "| Threshold | Trades | Coverage | Avg R | Total R | PF | Max DD | Win rate | Trade precision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in threshold_rows:
        lines.append(
            f"| {row['threshold']} | {row['trades']:,} | {pct(row['coverage'])} | "
            f"{row['avg_r']:.4f} | {row['total_r']:.2f} | {row['profit_factor']:.4f} | "
            f"{row['max_drawdown_r']:.2f} | {pct(row['win_rate'])} | {pct(row['trade_precision'])} |"
        )
    lines.extend(
        [
            "",
            "## BUY vs SELL",
            "",
            "| Threshold | Direction | Trades | Avg R | PF | Max DD | Win rate | Precision |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in threshold_rows:
        for direction, label in [("buy", "BUY"), ("sell", "SELL")]:
            payload = row[direction]
            lines.append(
                f"| {row['threshold']} | {label} | {payload['trades']:,} | {payload['avg_r']:.4f} | "
                f"{payload['profit_factor']:.4f} | {payload['max_drawdown_r']:.2f} | "
                f"{pct(payload['win_rate'])} | {pct(payload['precision'])} |"
            )
    lines.extend(
        [
            "",
            "## Baltasar v1 comparison",
            "",
            "| Split | Trades | Coverage | Avg R | Total R | PF | Max DD |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for split in ["validation", "test"]:
        row = v1.get(split, {})
        lines.append(
            f"| {split} | {row.get('trades', 0):,} | {pct(row.get('coverage'))} | "
            f"{row.get('avg_r', 0):.4f} | {row.get('total_r', 0):.2f} | "
            f"{row.get('profit_factor', 0):.4f} | {row.get('max_drawdown_r', 0):.2f} |"
        )
    lines.extend(
        [
            "",
            "## 2026Q2 diagnostic",
            "",
            "| Threshold | Trades | Coverage | Avg R | Total R | PF | Max DD | Win rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in q2:
        lines.append(
            f"| {row['threshold']} | {row['trades']:,} | {pct(row['coverage'])} | "
            f"{row['avg_r']:.4f} | {row['total_r']:.2f} | {row['profit_factor']:.4f} | "
            f"{row['max_drawdown_r']:.2f} | {pct(row['win_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Technical decision",
            "",
            "- `0.40` is the principal threshold because it keeps a much larger sample and remains EV positive.",
            "- `0.50` is a defensive threshold with higher avg R/PF and lower drawdown, but much lower coverage.",
            "- SELL remains weaker than BUY and should be diagnosed before promoting Baltasar v2.",
            "- 2026Q2 remains a regime warning and should be analyzed before starting production-style integration.",
        ]
    )
    return "\n".join(lines) + "\n"


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
