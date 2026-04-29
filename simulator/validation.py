from __future__ import annotations

from collections import Counter
from typing import Any

from simulator.schemas import DataQualityReport, Snapshot, ValidationIssue, timestamp_to_iso


REQUIRED_FIELDS = (
    "snapshot_id",
    "symbol",
    "timestamp",
    "anchor_bar_timestamp",
    "current_price",
    "spread_pips",
)


def validate_snapshot(snapshot: Snapshot) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    sid = snapshot.snapshot_id or "<missing>"

    for field_name in REQUIRED_FIELDS:
        if getattr(snapshot, field_name) in (None, ""):
            issues.append(ValidationIssue(sid, "error", f"missing_{field_name}", f"Missing {field_name}"))

    ohlc = [snapshot.open, snapshot.high, snapshot.low, snapshot.close]
    if all(value is not None for value in ohlc):
        if snapshot.high < max(snapshot.open, snapshot.close, snapshot.low) or snapshot.low > min(snapshot.open, snapshot.close, snapshot.high):
            issues.append(ValidationIssue(sid, "error", "invalid_ohlc", "OHLC values are internally inconsistent"))

    if snapshot.spread_pips is not None and snapshot.spread_pips < 0:
        issues.append(ValidationIssue(sid, "error", "negative_spread", "spread_pips cannot be negative"))

    if snapshot.validation and snapshot.validation.get("is_valid") is False:
        issues.append(ValidationIssue(sid, "warning", "source_marked_invalid", "Bot A marked this snapshot as invalid"))

    if not snapshot.features:
        issues.append(ValidationIssue(sid, "warning", "missing_features", "Snapshot has no features payload"))

    if not snapshot.gaspar_context:
        issues.append(ValidationIssue(sid, "warning", "missing_gaspar_context", "Snapshot has no gaspar_context payload"))

    return issues


def build_quality_report(snapshots: list[Snapshot], parse_errors: list[dict[str, Any]]) -> DataQualityReport:
    issue_records: list[dict[str, Any]] = []
    issue_counter: Counter[str] = Counter()
    duplicate_ids = _duplicate_count([snapshot.snapshot_id for snapshot in snapshots if snapshot.snapshot_id])
    seen_ids: set[str] = set()

    for snapshot in snapshots:
        for issue in validate_snapshot(snapshot):
            issue_counter[issue.code] += 1
            issue_records.append(
                {
                    "snapshot_id": issue.snapshot_id,
                    "severity": issue.severity,
                    "code": issue.code,
                    "message": issue.message,
                    "source_file": snapshot.source_file,
                    "source_line": snapshot.source_line,
                }
            )
        if snapshot.snapshot_id in seen_ids:
            issue_counter["duplicate_snapshot_id"] += 1
            issue_records.append(
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "severity": "error",
                    "code": "duplicate_snapshot_id",
                    "message": "snapshot_id appears more than once",
                    "source_file": snapshot.source_file,
                    "source_line": snapshot.source_line,
                }
            )
        seen_ids.add(snapshot.snapshot_id)

    invalid_ids = {issue["snapshot_id"] for issue in issue_records if issue["severity"] == "error"}
    timestamps = sorted(snapshot.anchor_bar_timestamp for snapshot in snapshots)
    symbols = Counter(snapshot.symbol for snapshot in snapshots if snapshot.symbol)
    source_files = sorted({snapshot.source_file for snapshot in snapshots if snapshot.source_file})

    return DataQualityReport(
        total_snapshots=len(snapshots),
        valid_snapshots=len(snapshots) - len(invalid_ids),
        invalid_snapshots=len(invalid_ids),
        duplicate_snapshot_ids=duplicate_ids,
        parse_errors=parse_errors,
        issues_by_code=dict(sorted(issue_counter.items())),
        symbols=dict(sorted(symbols.items())),
        first_timestamp=timestamp_to_iso(timestamps[0]) if timestamps else None,
        last_timestamp=timestamp_to_iso(timestamps[-1]) if timestamps else None,
        source_files=source_files,
        issues=issue_records,
    )


def _duplicate_count(values: list[str]) -> int:
    counts = Counter(values)
    return sum(count - 1 for count in counts.values() if count > 1)
