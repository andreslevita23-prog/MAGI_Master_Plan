from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .data import load_dataset
from .features import FEATURE_COLUMNS
from .targeting import attach_heuristic_target


def run_diagnostics(data_path: str | Path, output_root: str | Path = ".", target_version: str = "v1") -> dict:
    root = Path(output_root)
    metrics_dir = root / "artifacts" / "metrics"
    reports_dir = root / "reports"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    data = attach_heuristic_target(load_dataset(data_path), target_version=target_version, overwrite=True)
    missing = data.reindex(columns=FEATURE_COLUMNS).isna().mean().sort_values(ascending=False)
    class_distribution = data["voto"].value_counts(dropna=False).to_dict()
    summary = {
        "rows": int(len(data)),
        "columns": list(data.columns),
        "missing_ratio": {key: float(value) for key, value in missing.items()},
        "class_distribution": {str(key): int(value) for key, value in class_distribution.items()},
        "timestamp_min": _safe_timestamp(data, "min"),
        "timestamp_max": _safe_timestamp(data, "max"),
        "target_version": target_version,
    }
    artifact_stem = "gaspar" if target_version == "v1" else f"gaspar_{target_version}"
    (metrics_dir / f"{artifact_stem}_diagnostics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_diagnostics_report(reports_dir / f"{artifact_stem}_diagnostics_report.md", summary)
    return summary


def _safe_timestamp(data: pd.DataFrame, op: str) -> str | None:
    if "timestamp" not in data.columns:
        return None
    values = pd.to_datetime(data["timestamp"], errors="coerce").dropna()
    if values.empty:
        return None
    return getattr(values, op)().isoformat()


def write_diagnostics_report(path: Path, summary: dict) -> None:
    missing_rows = "\n".join(
        f"- `{column}`: {ratio:.2%}"
        for column, ratio in summary["missing_ratio"].items()
    )
    class_rows = "\n".join(
        f"- `{label}`: {count}"
        for label, count in summary["class_distribution"].items()
    )
    body = f"""# Gaspar Diagnostics Report

## Cobertura

- filas: {summary["rows"]}
- timestamp inicial: {summary["timestamp_min"]}
- timestamp final: {summary["timestamp_max"]}

## Distribucion de clases

{class_rows}

## Datos faltantes por feature

{missing_rows}
"""
    path.write_text(body, encoding="utf-8")
