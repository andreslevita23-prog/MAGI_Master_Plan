from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


FORBIDDEN_KEYWORDS = (
    "future",
    "outcome",
    "pnl",
    "mfe",
    "mae",
    "target",
    "label",
    "forward_return",
    "hit_tp",
    "hit_sl",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare clean Bot A sub3 JSONL dataset for MAGI simulation.")
    parser.add_argument(
        "--source-run",
        required=True,
        help="Exact Bot A sub3 run folder to clean.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/clean/bot_a_sub3_full",
        help="Output directory for cleaned dataset.",
    )
    args = parser.parse_args()

    source_run = Path(args.source_run)
    output_dir = Path(args.output_dir)
    summary = prepare_clean_dataset(source_run, output_dir)
    print(json.dumps({
        "output_dir": str(output_dir),
        "records_final": summary["records_final"],
        "high_spread_count": summary["high_spread_count"],
        "duplicates_removed": summary["duplicates_removed"],
    }, indent=2, sort_keys=True))
    return 0


def prepare_clean_dataset(source_run: Path, output_dir: Path) -> dict[str, Any]:
    if not source_run.exists():
        raise FileNotFoundError(f"Source run does not exist: {source_run}")
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_path = output_dir / "_cleaned_dataset.tmp.jsonl"
    final_path = output_dir / "cleaned_dataset.jsonl"
    summary_json_path = output_dir / "cleaned_dataset_summary.json"
    summary_md_path = output_dir / "cleaned_dataset_summary.md"

    jsonl_files = sorted(source_run.rglob("*.jsonl"))
    seen_snapshot_ids: set[str] = set()
    seen_symbol_anchor: set[tuple[str, str]] = set()
    entries: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    duplicate_snapshot_id = 0
    duplicate_symbol_anchor = 0
    forbidden_removed = Counter()
    symbols = Counter()
    timeframes = Counter()
    high_spread_count = 0
    first_anchor: datetime | None = None
    last_anchor: datetime | None = None
    raw_records = 0

    with temp_path.open("w", encoding="utf-8", newline="\n") as temp:
        for path in jsonl_files:
            with path.open("r", encoding="utf-8-sig") as handle:
                for line_number, line in enumerate(handle, 1):
                    text = line.strip()
                    if not text:
                        continue
                    raw_records += 1
                    try:
                        record = json.loads(text)
                    except Exception as exc:  # noqa: BLE001
                        parse_errors.append({"file": str(path), "line": line_number, "error": str(exc)})
                        continue

                    snapshot_id = str(record.get("snapshot_id") or "")
                    symbol = str(record.get("symbol") or "")
                    anchor = parse_timestamp(record.get("anchor_bar_timestamp") or record.get("bar_timestamp"))
                    timestamp = parse_timestamp(record.get("timestamp"))
                    if not snapshot_id or not symbol or anchor is None or timestamp is None:
                        parse_errors.append({"file": str(path), "line": line_number, "error": "missing id, symbol, timestamp, or anchor"})
                        continue
                    anchor_iso = iso(anchor)
                    if snapshot_id in seen_snapshot_ids:
                        duplicate_snapshot_id += 1
                        continue
                    seen_snapshot_ids.add(snapshot_id)
                    symbol_anchor = (symbol, anchor_iso)
                    if symbol_anchor in seen_symbol_anchor:
                        duplicate_symbol_anchor += 1
                        continue
                    seen_symbol_anchor.add(symbol_anchor)

                    cleaned, removed_paths = sanitize_record(record)
                    for removed in removed_paths:
                        forbidden_removed[removed] += 1
                    cleaned["timestamp"] = iso(timestamp)
                    cleaned["anchor_bar_timestamp"] = anchor_iso
                    if parse_timestamp(cleaned.get("bar_timestamp")) is not None:
                        cleaned["bar_timestamp"] = iso(parse_timestamp(cleaned.get("bar_timestamp")))
                    spread = as_float(cleaned.get("spread_pips"))
                    is_high_spread = spread is not None and spread > 5.0
                    cleaned["is_high_spread"] = is_high_spread
                    if is_high_spread:
                        high_spread_count += 1
                    cleaned["has_gap_forward"] = False

                    offset = temp.tell()
                    temp.write(json.dumps(cleaned, sort_keys=True, separators=(",", ":")))
                    temp.write("\n")
                    symbols[symbol] += 1
                    timeframes[str(cleaned.get("anchor_timeframe") or cleaned.get("timeframe") or "")] += 1
                    first_anchor = min_datetime(first_anchor, anchor)
                    last_anchor = max_datetime(last_anchor, anchor)
                    entries.append(
                        {
                            "symbol": symbol,
                            "anchor": anchor,
                            "anchor_iso": anchor_iso,
                            "snapshot_id": snapshot_id,
                            "offset": offset,
                            "is_high_spread": is_high_spread,
                        }
                    )

    entries.sort(key=lambda item: (item["symbol"], item["anchor"], item["snapshot_id"]))
    gap_flags = compute_gap_flags(entries)
    out_of_order_count = 0
    previous_key: tuple[str, datetime, str] | None = None
    with temp_path.open("r", encoding="utf-8") as temp, final_path.open("w", encoding="utf-8", newline="\n") as final:
        for entry in entries:
            key = (entry["symbol"], entry["anchor"], entry["snapshot_id"])
            if previous_key is not None and key < previous_key:
                out_of_order_count += 1
            previous_key = key
            temp.seek(entry["offset"])
            record = json.loads(temp.readline())
            record["has_gap_forward"] = gap_flags.get(entry["snapshot_id"], False)
            final.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            final.write("\n")

    gap_forward_count = sum(1 for value in gap_flags.values() if value)
    summary = {
        "schema_version": "bot_a_sub3_clean_dataset_summary_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_run": str(source_run),
        "output_dir": str(output_dir),
        "cleaned_dataset_path": str(final_path),
        "source_jsonl_files": len(jsonl_files),
        "source_jsonl_size_mb": round(sum(path.stat().st_size for path in jsonl_files) / (1024 * 1024), 2),
        "raw_records_read": raw_records,
        "records_final": len(entries),
        "parse_errors_count": len(parse_errors),
        "parse_errors_sample": parse_errors[:20],
        "duplicates_removed": {
            "snapshot_id": duplicate_snapshot_id,
            "symbol_anchor_timestamp": duplicate_symbol_anchor,
            "total": duplicate_snapshot_id + duplicate_symbol_anchor,
        },
        "symbols": dict(sorted(symbols.items())),
        "timeframes": dict(sorted(timeframes.items())),
        "first_anchor_bar_timestamp": iso(first_anchor),
        "last_anchor_bar_timestamp": iso(last_anchor),
        "high_spread_count": high_spread_count,
        "high_spread_pct": pct(high_spread_count, len(entries)),
        "gap_forward_count": gap_forward_count,
        "gap_forward_pct": pct(gap_forward_count, len(entries)),
        "forbidden_removed_total": sum(forbidden_removed.values()),
        "forbidden_removed_top": dict(forbidden_removed.most_common(30)),
        "temporal_consistency": {
            "sorted_output_out_of_order_count": out_of_order_count,
            "duplicate_snapshot_ids_after_cleaning": 0,
            "duplicate_symbol_anchor_after_cleaning": 0,
        },
    }
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary_md_path.write_text(summary_markdown(summary), encoding="utf-8")
    temp_path.unlink(missing_ok=True)
    return summary


def sanitize_record(record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    removed: list[str] = []

    def clean(value: Any, prefix: str = "") -> Any:
        if isinstance(value, dict):
            output = {}
            for key, nested in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if forbidden_key(str(key)):
                    removed.append(path)
                    continue
                output[str(key)] = clean(nested, path)
            return output
        if isinstance(value, list):
            return [clean(item, f"{prefix}[]") for item in value]
        return value

    return clean(record), removed


def forbidden_key(key: str) -> bool:
    lower = key.lower()
    return any(keyword in lower for keyword in FORBIDDEN_KEYWORDS)


def compute_gap_flags(entries: list[dict[str, Any]]) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for index, entry in enumerate(entries):
        if index + 1 >= len(entries) or entries[index + 1]["symbol"] != entry["symbol"]:
            flags[entry["snapshot_id"]] = False
            continue
        next_anchor = entries[index + 1]["anchor"]
        delta = next_anchor - entry["anchor"]
        flags[entry["snapshot_id"]] = delta > timedelta(minutes=5, seconds=1)
    return flags


def parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def min_datetime(left: datetime | None, right: datetime) -> datetime:
    return right if left is None or right < left else left


def max_datetime(left: datetime | None, right: datetime) -> datetime:
    return right if left is None or right > left else left


def pct(count: int, total: int) -> float:
    return round((count / total) * 100, 4) if total else 0.0


def summary_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Bot A sub3 Clean Dataset Summary",
            "",
            f"- Source run: `{summary['source_run']}`",
            f"- Output: `{summary['cleaned_dataset_path']}`",
            f"- Raw records read: `{summary['raw_records_read']}`",
            f"- Final records: `{summary['records_final']}`",
            f"- Parse errors: `{summary['parse_errors_count']}`",
            f"- Duplicates removed: `{summary['duplicates_removed']}`",
            f"- Symbols: `{summary['symbols']}`",
            f"- Timeframes: `{summary['timeframes']}`",
            f"- Range: `{summary['first_anchor_bar_timestamp']}` to `{summary['last_anchor_bar_timestamp']}`",
            f"- High spread count: `{summary['high_spread_count']}` (`{summary['high_spread_pct']}%`)",
            f"- Has gap forward count: `{summary['gap_forward_count']}` (`{summary['gap_forward_pct']}%`)",
            f"- Forbidden fields removed: `{summary['forbidden_removed_total']}`",
            f"- Forbidden fields top: `{summary['forbidden_removed_top']}`",
            f"- Temporal consistency: `{summary['temporal_consistency']}`",
        ]
    ) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
