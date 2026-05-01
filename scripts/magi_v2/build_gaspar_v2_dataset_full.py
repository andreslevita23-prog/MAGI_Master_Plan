from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import joblib
import pandas as pd


DEFAULT_MODEL = Path("data/output/magi_v2/baltasar_v2_rich_features_model/baltasar_v2_rich_model.joblib")
DEFAULT_RICH_FEATURES = Path("data/output/magi_v2/baltasar_v2_rich_features/baltasar_v2_rich_features.parquet")
DEFAULT_RR2_LABELS = Path("data/output/magi_v2/rr2_first_touch_labels/rr2_first_touch_labels.parquet")
DEFAULT_OUTPUT_DIR = Path("data/output/magi_v2/gaspar_v2_dataset_full")
DEFAULT_DOC = Path("docs/gaspar_v2_plan.md")

TARGET = "context_quality_rr2"
NEUTRAL_R_BAND = 0.10
POLICY_THRESHOLD = 0.40
DEFENSIVE_THRESHOLD = 0.50
BAD_HOURS = {13, 15, 16, 20, 22}
TRAIN_END = pd.Timestamp("2023-12-31 23:59:59", tz="UTC")
VALIDATION_END = pd.Timestamp("2024-12-31 23:59:59", tz="UTC")
TEST_END = pd.Timestamp("2026-04-14 23:59:59", tz="UTC")

