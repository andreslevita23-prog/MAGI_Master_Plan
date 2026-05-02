from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SOURCE_TRADES = Path("artifacts/magi_validation/online_priority_scoring_trades.csv")
SOURCE_PLANS = Path("artifacts/magi_realistic_scenario_c/scenario_c_realistic_trades.csv")
OUTPUT_DIR = Path("artifacts/ceo_magi_v3")
DECISIONS_CSV = OUTPUT_DIR / "ceo_magi_v3_decisions.csv"
DECISIONS_JSONL = OUTPUT_DIR / "ceo_magi_v3_decisions.jsonl"
SUMMARY_MD = OUTPUT_DIR / "ceo_magi_v3_summary.md"
SUMMARY_JSON = OUTPUT_DIR / "ceo_magi_v3_summary.json"

SOURCE_STRATEGY = "A_base_scenario_c"
POLICY_NAME = "CEO-MAGI v3"
SCHEMA_VERSION = "ceo_magi_v3.entry_decision.v1"
MIN_OPERATIONAL_SCORE = 0.20
GASPAR_HIGH_DETERIORATION = 0.70
SL_PIPS = 10.0
RR_MULTIPLE = 2.0


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    trades = load_source()
    decisions = build_decisions(trades)
    decisions.to_csv(DECISIONS_CSV, index=False)
    write_jsonl(decisions)

    summary = build_summary(decisions)
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_MD.write_text(markdown_summary(summary), encoding="utf-8")

    test_metrics = summary["metrics"]["test"]
    print(f"decisions={len(decisions)}")
    print(f"enter_decisions={summary['counts']['by_action'].get('ENTER', 0)}")
    print(f"do_nothing_decisions={summary['counts']['by_action'].get('DO_NOTHING', 0)}")
    print(f"test_pf={test_metrics['profit_factor']}")
    print(f"test_avg_r={test_metrics['avg_r']}")
    print(f"test_max_dd={test_metrics['max_drawdown_r']}")
    print(f"output_csv={DECISIONS_CSV}")
    print(f"output_jsonl={DECISIONS_JSONL}")
    print(f"output_md={SUMMARY_MD}")
    print(f"output_json={SUMMARY_JSON}")


def load_source() -> pd.DataFrame:
    if not SOURCE_TRADES.exists():
        raise FileNotFoundError(f"Missing source trades: {SOURCE_TRADES}")

    source = pd.read_csv(SOURCE_TRADES)
    source = source[source["priority_strategy"].eq(SOURCE_STRATEGY)].copy()
    if source.empty:
        raise ValueError(f"No rows found for priority_strategy={SOURCE_STRATEGY!r}")

    source["timestamp"] = pd.to_datetime(source["timestamp"], utc=True, errors="coerce")
    source["exit_timestamp"] = pd.to_datetime(source["exit_timestamp"], utc=True, errors="coerce")

    if SOURCE_PLANS.exists():
        plans = pd.read_csv(SOURCE_PLANS)
        plan_cols = [
            "timestamp",
            "symbol",
            "split",
            "prediction",
            "entry_price",
            "exit_timestamp_raw",
            "is_timeout",
            "first_touch",
            "bars_to_exit",
        ]
        available = [col for col in plan_cols if col in plans.columns]
        plans = plans[available].copy()
        plans["timestamp"] = pd.to_datetime(plans["timestamp"], utc=True, errors="coerce")
        source = source.merge(
            plans,
            on=["timestamp", "symbol", "split", "prediction"],
            how="left",
            suffixes=("", "_plan"),
        )
    else:
        source["entry_price"] = np.nan
        source["exit_timestamp_raw"] = pd.NaT
        source["is_timeout"] = False
        source["first_touch"] = ""
        source["bars_to_exit"] = np.nan

    numeric_cols = ["priority_score", "baltasar_confidence", "gaspar_p_deteriorating", "gross_r", "adjusted_R", "entry_price"]
    for col in numeric_cols:
        if col in source.columns:
            source[col] = pd.to_numeric(source[col], errors="coerce")

    source = source.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)
    return source


