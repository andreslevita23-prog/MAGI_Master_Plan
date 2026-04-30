from __future__ import annotations

import argparse
import csv
import json
import logging
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import accuracy_score, mutual_info_score, normalized_mutual_info_score


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
DEFAULT_INPUT = RUN_DIR / "ceo_final_dataset.parquet"
DEFAULT_RAW_JSONL = RUN_DIR / "ceo_training_records.jsonl"
DEFAULT_OUTPUT_DIR = RUN_DIR / "label_audit"

LABEL = "ceo_label_h48"
HORIZON = "48"
ACTION_LABELS = ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"]
NUMERIC_CONTEXT_COLUMNS = ["atr", "daily_range_position", "spread"]


def main() -> int:
    args = parse_args()
    setup_logging()

    input_path = Path(args.input)
    raw_jsonl = Path(args.raw_jsonl)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading final dataset: %s", input_path)
    df = pd.read_parquet(input_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["year"] = df["timestamp"].dt.year.astype("Int64").astype("string")
    logging.info("Rows loaded: %s", len(df))

    write_crosstab(output_dir / "label_distribution_by_year.csv", df, "year", LABEL)
    write_crosstab(output_dir / "label_distribution_by_session.csv", df, "session", LABEL)
    write_crosstab(output_dir / "label_vs_baltasar_crosstab.csv", df, LABEL, "baltasar_signal")
    write_crosstab(output_dir / "label_vs_gaspar_crosstab.csv", df, LABEL, "gaspar_signal")
    write_crosstab(output_dir / "label_vs_regime_crosstab.csv", df, LABEL, "regime")

    logging.info("Inspecting raw JSONL outcomes: %s", raw_jsonl)
    raw_audit = inspect_raw_outcomes(raw_jsonl, df)

    metrics = build_metrics(df, raw_audit)
    (output_dir / "label_audit_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "label_audit_summary.md").write_text(markdown_summary(metrics), encoding="utf-8")
    logging.info("Label audit written to %s", output_dir)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit CEO-MAGI labels and outcome fields.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input ceo_final_dataset.parquet path.")
    parser.add_argument("--raw-jsonl", default=str(DEFAULT_RAW_JSONL), help="Raw ceo_training_records.jsonl path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output label audit directory.")
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_metrics(df: pd.DataFrame, raw_audit: dict[str, Any]) -> dict[str, Any]:
    baltasar_rule = df["baltasar_signal"].map(label_from_direction)
    crosstab_abs = pd.crosstab(df[LABEL], df["baltasar_signal"])
    crosstab_pct = normalize_crosstab(crosstab_abs)

    metrics = {
        "schema_version": "ceo_label_audit_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows": int(len(df)),
        "label_distribution": value_counts(df[LABEL]),
        "dependency_label_vs_baltasar": {
            "crosstab_absolute": dataframe_dict(crosstab_abs),
            "crosstab_overall_percent": crosstab_pct,
            "mutual_information": round(float(mutual_info_score(df[LABEL].astype(str), df["baltasar_signal"].astype(str))), 6),
            "normalized_mutual_information": round(float(normalized_mutual_info_score(df[LABEL].astype(str), df["baltasar_signal"].astype(str))), 6),
            "simple_baltasar_rule_accuracy": round(float(accuracy_score(df[LABEL], baltasar_rule)), 6),
            "structural_coupling": {
                "enter_buy_without_baltasar_buy": int(((df[LABEL] == "ENTER_BUY") & (df["baltasar_signal"] != "BUY")).sum()),
                "enter_sell_without_baltasar_sell": int(((df[LABEL] == "ENTER_SELL") & (df["baltasar_signal"] != "SELL")).sum()),
                "neutral_with_enter_label": int(((df["baltasar_signal"] == "NEUTRAL") & (df[LABEL] != "DO_NOTHING")).sum()),
            },
        },
        "relationships": {
            "gaspar_signal": crosstab_summary(df, "gaspar_signal"),
            "session": crosstab_summary(df, "session"),
            "regime_top_by_enter_rate": top_regimes(df),
            "numeric_context_by_label": numeric_context_by_label(df),
            "numeric_context_correlations": numeric_context_correlations(df),
        },
        "raw_future_outcomes": raw_audit["future_outcomes"],
        "candidate_label_distributions": raw_audit["candidate_label_distributions"],
        "candidate_label_vs_baltasar_accuracy": raw_audit["candidate_label_vs_baltasar_accuracy"],
        "usable_numeric_outcome_fields": usable_numeric_outcome_fields(raw_audit["future_outcomes"]),
        "alternative_label_proposals": alternative_label_proposals(raw_audit["future_outcomes"]),
        "missing_data_for_institutional_labels": missing_data_for_institutional_labels(),
        "technical_decisions": [
            "The final dataset is not modified by this audit.",
            "Candidate labels are computed in memory from current final features plus raw H48 numeric outcomes.",
            "No model is trained.",
            "Mutual information uses sklearn.metrics on categorical string values.",
        ],
    }
    return metrics


def inspect_raw_outcomes(raw_jsonl: Path, df: pd.DataFrame) -> dict[str, Any]:
    if not raw_jsonl.exists():
        raise FileNotFoundError(f"Missing raw CEO JSONL: {raw_jsonl}")

    field_stats: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(new_field_stats))
    candidate_counts = {
        "ceo_label_h48_strict": Counter(),
        "ceo_label_h48_ev": Counter(),
        "ceo_label_h48_directional_filtered": Counter(),
        "ceo_label_h48_tradeable": Counter(),
    }
    candidate_vs_baltasar_hits = {name: 0 for name in candidate_counts}
    rows = 0

    with raw_jsonl.open("r", encoding="utf-8-sig") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            record = json.loads(line)
            if index >= len(df):
                break
            final_row = df.iloc[index]
            outcomes = record.get("future_outcomes") if isinstance(record.get("future_outcomes"), dict) else {}
            for horizon, outcome in outcomes.items():
                if not isinstance(outcome, dict):
                    continue
                for field, value in outcome.items():
                    update_field_stats(field_stats[str(horizon)][str(field)], value)

            h48 = outcomes.get(HORIZON) if isinstance(outcomes.get(HORIZON), dict) else {}
            labels = candidate_labels(final_row, h48)
            for name, label in labels.items():
                candidate_counts[name][label] += 1
                if label == label_from_direction(final_row.get("baltasar_signal")):
                    candidate_vs_baltasar_hits[name] += 1

            rows += 1
            if rows % 50000 == 0:
                logging.info("Inspected %s raw records", rows)

    return {
        "records_inspected": rows,
        "future_outcomes": finalize_field_stats(field_stats),
        "candidate_label_distributions": {
            name: dict(sorted(counter.items()))
            for name, counter in candidate_counts.items()
        },
        "candidate_label_vs_baltasar_accuracy": {
            name: round(hits / rows, 6) if rows else None
            for name, hits in candidate_vs_baltasar_hits.items()
        },
    }


def candidate_labels(row: pd.Series, outcome: dict[str, Any]) -> dict[str, str]:
    direction = str(row.get("baltasar_signal") or "").upper()
    melchor = str(row.get("melchor_signal") or "").upper()
    gaspar = str(row.get("gaspar_signal") or "").upper()
    session = str(row.get("session") or "").lower()
    alignment = str(row.get("baltasar_gaspar_alignment") or "").upper()
    spread = as_float(row.get("spread")) or 0.0
    atr = as_float(row.get("atr"))
    daily_range_position = as_float(row.get("daily_range_position"))
    future_return_pips = as_float(outcome.get("future_return_pips"))
    mfe = as_float(outcome.get("max_favorable_excursion"))
    mae = as_float(outcome.get("max_adverse_excursion"))

    return {
        "ceo_label_h48_strict": label_strict(direction, melchor, gaspar, spread, future_return_pips, mfe, mae),
        "ceo_label_h48_ev": label_ev(direction, spread, future_return_pips),
        "ceo_label_h48_directional_filtered": label_directional_filtered(
            direction, melchor, gaspar, session, alignment, atr, daily_range_position, spread, future_return_pips
        ),
        "ceo_label_h48_tradeable": label_tradeable(
            direction, melchor, gaspar, session, alignment, atr, daily_range_position, spread, future_return_pips, mfe, mae
        ),
    }


def label_strict(direction: str, melchor: str, gaspar: str, spread: float, future_return_pips: float | None, mfe: float | None, mae: float | None) -> str:
    if direction not in {"BUY", "SELL"} or melchor != "APPROVE" or gaspar == "POOR" or future_return_pips is None:
        return "DO_NOTHING"
    required_net = max(6.0, spread * 2.0)
    adverse_limit = 12.0
    if direction == "BUY" and future_return_pips >= required_net and enough_excursion(mfe, mae, adverse_limit):
        return "ENTER_BUY"
    if direction == "SELL" and -future_return_pips >= required_net and enough_excursion(mfe, mae, adverse_limit):
        return "ENTER_SELL"
    return "DO_NOTHING"


def label_ev(direction: str, spread: float, future_return_pips: float | None) -> str:
    if direction not in {"BUY", "SELL"} or future_return_pips is None:
        return "DO_NOTHING"
    if direction == "BUY":
        net = future_return_pips - spread
        return "ENTER_BUY" if net >= 5.0 else "DO_NOTHING"
    net = -future_return_pips - spread
    return "ENTER_SELL" if net >= 5.0 else "DO_NOTHING"


def label_directional_filtered(
    direction: str,
    melchor: str,
    gaspar: str,
    session: str,
    alignment: str,
    atr: float | None,
    daily_range_position: float | None,
    spread: float,
    future_return_pips: float | None,
) -> str:
    if direction not in {"BUY", "SELL"} or future_return_pips is None:
        return "DO_NOTHING"
    if melchor != "APPROVE" or gaspar == "POOR" or session not in {"london", "new_york", "overlap"}:
        return "DO_NOTHING"
    if spread > 2.0 or (atr is not None and atr > 1.2):
        return "DO_NOTHING"
    if daily_range_position is not None and not 0.15 <= daily_range_position <= 0.85:
        return "DO_NOTHING"
    if alignment in {"DIRECTION_MISMATCH", "DIRECTION_REJECTED_BY_GASPAR"}:
        return "DO_NOTHING"
    if direction == "BUY" and future_return_pips >= 5.0:
        return "ENTER_BUY"
    if direction == "SELL" and future_return_pips <= -5.0:
        return "ENTER_SELL"
    return "DO_NOTHING"


def label_tradeable(
    direction: str,
    melchor: str,
    gaspar: str,
    session: str,
    alignment: str,
    atr: float | None,
    daily_range_position: float | None,
    spread: float,
    future_return_pips: float | None,
    mfe: float | None,
    mae: float | None,
) -> str:
    base = label_directional_filtered(direction, melchor, gaspar, session, alignment, atr, daily_range_position, spread, future_return_pips)
    if base == "DO_NOTHING":
        return base
    if not enough_excursion(mfe, mae, adverse_limit=10.0):
        return "DO_NOTHING"
    if direction == "BUY" and future_return_pips is not None and future_return_pips - spread >= 7.0:
        return "ENTER_BUY"
    if direction == "SELL" and future_return_pips is not None and -future_return_pips - spread >= 7.0:
        return "ENTER_SELL"
    return "DO_NOTHING"


def enough_excursion(mfe: float | None, mae: float | None, adverse_limit: float) -> bool:
    if mfe is None or mae is None:
        return False
    return mfe >= 8.0 and abs(mae) <= adverse_limit


def write_crosstab(path: Path, df: pd.DataFrame, index: str, column: str) -> None:
    table = pd.crosstab(df[index].fillna("UNKNOWN"), df[column].fillna("UNKNOWN"))
    table.to_csv(path, encoding="utf-8")


def normalize_crosstab(table: pd.DataFrame) -> dict[str, dict[str, float]]:
    total = table.to_numpy().sum()
    if total == 0:
        return {}
    return {
        str(index): {
            str(column): round(float(value) / float(total), 6)
            for column, value in row.items()
        }
        for index, row in table.iterrows()
    }


def dataframe_dict(table: pd.DataFrame) -> dict[str, dict[str, int]]:
    return {
        str(index): {
            str(column): int(value)
            for column, value in row.items()
        }
        for index, row in table.iterrows()
    }


def crosstab_summary(df: pd.DataFrame, column: str) -> dict[str, Any]:
    table = pd.crosstab(df[column].fillna("UNKNOWN"), df[LABEL].fillna("UNKNOWN"))
    rows = {}
    for index, row in table.iterrows():
        total = int(row.sum())
        enters = int(row.get("ENTER_BUY", 0) + row.get("ENTER_SELL", 0))
        rows[str(index)] = {
            "rows": total,
            "enter_rate": round(enters / total, 6) if total else None,
            "label_distribution": {str(key): int(value) for key, value in row.items()},
        }
    return rows


def top_regimes(df: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    table = pd.crosstab(df["regime"].fillna("UNKNOWN"), df[LABEL].fillna("UNKNOWN"))
    rows = []
    for regime, row in table.iterrows():
        total = int(row.sum())
        if total < 500:
            continue
        enters = int(row.get("ENTER_BUY", 0) + row.get("ENTER_SELL", 0))
        rows.append({
            "regime": str(regime),
            "rows": total,
            "enter_rate": round(enters / total, 6),
            "enter_buy": int(row.get("ENTER_BUY", 0)),
            "enter_sell": int(row.get("ENTER_SELL", 0)),
            "do_nothing": int(row.get("DO_NOTHING", 0)),
        })
    return sorted(rows, key=lambda item: item["enter_rate"], reverse=True)[:limit]


def numeric_context_by_label(df: pd.DataFrame) -> dict[str, Any]:
    result = {}
    for column in NUMERIC_CONTEXT_COLUMNS:
        groups = {}
        for label, values in df.groupby(LABEL, dropna=False)[column]:
            numeric = pd.to_numeric(values, errors="coerce")
            groups[str(label)] = {
                "count": int(numeric.count()),
                "mean": round_float(numeric.mean()),
                "median": round_float(numeric.median()),
                "p25": round_float(numeric.quantile(0.25)),
                "p75": round_float(numeric.quantile(0.75)),
            }
        result[column] = groups
    return result


def numeric_context_correlations(df: pd.DataFrame) -> dict[str, Any]:
    enter = df[LABEL].isin(["ENTER_BUY", "ENTER_SELL"]).astype(int)
    result = {}
    for column in NUMERIC_CONTEXT_COLUMNS:
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.nunique(dropna=True) < 2:
            result[column] = None
        else:
            result[column] = round_float(numeric.corr(enter))
    return result


def new_field_stats() -> dict[str, Any]:
    return {
        "present_count": 0,
        "numeric_count": 0,
        "string_count": 0,
        "bool_count": 0,
        "null_count": 0,
        "min": None,
        "max": None,
        "examples": [],
    }


def update_field_stats(stats: dict[str, Any], value: Any) -> None:
    stats["present_count"] += 1
    if value is None:
        stats["null_count"] += 1
        return
    if isinstance(value, bool):
        stats["bool_count"] += 1
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        stats["numeric_count"] += 1
        number = float(value)
        stats["min"] = number if stats["min"] is None else min(stats["min"], number)
        stats["max"] = number if stats["max"] is None else max(stats["max"], number)
    elif isinstance(value, str):
        stats["string_count"] += 1
    if len(stats["examples"]) < 3 and value not in stats["examples"]:
        stats["examples"].append(value)


def finalize_field_stats(field_stats: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    final = {}
    for horizon, fields in field_stats.items():
        final[horizon] = {}
        for field, stats in fields.items():
            final[horizon][field] = {
                **stats,
                "min": round_float(stats["min"]),
                "max": round_float(stats["max"]),
            }
    return final


def usable_numeric_outcome_fields(outcome_stats: dict[str, Any]) -> dict[str, list[str]]:
    usable = {}
    for horizon, fields in outcome_stats.items():
        usable[horizon] = [
            field for field, stats in fields.items()
            if stats.get("numeric_count", 0) > 0
        ]
    return usable


def alternative_label_proposals(outcome_stats: dict[str, Any]) -> dict[str, Any]:
    h48_fields = outcome_stats.get(HORIZON, {})
    has = lambda field: field in h48_fields and h48_fields[field].get("present_count", 0) > 0
    return {
        "ceo_label_h48_strict": {
            "status": "implementable_with_current_data",
            "rule": "ENTER only when Baltasar is directional, Melchor APPROVE, Gaspar not POOR, absolute H48 move clears max(6 pips, 2x spread), MFE >= 8 pips, and abs(MAE) <= 12 pips.",
            "required_fields_available": all(has(field) for field in ["future_return_pips", "max_favorable_excursion", "max_adverse_excursion"]),
        },
        "ceo_label_h48_ev": {
            "status": "partially_implementable_with_current_data",
            "rule": "Use spread-adjusted realized directional pips as EV proxy; true EV requires costs and many-sample expectation by state/regime.",
            "required_fields_available": has("future_return_pips"),
        },
        "ceo_label_h48_directional_filtered": {
            "status": "implementable_with_current_data",
            "rule": "Use direction but require Melchor APPROVE, Gaspar not POOR, tradeable session, spread <= 2, ATR <= 1.2, D1 range position inside 0.15-0.85, and no Gaspar direction mismatch/rejection.",
            "required_fields_available": has("future_return_pips"),
        },
        "ceo_label_h48_tradeable": {
            "status": "partially_implementable_with_current_data",
            "rule": "Combine contextual filters, spread-adjusted realized movement, MFE/MAE limits; institutional version still needs explicit SL/TP, costs, slippage and R multiple.",
            "required_fields_available": all(has(field) for field in ["future_return_pips", "max_favorable_excursion", "max_adverse_excursion"]),
        },
    }


def missing_data_for_institutional_labels() -> list[str]:
    return [
        "Explicit entry/exit simulation per candidate signal with SL, TP, timeout and exit reason.",
        "Spread, commission and slippage adjusted net PnL.",
        "R multiple per trade candidate.",
        "Hit TP / hit SL flags and order of intrabar hit when both are touched.",
        "Realized drawdown path while trade is open.",
        "Position sizing and account-level risk impact.",
        "News/event blackout flags if those will be hard risk filters.",
        "Out-of-sample regime identifiers not derived from future performance.",
    ]


def label_from_direction(value: Any) -> str:
    text = str(value or "").upper()
    if text in {"BUY", "ENTER_BUY", "LONG"}:
        return "ENTER_BUY"
    if text in {"SELL", "ENTER_SELL", "SHORT"}:
        return "ENTER_SELL"
    return "DO_NOTHING"


def value_counts(series: pd.Series) -> dict[str, int]:
    return dict(sorted(Counter("UNKNOWN" if pd.isna(value) else str(value) for value in series).items()))


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def round_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def markdown_summary(metrics: dict[str, Any]) -> str:
    dep = metrics["dependency_label_vs_baltasar"]
    lines = [
        "# CEO-MAGI Label Audit",
        "",
        f"- generated_at: {metrics['generated_at']}",
        f"- rows: {metrics['rows']}",
        f"- label_distribution: {json.dumps(metrics['label_distribution'], sort_keys=True)}",
        "",
        "## Label vs Baltasar",
        "",
        f"- mutual_information: {dep['mutual_information']}",
        f"- normalized_mutual_information: {dep['normalized_mutual_information']}",
        f"- simple_baltasar_rule_accuracy: {dep['simple_baltasar_rule_accuracy']}",
        f"- ENTER_BUY without Baltasar BUY: {dep['structural_coupling']['enter_buy_without_baltasar_buy']}",
        f"- ENTER_SELL without Baltasar SELL: {dep['structural_coupling']['enter_sell_without_baltasar_sell']}",
        f"- Baltasar NEUTRAL with enter label: {dep['structural_coupling']['neutral_with_enter_label']}",
        "",
        "## Raw H48 Outcome Fields",
        outcome_table(metrics["raw_future_outcomes"].get(HORIZON, {})),
        "",
        "## Candidate Label Distributions",
        "| Candidate | DO_NOTHING | ENTER_BUY | ENTER_SELL | Baltasar-rule accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, dist in metrics["candidate_label_distributions"].items():
        lines.append(
            f"| {name} | {dist.get('DO_NOTHING', 0)} | {dist.get('ENTER_BUY', 0)} | "
            f"{dist.get('ENTER_SELL', 0)} | {metrics['candidate_label_vs_baltasar_accuracy'].get(name)} |"
        )
    lines.extend([
        "",
        "## Proposed Labels",
    ])
    for name, proposal in metrics["alternative_label_proposals"].items():
        lines.extend([
            f"### {name}",
            f"- status: {proposal['status']}",
            f"- required_fields_available: {proposal['required_fields_available']}",
            f"- rule: {proposal['rule']}",
            "",
        ])
    lines.extend([
        "## Missing Data For Institutional Labels",
        *[f"- {item}" for item in metrics["missing_data_for_institutional_labels"]],
    ])
    return "\n".join(lines) + "\n"


def outcome_table(fields: dict[str, Any]) -> str:
    lines = [
        "| Field | Present | Numeric | String | Bool | Min | Max | Examples |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for field, stats in sorted(fields.items()):
        lines.append(
            f"| {field} | {stats['present_count']} | {stats['numeric_count']} | {stats['string_count']} | "
            f"{stats['bool_count']} | {stats['min']} | {stats['max']} | {json.dumps(stats['examples'])} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