TIMING_FEATURE_EXCLUSIONS = {"hour", "weekday", "session"}
FORBIDDEN_GASPAR_FEATURES = {
    TARGET,
    "tradeable_direction_rr2_first_touch",
    "buy_R",
    "sell_R",
    "buy_first_touch",
    "sell_first_touch",
    "buy_bars_to_exit",
    "sell_bars_to_exit",
    "same_bar_ambiguous_flag",
    "prediction",
    "base_prediction_040",
    "base_prediction_050",
    "policy_prediction_040",
    "policy_prediction_050",
    "realized_R",
    "selected_at_050",
    "policy_threshold",
    "baltasar_max_prob_040",
    "baltasar_max_prob_050",
}


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = joblib.load(args.model)
    pipeline = payload["pipeline"]
    model_features = list(payload["features"])

    rich = read_rich_features(Path(args.rich_features))
    labels = read_rr2_labels(Path(args.rr2_labels))
    verify_inputs(rich, labels, model_features)

    scored = score_baltasar_policy(rich, pipeline, model_features)
    selected = scored[scored["policy_prediction_040"].isin(["ENTER_BUY", "ENTER_SELL"])].copy()
    selected["prediction"] = selected["policy_prediction_040"]
    selected["policy_threshold"] = f"{POLICY_THRESHOLD:.2f}"
    selected["selected_at_050"] = selected["policy_prediction_050"].isin(["ENTER_BUY", "ENTER_SELL"])

    merged = join_labels(selected, labels)
    merged["realized_R"] = merged.apply(realized_r, axis=1)
    merged[TARGET] = merged.apply(label_context, axis=1)
    add_temporal_columns(merged)

    gaspar_features = choose_gaspar_features(merged)
    diagnostics = [
        "timestamp",
        "symbol",
        "split",
        "year",
        "quarter",
        "month",
        "prediction",
        "realized_R",
        "policy_threshold",
        "selected_at_050",
        "base_prediction_040",
        "policy_prediction_040",
        "baltasar_max_prob_040",
        "base_prediction_050",
        "policy_prediction_050",
        "baltasar_max_prob_050",
        "tradeable_direction_rr2_first_touch",
        "buy_R",
        "sell_R",
        "buy_first_touch",
        "sell_first_touch",
        "same_bar_ambiguous_flag",
        "session",
        "hour",
        "weekday",
    ]
    output_columns = [c for c in diagnostics if c in merged.columns] + [TARGET] + gaspar_features
    dataset = merged[dedupe_preserve_order(output_columns)].copy()

    dataset.to_parquet(output_dir / "gaspar_v2_dataset_full.parquet", index=False)
    dataset.to_csv(output_dir / "gaspar_v2_dataset_full.csv", index=False)
    train, validation, test = split_dataset(dataset)
    train.to_parquet(output_dir / "train.parquet", index=False)
    validation.to_parquet(output_dir / "validation.parquet", index=False)
    test.to_parquet(output_dir / "test.parquet", index=False)

    summary = build_summary(dataset, train, validation, test, gaspar_features, args)
    (output_dir / "gaspar_v2_dataset_full_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown = markdown_summary(summary)
    (output_dir / "gaspar_v2_dataset_full_summary.md").write_text(markdown, encoding="utf-8")
    Path(args.doc).write_text(markdown, encoding="utf-8")

    print(f"rows={len(dataset)}")
    print(f"train={len(train)} validation={len(validation)} test={len(test)}")
    print(f"label_by_split={summary['label_distribution_by_split']}")
    print("used_gaspar_training_v1=false")
    print(f"output_dir={output_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build full 2020-2026 Gaspar v2 context dataset.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--rich-features", default=str(DEFAULT_RICH_FEATURES))
    parser.add_argument("--rr2-labels", default=str(DEFAULT_RR2_LABELS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--doc", default=str(DEFAULT_DOC))
    return parser.parse_args()


def read_rich_features(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["symbol"] = df["symbol"].astype(str)
    return df.sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def read_rr2_labels(path: Path) -> pd.DataFrame:
    keep = [
        "timestamp",
        "symbol",
        "tradeable_direction_rr2_first_touch",
        "buy_R",
        "sell_R",
        "buy_first_touch",
        "sell_first_touch",
        "same_bar_ambiguous_flag",
    ]
    df = pd.read_parquet(path, columns=keep)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["symbol"] = df["symbol"].astype(str)
    return df.drop_duplicates(["timestamp", "symbol"]).reset_index(drop=True)


def verify_inputs(rich: pd.DataFrame, labels: pd.DataFrame, model_features: list[str]) -> None:
    missing_features = [c for c in model_features if c not in rich.columns]
    if missing_features:
        raise ValueError(f"Missing model features in rich dataset: {missing_features}")
    for name, df in [("rich", rich), ("labels", labels)]:
        if df.empty:
            raise ValueError(f"{name} dataset is empty")
        if df["timestamp"].min() > pd.Timestamp("2020-12-31", tz="UTC"):
            raise ValueError(f"{name} dataset does not cover train period: min={df['timestamp'].min()}")


def score_baltasar_policy(df: pd.DataFrame, pipeline: Any, model_features: list[str]) -> pd.DataFrame:
    out = df.copy()
    probabilities = pipeline.predict_proba(out[model_features])
    classes = list(pipeline.named_steps["model"].classes_)
    buy_idx = classes.index("ENTER_BUY")
    sell_idx = classes.index("ENTER_SELL")
    for threshold in [POLICY_THRESHOLD, DEFENSIVE_THRESHOLD]:
        key = threshold_key(threshold)
        base = []
        max_probs = []
        for row in probabilities:
            buy_prob = float(row[buy_idx])
            sell_prob = float(row[sell_idx])
            best_prob = max(buy_prob, sell_prob)
            max_probs.append(best_prob)
            if buy_prob >= sell_prob and buy_prob >= threshold:
                base.append("ENTER_BUY")
            elif sell_prob > buy_prob and sell_prob >= threshold:
                base.append("ENTER_SELL")
            else:
                base.append("DO_NOTHING")
        base_series = pd.Series(base, index=out.index)
        allowed = policy_medium_mask(out)
        out[f"base_prediction_{key}"] = base_series
        out[f"policy_prediction_{key}"] = base_series.where(
            allowed | ~base_series.isin(["ENTER_BUY", "ENTER_SELL"]),
            "DO_NOTHING",
        )
        out[f"baltasar_max_prob_{key}"] = max_probs
    return out


def policy_medium_mask(df: pd.DataFrame) -> pd.Series:
    hour = pd.to_numeric(df["hour"], errors="coerce")
    daily_range = pd.to_numeric(df["daily_range_position"], errors="coerce")
    session = df["session"].astype(str).str.lower()
    light = (session != "inactive") & ~((daily_range > 0.85) & daily_range.notna())
    return light & ~hour.isin(BAD_HOURS)


def join_labels(selected: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    label_columns = [
        "tradeable_direction_rr2_first_touch",
        "buy_R",
        "sell_R",
        "buy_first_touch",
        "sell_first_touch",
        "same_bar_ambiguous_flag",
    ]
    selected = selected.drop(columns=[c for c in label_columns if c in selected.columns])
    merged = selected.merge(labels, on=["timestamp", "symbol"], how="left", validate="many_to_one")
    missing = merged["buy_R"].isna() | merged["sell_R"].isna()
    if missing.any():
        raise ValueError(f"Missing RR2 labels for {int(missing.sum())} selected rows")
    return merged


def realized_r(row: pd.Series) -> float:
    if row["prediction"] == "ENTER_BUY":
        return float(row["buy_R"])
    if row["prediction"] == "ENTER_SELL":
        return float(row["sell_R"])
    return 0.0


def label_context(row: pd.Series) -> str:
    ambiguous_value = row.get("same_bar_ambiguous_flag", False)
    ambiguous = False if pd.isna(ambiguous_value) else bool(ambiguous_value)
    r_value = row.get("realized_R")
    if pd.isna(r_value) or ambiguous or abs(float(r_value)) <= NEUTRAL_R_BAND:
        return "NEUTRAL"
    if float(r_value) > NEUTRAL_R_BAND:
        return "FAVORABLE"
    return "UNFAVORABLE"


def add_temporal_columns(df: pd.DataFrame) -> None:
    ts = df["timestamp"]
    naive = ts.dt.tz_convert("UTC").dt.tz_localize(None)
    df["split"] = ts.apply(split_name)
    df["year"] = naive.dt.year.astype(str)
    df["quarter"] = naive.dt.to_period("Q").astype(str)
    df["month"] = naive.dt.to_period("M").astype(str)


def split_name(timestamp: pd.Timestamp) -> str:
    if timestamp <= TRAIN_END:
        return "train"
    if timestamp <= VALIDATION_END:
        return "validation"
    if timestamp <= TEST_END:
        return "test"
    return "outside"


def split_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        df[df["split"].eq("train")].copy(),
        df[df["split"].eq("validation")].copy(),
        df[df["split"].eq("test")].copy(),
    )


def choose_gaspar_features(df: pd.DataFrame) -> list[str]:
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
    return [
        c
        for c in dedupe_preserve_order(preferred)
        if c in df.columns and c not in TIMING_FEATURE_EXCLUSIONS and c not in FORBIDDEN_GASPAR_FEATURES
    ]


def build_summary(
    dataset: pd.DataFrame,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    return {
        "schema_version": "gaspar_v2_dataset_full_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model": str(args.model),
        "rich_features": str(args.rich_features),
        "rr2_labels": str(args.rr2_labels),
        "explicitly_not_used": ["gaspar_training_v1", "existing gaspar_v2_dataset.parquet", "policy_trades.csv as base"],
        "policy": {
            "variant": "rich_policy_medium",
            "threshold": f"{POLICY_THRESHOLD:.2f}",
            "rules": [
                "Baltasar rich model directional probability threshold >= 0.40",
                "block session == inactive",
                "block daily_range_position > 0.85",
                f"block hours {sorted(BAD_HOURS)}",
            ],
        },
        "rows": int(len(dataset)),
        "columns": int(len(dataset.columns)),
        "feature_columns": feature_columns,
        "feature_column_count": len(feature_columns),
        "temporal_range": {
            "min": dataset["timestamp"].min().isoformat() if not dataset.empty else None,
            "max": dataset["timestamp"].max().isoformat() if not dataset.empty else None,
        },
        "split_rows": {
            "train": int(len(train)),
            "validation": int(len(validation)),
            "test": int(len(test)),
        },
        "has_valid_train_2020_2023": bool(len(train) > 0),
        "label_distribution": value_counts(dataset[TARGET]),
        "label_distribution_by_split": {
            "train": value_counts(train[TARGET]),
            "validation": value_counts(validation[TARGET]),
            "test": value_counts(test[TARGET]),
        },
        "selected_at_050": {
            "rows": int(dataset["selected_at_050"].sum()),
            "share": round(float(dataset["selected_at_050"].mean()), 6),
        },
        "gaspar_training_v1_used": False,
        "leakage_check": {
            "forbidden_feature_intersection": sorted(set(feature_columns) & FORBIDDEN_GASPAR_FEATURES),
            "timing_feature_intersection": sorted(set(feature_columns) & TIMING_FEATURE_EXCLUSIONS),
        },
    }


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Gaspar v2 Full Dataset",
        "",
        "## Status",
        "",
        "Rebuilt from the complete 2020-2026 MAGI v2 base, not from `policy_trades.csv` and not from `gaspar_training_v1`.",
        "",
        "## Sources",
        "",
        f"- Rich features: `{summary['rich_features']}`",
        f"- RR2 first-touch labels: `{summary['rr2_labels']}`",
        f"- Baltasar v2 rich model: `{summary['model']}`",
        "- Explicitly not used as base: `gaspar_training_v1`, old `gaspar_v2_dataset.parquet`, `policy_trades.csv`.",
        "",
        "## Policy Applied",
        "",
    ]
    lines.extend(f"- {rule}" for rule in summary["policy"]["rules"])
    lines.extend(
        [
            "",
            "## Dataset Size",
            "",
            f"- Rows: `{summary['rows']:,}`",
            f"- Columns: `{summary['columns']:,}`",
            f"- Feature columns for Gaspar: `{summary['feature_column_count']:,}`",
            f"- Temporal range: `{summary['temporal_range']['min']}` to `{summary['temporal_range']['max']}`",
            f"- Valid train 2020-2023: `{summary['has_valid_train_2020_2023']}`",
            "",
            "## Split Rows",
            "",
            "| Split | Rows |",
            "| --- | ---: |",
        ]
    )
    for split, rows in summary["split_rows"].items():
        lines.append(f"| {split} | {rows:,} |")
    lines.extend(["", "## Label Distribution by Split", ""])
    for split, distribution in summary["label_distribution_by_split"].items():
        lines.extend([f"### {split}", "", "| Label | Rows |", "| --- | ---: |"])
        for label, count in distribution.items():
            lines.append(f"| {label} | {count:,} |")
        lines.append("")
    lines.extend(
        [
            "## Leakage Check",
            "",
            f"- Forbidden feature intersection: `{summary['leakage_check']['forbidden_feature_intersection']}`",
            f"- Direct timing feature intersection: `{summary['leakage_check']['timing_feature_intersection']}`",
            f"- Gaspar v1 used: `{summary['gaspar_training_v1_used']}`",
            "",
            "## Next Step",
            "",
            "Train `Gaspar v2 context classifier` using the generated `train.parquet`, `validation.parquet`, and `test.parquet` splits.",
        ]
    )
    return "\n".join(lines) + "\n"


def threshold_key(threshold: float) -> str:
    return f"{int(round(threshold * 100)):03d}"


def value_counts(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.fillna("NULL").value_counts(dropna=False).to_dict().items()}


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
