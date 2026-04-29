from __future__ import annotations

import json
import csv
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from simulator.schemas import DataQualityReport, SimulationConfig


def create_run_dir(output_root: str | Path, run_name: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in run_name)
    run_dir = Path(output_root) / f"{timestamp}_{safe_name}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: str | Path, data: Any) -> None:
    Path(path).write_text(json.dumps(to_jsonable(data), indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: str | Path, rows: list[Any]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(to_jsonable(row), sort_keys=True))
            handle.write("\n")


def write_csv(path: str | Path, rows: list[Any], fieldnames: list[str] | None = None) -> None:
    jsonable_rows = [to_jsonable(row) for row in rows]
    if fieldnames is None:
        keys: list[str] = []
        for row in jsonable_rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in jsonable_rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_text(path: str | Path, content: str) -> None:
    Path(path).write_text(content, encoding="utf-8")


def write_config(path: str | Path, config: SimulationConfig) -> None:
    write_json(path, config)


def write_manifest(path: str | Path, config: SimulationConfig, quality: DataQualityReport, counts: dict[str, int]) -> None:
    manifest = {
        "schema_version": "simulator_run_manifest_v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config": config,
        "quality_summary": {
            "total_snapshots": quality.total_snapshots,
            "valid_snapshots": quality.valid_snapshots,
            "invalid_snapshots": quality.invalid_snapshots,
            "duplicate_snapshot_ids": quality.duplicate_snapshot_ids,
            "parse_errors": len(quality.parse_errors),
        },
        "outputs": counts,
    }
    write_json(path, manifest)


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value
