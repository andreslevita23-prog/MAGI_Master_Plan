from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


INPUT_JSONL = Path("artifacts/ceo_magi_v3/ceo_magi_v3_decisions.jsonl")
OUTPUT_DIR = Path("artifacts/ceo_magi_v3")
RESULTS_CSV = OUTPUT_DIR / "bot_b_dry_run_results.csv"
SUMMARY_MD = OUTPUT_DIR / "bot_b_dry_run_summary.md"
ERRORS_JSONL = OUTPUT_DIR / "bot_b_dry_run_errors.jsonl"

VALID_ACTIONS = {"ENTER", "DO_NOTHING"}
VALID_DIRECTIONS = {"BUY", "SELL"}
VALID_EXECUTION_MODES = {"none", "cautious", "normal", "premium"}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if not INPUT_JSONL.exists():
        raise FileNotFoundError(f"Missing CEO-MAGI v3 decisions JSONL: {INPUT_JSONL}")

    with INPUT_JSONL.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue

            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                result = reject_result(line_number, {}, ["invalid_json"], [str(exc)])
                results.append(result)
                errors.append(error_record(line_number, {}, ["invalid_json"], [str(exc)]))
                continue

            validation = validate_payload(payload)
            if validation["errors"]:
                ack_status = "REJECT_INVALID_PAYLOAD"
                bot_b_action = "reject"
                errors.append(error_record(line_number, payload, validation["errors"], validation["warnings"]))
            elif payload["action"] == "ENTER":
                ack_status = "ACK_EXECUTABLE"
                bot_b_action = "dry_run_open_trade"
            else:
                ack_status = "ACK_DO_NOTHING"
                bot_b_action = "dry_run_noop"

            results.append(
                {
                    "line_number": line_number,
                    "decision_id": payload.get("decision_id") or payload.get("snapshot_id") or "",
                    "snapshot_id": payload.get("snapshot_id", ""),
                    "symbol": payload.get("symbol", ""),
                    "action": payload.get("action", ""),
                    "execution_mode": execution_mode(payload),
                    "direction": payload.get("direction"),
                    "entry_price": payload.get("entry_price"),
                    "stop_loss": payload.get("stop_loss"),
                    "take_profit": payload.get("take_profit"),
                    "reason_code": payload.get("reason_code") or payload.get("reason_codes") or "",
                    "ack_status": ack_status,
                    "bot_b_action": bot_b_action,
                    "error_count": len(validation["errors"]),
                    "warning_count": len(validation["warnings"]),
                    "error_types": "|".join(validation["errors"]),
                    "warnings": "|".join(validation["warnings"]),
                    "orders_sent": 0,
                    "dry_run": True,
                }
            )

    pd.DataFrame(results).to_csv(RESULTS_CSV, index=False)
    write_errors(errors)
    SUMMARY_MD.write_text(markdown_summary(results, errors), encoding="utf-8")

    counts = Counter(item["ack_status"] for item in results)
    print(f"total_decisions_read={len(results)}")
    print(f"ack_executable={counts.get('ACK_EXECUTABLE', 0)}")
    print(f"ack_do_nothing={counts.get('ACK_DO_NOTHING', 0)}")
    print(f"reject_invalid_payload={counts.get('REJECT_INVALID_PAYLOAD', 0)}")
    print(f"output_results={RESULTS_CSV}")
    print(f"output_summary={SUMMARY_MD}")
    print(f"output_errors={ERRORS_JSONL}")