def build_decisions(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index, row in trades.iterrows():
        score = safe_float(row.get("priority_score"), 0.0)
        gaspar_p = safe_float(row.get("gaspar_p_deteriorating"), 0.0)
        melchor_signal = normalize(row.get("melchor_signal"), "UNKNOWN")
        prediction = normalize(row.get("prediction"), "NO_SIGNAL")
        direction = direction_from_prediction(prediction)
        timestamp = row["timestamp"]
        symbol = str(row.get("symbol", "UNKNOWN"))
        decision_id = f"{symbol}-{timestamp.isoformat().replace('+00:00', 'Z')}-{index:06d}"

        action = "DO_NOTHING"
        mode = "none"
        base_mode = "none"
        reason_code = "score_below_0_20"
        gaspar_downgraded = False
        risk_notes: list[str] = []

        if melchor_signal == "BLOCK":
            reason_code = "melchor_block"
            risk_notes.append("Melchor BLOCK: hard veto.")
        elif direction is None:
            reason_code = "no_valid_baltasar_direction"
            risk_notes.append("Baltasar did not provide a valid BUY/SELL direction.")
        elif score < MIN_OPERATIONAL_SCORE:
            reason_code = "score_below_0_20"
            risk_notes.append("Score below validated operational threshold.")
        else:
            action = "ENTER"
            if score < 0.30:
                base_mode = "cautious"
                reason_code = "score_cautious"
            elif score < 0.40:
                base_mode = "normal"
                reason_code = "score_normal"
            else:
                base_mode = "premium"
                reason_code = "score_premium"

            mode = base_mode
            risk_notes.append(f"Score accepted in {base_mode} band.")
            if gaspar_p >= GASPAR_HIGH_DETERIORATION:
                gaspar_downgraded = True
                if mode == "premium":
                    mode = "normal"
                    reason_code = "score_premium_gaspar_downgraded"
                elif mode == "normal":
                    mode = "cautious"
                    reason_code = "score_normal_gaspar_downgraded"
                risk_notes.append("Gaspar deterioration is high; execution mode downgraded.")

        entry_price = safe_float(row.get("entry_price"), math.nan)
        stop_loss, take_profit = stops_from_plan(entry_price, direction) if action == "ENTER" else (math.nan, math.nan)
        realized_r = safe_float(row.get("adjusted_R"), math.nan) if action == "ENTER" else math.nan
        hypothetical_r = safe_float(row.get("adjusted_R"), math.nan)

        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "decision_id": decision_id,
                "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                "exit_timestamp": timestamp_to_json(row.get("exit_timestamp"))
                or timestamp_to_json(row.get("exit_timestamp_raw")),
                "symbol": symbol,
                "split": row.get("split"),
                "action": action,
                "aggression_mode": mode,
                "base_aggression_mode": base_mode,
                "direction": direction if action == "ENTER" else "",
                "entry_price": round_float(entry_price) if action == "ENTER" else np.nan,
                "stop_loss": round_float(stop_loss) if action == "ENTER" else np.nan,
                "take_profit": round_float(take_profit) if action == "ENTER" else np.nan,
                "score": round_float(score, 6),
                "baltasar_signal": prediction,
                "baltasar_confidence": round_float(safe_float(row.get("baltasar_confidence"), 0.0), 6),
                "gaspar_signal": gaspar_signal_from_probability(gaspar_p),
                "gaspar_p_deteriorating": round_float(gaspar_p, 6),
                "gaspar_high_deterioration": bool(gaspar_p >= GASPAR_HIGH_DETERIORATION),
                "gaspar_downgraded": gaspar_downgraded,
                "melchor_signal": melchor_signal,
                "melchor_risk_flags": row.get("melchor_risk_flags", ""),
                "context_quality_rr2": row.get("context_quality_rr2", ""),
                "reason_code": reason_code,
                "risk_notes": " | ".join(risk_notes),
                "realized_R": round_float(realized_r, 6) if math.isfinite(realized_r) else np.nan,
                "hypothetical_adjusted_R": round_float(hypothetical_r, 6) if math.isfinite(hypothetical_r) else np.nan,
                "gross_r": round_float(safe_float(row.get("gross_r"), math.nan), 6),
                "spread_r": round_float(safe_float(row.get("spread_r"), math.nan), 6),
                "commission_r": round_float(safe_float(row.get("commission_r"), math.nan), 6),
                "slippage_r": round_float(safe_float(row.get("slippage_r"), math.nan), 6),
                "is_2026q2": is_2026q2(timestamp),
                "source_strategy": SOURCE_STRATEGY,
                "policy": POLICY_NAME,
                "score_formula": "unchanged_online_priority_score",
                "min_operational_score": MIN_OPERATIONAL_SCORE,
            }
        )

    return pd.DataFrame(rows)


