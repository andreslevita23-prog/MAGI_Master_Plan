"""Report generation for phase 3."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _fmt(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.4f}"


def choose_recommended_configuration(comparison_df: pd.DataFrame) -> pd.Series:
    """Choose a recommendation with signal and stability, not only best point metric."""
    ranked = comparison_df.copy()
    for column in ["f1_macro", "walk_forward_f1_mean", "walk_forward_f1_std"]:
        min_value = float(ranked[column].min())
        max_value = float(ranked[column].max())
        if max_value - min_value < 1e-9:
            ranked[f"{column}_norm"] = 1.0
        else:
            ranked[f"{column}_norm"] = (ranked[column] - min_value) / (max_value - min_value)

    ranked["stability_inverse_norm"] = 1 - ranked["walk_forward_f1_std_norm"]
    ranked["recommendation_score"] = (
        0.40 * ranked["walk_forward_f1_mean_norm"]
        + 0.30 * ranked["stability_inverse_norm"]
        + 0.20 * ranked["f1_macro_norm"]
        + 0.10 * (ranked["feature_variant"] == "compact").astype(float)
    )
    return ranked.sort_values("recommendation_score", ascending=False).iloc[0]


def build_phase3_report(
    run_id: str,
    target_grid_df: pd.DataFrame,
    candidate_targets_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    recommended_row: pd.Series,
) -> str:
    """Build a phase 3 markdown report."""
    top_candidates_text = candidate_targets_df[
        [
            "target_name",
            "horizon_steps",
            "threshold",
            "imbalance_ratio",
            "f1_macro",
            "walk_forward_f1_mean",
            "walk_forward_f1_std",
            "candidate_score",
        ]
    ].to_string(index=False)

    comparison_text = comparison_df[
        [
            "scenario_name",
            "target_name",
            "feature_variant",
            "model_name",
            "feature_count",
            "accuracy",
            "f1_macro",
            "walk_forward_f1_mean",
            "walk_forward_f1_std",
        ]
    ].to_string(index=False)

    recommended_name = recommended_row["scenario_name"]
    return f"""# Baltasar v1.1 Recommendation Report

## Executive Summary

- Reference run: `{run_id}`
- Recommended base for Baltasar v1.1: `{recommended_name}`
- Target candidate: `{recommended_row['target_name']}`
- Feature variant: `{recommended_row['feature_variant']}`
- Model with best trade-off in comparison: `{recommended_row['model_name']}`
- Holdout F1 macro: {_fmt(recommended_row['f1_macro'])}
- Walk-forward F1 mean: {_fmt(recommended_row['walk_forward_f1_mean'])}
- Walk-forward F1 std: {_fmt(recommended_row['walk_forward_f1_std'])}

## Why This Recommendation

La nueva base se recomienda por equilibrio entre tres cosas:

1. mejor senal del target que la configuracion original
2. menor dependencia de una sola corrida holdout
3. mayor trazabilidad de features si la variante compacta mantiene o mejora la estabilidad

## Systematic Target Exploration

Se evaluaron {len(target_grid_df)} configuraciones de target sobre el arbol baseline como sonda controlada.

Top target candidates:

{top_candidates_text}

Lectura:
- no se eligio solo el mayor `f1_macro`
- se priorizo tambien desbalance mas razonable y menor dispersion en walk-forward

## Experimental Comparison

Se compararon los escenarios obligatorios:

{comparison_text}

Trade-offs observados:
- `current_target_current_features` sirve como linea base historica
- `candidate_target_current_features` aísla el efecto del rediseño del target
- `candidate_target_compact_features` muestra si podemos ganar claridad y estabilidad con menos redundancia

## Recommended New Base for Baltasar v1.1

- Scenario: `{recommended_row['scenario_name']}`
- Target: `{recommended_row['target_name']}`
- Feature variant: `{recommended_row['feature_variant']}`
- Suggested model family for base tracking: `{recommended_row['model_name']}`

## Practical Interpretation

- Si la variante compacta queda cerca o por encima del set actual, conviene adoptarla porque reduce ruido estructural y hace mas interpretable el laboratorio.
- Si el target candidato mejora `walk_forward_f1_mean` con menor dispersion, vale mas como nueva base que una mejora puntual de holdout.
- Si `random_forest` supera al arbol pero con estabilidad similar, puede quedar como comparador secundario y no necesariamente como unica base operativa.

## Next Steps

1. Promover el escenario recomendado como nueva configuracion base `Baltasar v1.1`.
2. Reentrenar y redocumentar notebooks usando ese target y ese set de features.
3. Mantener walk-forward como criterio principal antes de cualquier tuning.
4. Solo despues de consolidar esta base, evaluar calibracion, costos de clase o reglas de evento mas cercanas a trading real.
"""


def write_phase3_report(markdown: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