def validate_payload(payload: dict[str, Any]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    action = payload.get("action")
    symbol = payload.get("symbol")
    decision_ref = payload.get("decision_id") or payload.get("snapshot_id")
    mode = execution_mode(payload)
    reason = payload.get("reason_code") or payload.get("reason_codes")

    require(action in VALID_ACTIONS, "invalid_or_missing_action", errors)
    require(is_non_empty_string(symbol), "missing_symbol", errors)
    require(is_non_empty_string(decision_ref), "missing_decision_id_or_snapshot_id", errors)
    require(is_non_empty_string(reason), "missing_reason_code", errors)
    require(is_non_empty_string(mode), "missing_aggression_or_execution_mode", errors)

    if is_non_empty_string(mode) and mode not in VALID_EXECUTION_MODES:
        errors.append("invalid_aggression_or_execution_mode")

    if "aggression_mode" not in payload and "execution_mode" in payload:
        warnings.append("payload_uses_execution_mode_alias_for_aggression_mode")

    if action == "ENTER":
        direction = payload.get("direction")
        require(direction in VALID_DIRECTIONS, "missing_or_invalid_direction_for_enter", errors)
        require(is_valid_number(payload.get("entry_price")), "missing_or_invalid_entry_price_for_enter", errors)

        stop_loss_exists = "stop_loss" in payload or "sl" in payload
        take_profit_exists = "take_profit" in payload or "tp" in payload
        require(stop_loss_exists, "missing_stop_loss_field_for_enter", errors)
        require(take_profit_exists, "missing_take_profit_field_for_enter", errors)

        stop_loss = payload.get("stop_loss", payload.get("sl"))
        take_profit = payload.get("take_profit", payload.get("tp"))
        require(is_valid_number(stop_loss), "missing_or_invalid_stop_loss_for_enter", errors)
        require(is_valid_number(take_profit), "missing_or_invalid_take_profit_for_enter", errors)
        if is_valid_number(payload.get("entry_price")) and is_valid_number(stop_loss) and is_valid_number(take_profit):
            validate_price_geometry(direction, float(payload["entry_price"]), float(stop_loss), float(take_profit), errors)

        if mode == "none":
            errors.append("enter_cannot_use_none_execution_mode")

    if action == "DO_NOTHING":
        if mode != "none":
            errors.append("do_nothing_must_use_none_execution_mode")
        for field in ["direction", "entry_price", "stop_loss", "take_profit"]:
            value = payload.get(field)
            if value not in (None, "", []):
                warnings.append(f"do_nothing_has_non_null_{field}")

    return {"errors": errors, "warnings": warnings}


def validate_price_geometry(direction: Any, entry: float, stop_loss: float, take_profit: float, errors: list[str]) -> None:
    if direction == "BUY":
        if not stop_loss < entry < take_profit:
            errors.append("invalid_buy_price_geometry")
    elif direction == "SELL":
        if not take_profit < entry < stop_loss:
            errors.append("invalid_sell_price_geometry")


def execution_mode(payload: dict[str, Any]) -> str:
    value = payload.get("aggression_mode", payload.get("execution_mode", ""))
    return str(value).strip() if value is not None else ""


def require(condition: bool, error_type: str, errors: list[str]) -> None:
    if not condition:
        errors.append(error_type)


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_valid_number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def reject_result(line_number: int, payload: dict[str, Any], errors: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "line_number": line_number,
        "decision_id": payload.get("decision_id", ""),
        "snapshot_id": payload.get("snapshot_id", ""),
        "symbol": payload.get("symbol", ""),
        "action": payload.get("action", ""),
        "execution_mode": execution_mode(payload),
        "direction": payload.get("direction"),
        "entry_price": payload.get("entry_price"),
        "stop_loss": payload.get("stop_loss"),
        "take_profit": payload.get("take_profit"),
        "reason_code": payload.get("reason_code", ""),
        "ack_status": "REJECT_INVALID_PAYLOAD",
        "bot_b_action": "reject",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "error_types": "|".join(errors),
        "warnings": "|".join(warnings),
        "orders_sent": 0,
        "dry_run": True,
    }


def error_record(line_number: int, payload: dict[str, Any], errors: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "line_number": line_number,
        "decision_id": payload.get("decision_id") or payload.get("snapshot_id") or "",
        "errors": errors,
        "warnings": warnings,
        "payload_excerpt": payload_excerpt(payload),
    }


def payload_excerpt(payload: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "schema_version",
        "decision_id",
        "snapshot_id",
        "symbol",
        "action",
        "execution_mode",
        "aggression_mode",
        "direction",
        "entry_price",
        "stop_loss",
        "take_profit",
        "reason_code",
    ]
    return {key: payload.get(key) for key in keys if key in payload}


def write_errors(errors: list[dict[str, Any]]) -> None:
    with ERRORS_JSONL.open("w", encoding="utf-8") as handle:
        for item in errors:
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")


def markdown_summary(results: list[dict[str, Any]], errors: list[dict[str, Any]]) -> str:
    frame = pd.DataFrame(results)
    total = int(len(frame))
    counts = Counter(frame["ack_status"]) if total else Counter()
    enter_valid = int(((frame["ack_status"] == "ACK_EXECUTABLE") & (frame["action"] == "ENTER")).sum()) if total else 0
    do_nothing_valid = int(((frame["ack_status"] == "ACK_DO_NOTHING") & (frame["action"] == "DO_NOTHING")).sum()) if total else 0
    rejects = int((frame["ack_status"] == "REJECT_INVALID_PAYLOAD").sum()) if total else 0
    warning_count = int(frame["warning_count"].sum()) if total else 0
    error_counts = error_type_counts(errors)

    lines = [
        "# Bot B Dry-Run Summary for CEO-MAGI v3",
        "",
        "## Scope",
        "",
        f"- Input: `{INPUT_JSONL}`",
        "- Mode: dry-run only",
        "- Orders sent: `0`",
        "- MT5 touched: `no`",
        "- Bot B real modified: `no`",
        "",
        "## Results",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Total decisions read | {total} |",
        f"| ENTER valid | {enter_valid} |",
        f"| DO_NOTHING valid | {do_nothing_valid} |",
        f"| Rejections | {rejects} |",
        f"| Payload warnings | {warning_count} |",
        "",
        "## ACK Status",
        "",
        dict_table("ACK status", {str(k): int(v) for k, v in counts.items()}),
        "",
        "## Errors by Type",
        "",
        dict_table("Error type", error_counts) if error_counts else "No schema errors found.",
        "",
        "## Rejected Payload Examples",
        "",
        rejected_examples(errors),
        "",
        "## Operational Notes",
        "",
        "- `ACK_EXECUTABLE` means the payload is structurally executable by Bot B, not that a broker order was sent.",
        "- `ACK_DO_NOTHING` means Bot B can safely ignore the decision.",
        "- `REJECT_INVALID_PAYLOAD` means Bot B should refuse the decision before any execution adapter sees it.",
        "- The current CEO contract includes both `aggression_mode` and `execution_mode` for compatibility.",
        "",
        "## Recommendation for Runtime Integration",
        "",
        runtime_recommendation(rejects, warning_count),
        "",
        "## Generated Files",
        "",
        f"- `{RESULTS_CSV}`",
        f"- `{SUMMARY_MD}`",
        f"- `{ERRORS_JSONL}`",
        "",
    ]
    return "\n".join(lines)


def error_type_counts(errors: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in errors:
        counter.update(item["errors"])
    return {key: int(value) for key, value in counter.most_common()}


def dict_table(label: str, values: dict[str, int]) -> str:
    rows = [f"| {label} | Count |", "| --- | ---: |"]
    for key, value in values.items():
        rows.append(f"| `{key}` | {value} |")
    return "\n".join(rows)


def rejected_examples(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "No rejected payloads."
    rows = ["```json"]
    for item in errors[:5]:
        rows.append(json.dumps(item, ensure_ascii=False, indent=2))
    rows.append("```")
    return "\n".join(rows)


def runtime_recommendation(rejects: int, warnings: int) -> str:
    if rejects:
        return (
            "Do not connect this stream to a live execution adapter yet. Fix rejected payloads first, then rerun dry-run."
        )
    if warnings:
        return (
            "Payloads are executable, but standardize the field name before runtime: either keep `execution_mode` as the Bot B contract "
            "or add `aggression_mode` as an explicit alias."
        )
    return (
        "Payloads are structurally ready for a runtime shadow mode. Next step: route JSONL decisions through a Bot B adapter stub "
        "that emits acknowledgements to Bot C without broker connectivity."
    )


if __name__ == "__main__":
    main()