def write_jsonl(decisions: pd.DataFrame) -> None:
    with DECISIONS_JSONL.open("w", encoding="utf-8") as handle:
        for record in decisions.to_dict(orient="records"):
            payload = bot_b_payload(record)
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def bot_b_payload(record: dict[str, Any]) -> dict[str, Any]:
    action = record["action"]
    payload = {
        "schema_version": record["schema_version"],
        "decision_id": record["decision_id"],
        "timestamp": record["timestamp"],
        "symbol": record["symbol"],
        "action": action,
        "aggression_mode": record["aggression_mode"],
        "execution_mode": record["aggression_mode"],
        "direction": record["direction"] if action == "ENTER" else None,
        "entry_price": json_number(record["entry_price"]) if action == "ENTER" else None,
        "stop_loss": json_number(record["stop_loss"]) if action == "ENTER" else None,
        "take_profit": json_number(record["take_profit"]) if action == "ENTER" else None,
        "score": json_number(record["score"]),
        "reason_code": record["reason_code"],
        "reason_codes": [record["reason_code"]],
        "risk_notes": split_notes(record.get("risk_notes", "")),
        "votes": {
            "baltasar": {
                "signal": record["baltasar_signal"],
                "direction": direction_from_prediction(record["baltasar_signal"]),
                "confidence": json_number(record["baltasar_confidence"]),
            },
            "gaspar": {
                "signal": record["gaspar_signal"],
                "p_deteriorating": json_number(record["gaspar_p_deteriorating"]),
                "high_deterioration": bool(record["gaspar_high_deterioration"]),
                "downgraded_aggression": bool(record["gaspar_downgraded"]),
            },
            "melchor": {
                "signal": record["melchor_signal"],
                "risk_flags": split_flags(record.get("melchor_risk_flags", "")),
            },
        },
        "source": {
            "policy": record["policy"],
            "score_formula": record["score_formula"],
            "min_operational_score": record["min_operational_score"],
            "offline_source_strategy": record["source_strategy"],
        },
    }
    return payload


def build_summary(decisions: pd.DataFrame) -> dict[str, Any]:
    counts = {
        "total_decisions": int(len(decisions)),
        "by_action": int_counts(decisions["action"]),
        "by_aggression_mode": int_counts(decisions["aggression_mode"]),
        "by_reason_code": int_counts(decisions["reason_code"]),
        "top_reason_codes": int_counts(decisions["reason_code"].head(0)),
    }
    counts["top_reason_codes"] = {
        str(k): int(v) for k, v in decisions["reason_code"].value_counts().head(10).items()
    }

    metrics = {
        "all": metric_row(decisions),
        "train": metric_row(decisions[decisions["split"].eq("train")]),
        "validation": metric_row(decisions[decisions["split"].eq("validation")]),
        "test": metric_row(decisions[decisions["split"].eq("test")]),
        "2026Q2": metric_row(decisions[decisions["is_2026q2"].eq(True)]),
    }

    test_enter = decisions[decisions["split"].eq("test") & decisions["action"].eq("ENTER")].copy()
    direction = {
        "BUY": metric_row(test_enter[test_enter["direction"].eq("BUY")]),
        "SELL": metric_row(test_enter[test_enter["direction"].eq("SELL")]),
    }

    warnings = operational_warnings(decisions, metrics)
    return {
        "source": {
            "input_trades": str(SOURCE_TRADES),
            "input_trade_plans": str(SOURCE_PLANS),
            "source_strategy": SOURCE_STRATEGY,
            "policy_doc": "docs/ceo_magi_v3_decision_logic.md",
            "realized_r_column": "adjusted_R",
        },
        "policy": {
            "name": POLICY_NAME,
            "schema_version": SCHEMA_VERSION,
            "min_operational_score": MIN_OPERATIONAL_SCORE,
            "gaspar_high_deterioration": GASPAR_HIGH_DETERIORATION,
            "melchor_block_is_hard_veto": True,
        },
        "counts": counts,
        "metrics": metrics,
        "direction_breakdown_test": direction,
        "operational_warnings": warnings,
        "outputs": {
            "decisions_csv": str(DECISIONS_CSV),
            "decisions_jsonl": str(DECISIONS_JSONL),
            "summary_md": str(SUMMARY_MD),
            "summary_json": str(SUMMARY_JSON),
        },
    }


