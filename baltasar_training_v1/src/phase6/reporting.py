"""Reporting helpers for Baltasar v1.2 training."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _fmt(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.4f}"


def build_v12_report(
    dataset_summary: dict,
    quick_checks: dict,
    validation_report: dict,
    metrics_df: pd.DataFrame,
    class_tables: dict[str, pd.DataFrame],
    comparison_df: pd.DataFrame,
) -> str:
    """Build the Baltasar v1.2 markdown report."""
    metrics_text = metrics_df.to_string(index=False)
    comparison_text = comparison_df.to_string(index=False)
    class_sections = []
    for model_name, class_df in class_tables.items():
        class_sections.append(f"### {model_name}\n\n{class_df.to_string(index=False)}")
    class_text = "\n\n".join(class_sections)

    return f"""# Baltasar v1.2 Training Report

## Dataset Located

- Source run: `{dataset_summary['run_name']}`
- Source path: `{dataset_summary['path']}`
- Source type: `{dataset_summary['source_type']}`
- CSV files: `{dataset_summary['csv_files']}`
- Rows before target drop: `{dataset_summary['rows']}`
- Columns: `{dataset_summary['columns']}`
- Timestamp min: `{dataset_summary['timestamp_min']}`
- Timestamp max: `{dataset_summary['timestamp_max']}`
- Approx months: `{dataset_summary['approx_months']:.2f}`

## Quick Validation

- Duplicate rows: `{quick_checks['duplicate_rows']}`
- Duplicate snapshot ids: `{quick_checks['duplicate_snapshot_ids']}`
- Null timestamp rows: `{quick_checks['null_timestamp_rows']}`
- Median gap minutes: `{_fmt(quick_checks['median_gap_minutes'])}`
- P95 gap minutes: `{_fmt(quick_checks['p95_gap_minutes'])}`
- Gaps over 8h: `{quick_checks['gaps_over_8h']}`
- Largest gap hours: `{_fmt(quick_checks['largest_gap_hours'])}`
- Missing required columns: `{quick_checks['schema_check']['missing_required_columns']}`
- Validation passed: `{validation_report['passed']}`

## Baltasar v1.2 Metrics

{metrics_text}

## Metrics by Class

{class_text}

## v1.1 vs v1.2

{comparison_text}

## Conclusion

- Esta comparacion indica si Baltasar mejora al escalar a 24 meses sin tocar tuning ni arquitectura.
- El criterio principal sigue siendo consistencia temporal y comportamiento por clase, no solo el mejor punto de F1.
"""


def write_report(markdown: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