def metric_row(frame: pd.DataFrame) -> dict[str, Any]:
    enter = frame[frame["action"].eq("ENTER")].copy()
    r = pd.to_numeric(enter["realized_R"], errors="coerce").dropna()
    trades = int(len(r))
    wins = r[r > 0]
    losses = r[r < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (math.inf if gross_profit > 0 else 0.0)
    equity = r.cumsum()
    drawdown = equity.cummax() - equity
    return {
        "decisions": int(len(frame)),
        "enter_decisions": int((frame["action"] == "ENTER").sum()),
        "do_nothing_decisions": int((frame["action"] == "DO_NOTHING").sum()),
        "coverage": round_float(float((frame["action"] == "ENTER").mean()) if len(frame) else 0.0, 6),
        "profit_factor": round_float(pf, 6),
        "avg_r": round_float(float(r.mean()) if trades else 0.0, 6),
        "max_drawdown_r": round_float(float(drawdown.max()) if trades else 0.0, 6),
        "total_r": round_float(float(r.sum()) if trades else 0.0, 6),
        "win_rate": round_float(float((r > 0).mean()) if trades else 0.0, 6),
        "gross_profit_r": round_float(gross_profit, 6),
        "gross_loss_r": round_float(gross_loss, 6),
    }


def markdown_summary(summary: dict[str, Any]) -> str:
    counts = summary["counts"]
    metrics = summary["metrics"]
    direction = summary["direction_breakdown_test"]
    warnings = summary["operational_warnings"]

    lines = [
        "# CEO-MAGI v3 Offline Decision Summary",
        "",
        "## Scope",
        "",
        f"- Policy: `{summary['policy']['name']}`",
        f"- Source strategy: `{summary['source']['source_strategy']}`",
        f"- Realized R column for metrics: `{summary['source']['realized_r_column']}`",
        f"- Min operational score: `{summary['policy']['min_operational_score']:.2f}`",
        f"- Gaspar high deterioration threshold: `{summary['policy']['gaspar_high_deterioration']:.2f}`",
        "",
        "## Decision Counts",
        "",
        dict_table("Action", counts["by_action"]),
        "",
        "## Aggression Modes",
        "",
        dict_table("Mode", counts["by_aggression_mode"]),
        "",
        "## Metrics",
        "",
        metrics_table(metrics),
        "",
        "## BUY vs SELL - Test ENTER Decisions",
        "",
        metrics_table(direction),
        "",
        "## Top Reason Codes",
        "",
        dict_table("Reason code", counts["top_reason_codes"]),
        "",
        "## Operational Warnings",
        "",
    ]
    lines.extend([f"- {warning}" for warning in warnings])
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            conclusion_text(metrics["test"], metrics["2026Q2"]),
            "",
            "## Generated Files",
            "",
            f"- `{summary['outputs']['decisions_csv']}`",
            f"- `{summary['outputs']['decisions_jsonl']}`",
            f"- `{summary['outputs']['summary_md']}`",
            f"- `{summary['outputs']['summary_json']}`",
            "",
        ]
    )
    return "\n".join(lines)


def metrics_table(items: dict[str, dict[str, Any]]) -> str:
    rows = [
        "| Segment | Decisions | ENTER | DO_NOTHING | Coverage | PF | Avg R | Max DD | Total R | Win rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, m in items.items():
        rows.append(
            f"| `{name}` | {m['decisions']} | {m['enter_decisions']} | {m['do_nothing_decisions']} | "
            f"{m['coverage']:.2%} | {format_float(m['profit_factor'])} | {m['avg_r']:.4f} | "
            f"{m['max_drawdown_r']:.2f} | {m['total_r']:.2f} | {m['win_rate']:.2%} |"
        )
    return "\n".join(rows)


def dict_table(label: str, values: dict[str, int]) -> str:
    rows = [f"| {label} | Count |", "| --- | ---: |"]
    for key, value in values.items():
        rows.append(f"| `{key}` | {value} |")
    return "\n".join(rows)


def operational_warnings(decisions: pd.DataFrame, metrics: dict[str, Any]) -> list[str]:
    warnings = [
        "Offline mode uses already generated/validated signals; it does not prove live connectivity or broker execution.",
        "Bot A and Bot B were not modified. JSONL is an execution contract candidate only.",
        "Metrics use `adjusted_R` when CEO-MAGI v3 returns ENTER; skipped trades keep hypothetical R only for audit.",
        "Trade plans use the existing RR2 convention with 10-pip SL to derive SL/TP when entry price is available.",
    ]
    if int(decisions["gaspar_downgraded"].sum()) == 0:
        warnings.append("No Gaspar downgrades were observed in this source because `p_deteriorating` never reached 0.70.")
    q2 = metrics["2026Q2"]
    if q2["enter_decisions"] and q2["profit_factor"] <= 1.20:
        warnings.append("2026Q2 remains a weak regime and should stay under special monitoring.")
    enter = decisions[decisions["action"].eq("ENTER")]
    if enter["entry_price"].isna().any():
        warnings.append("Some ENTER decisions are missing entry price; Bot B should reject those records in live mode.")
    return warnings


def conclusion_text(test: dict[str, Any], q2: dict[str, Any]) -> str:
    verdict = "CEO-MAGI v3 offline keeps a positive realistic edge on the test split"
    if test["profit_factor"] <= 1.0 or test["avg_r"] <= 0:
        verdict = "CEO-MAGI v3 offline is not operationally acceptable on the test split"
    elif q2["enter_decisions"] and q2["profit_factor"] <= 1.20:
        verdict += ", but 2026Q2 remains fragile"
    return (
        f"{verdict}: PF `{format_float(test['profit_factor'])}`, Avg R `{test['avg_r']:.4f}`, "
        f"Max DD `{test['max_drawdown_r']:.2f}` and Total R `{test['total_r']:.2f}`."
    )


def stops_from_plan(entry_price: float, direction: str | None) -> tuple[float, float]:
    if not math.isfinite(entry_price) or direction not in {"BUY", "SELL"}:
        return math.nan, math.nan
    pip = 0.0001
    risk = SL_PIPS * pip
    reward = risk * RR_MULTIPLE
    if direction == "BUY":
        return entry_price - risk, entry_price + reward
    return entry_price + risk, entry_price - reward


def direction_from_prediction(prediction: Any) -> str | None:
    value = normalize(prediction, "NO_SIGNAL")
    if value in {"ENTER_BUY", "BUY"}:
        return "BUY"
    if value in {"ENTER_SELL", "SELL"}:
        return "SELL"
    return None


def gaspar_signal_from_probability(p_deteriorating: float) -> str:
    if p_deteriorating >= GASPAR_HIGH_DETERIORATION:
        return "CAUTION"
    return "ALLOW"


def is_2026q2(timestamp: pd.Timestamp) -> bool:
    if pd.isna(timestamp):
        return False
    return bool(
        pd.Timestamp("2026-04-01 00:00:00", tz="UTC")
        <= timestamp
        <= pd.Timestamp("2026-04-14 23:59:59", tz="UTC")
    )


def int_counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).items()}


def normalize(value: Any, default: str) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    text = str(value).strip().upper()
    return text if text else default


def safe_float(value: Any, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def round_float(value: float, digits: int = 6) -> float:
    if not math.isfinite(value):
        return value
    return round(float(value), digits)


def format_float(value: float) -> str:
    if value == math.inf:
        return "inf"
    return f"{value:.4f}"


def timestamp_to_json(value: Any) -> str:
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        return ""
    return timestamp.isoformat().replace("+00:00", "Z")


def json_number(value: Any) -> float | None:
    numeric = safe_float(value, math.nan)
    if not math.isfinite(numeric):
        return None
    return numeric


def split_notes(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.split("|") if part.strip()]


def split_flags(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]


if __name__ == "__main__":
    main()
