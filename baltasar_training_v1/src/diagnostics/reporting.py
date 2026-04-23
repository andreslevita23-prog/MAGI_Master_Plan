"""Report generation for diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _format_float(value: float) -> str:
    return f"{value:.4f}"


def _dominant_target_hypothesis(target_audit_df: pd.DataFrame) -> str:
    current = target_audit_df[target_audit_df["name"] == "current_h12_t08"]
    if current.empty:
        current = target_audit_df.head(1)
    neutral_share = float(current.iloc[0]["neutral_share"])
    imbalance_ratio = float(current.iloc[0]["imbalance_ratio"])
    return (
        f"El target actual concentra {neutral_share:.1%} en `NEUTRAL` con una razon max/min de "
        f"{imbalance_ratio:.2f}. Esto sugiere una tarea ruidosa y parcialmente desbalanceada donde "
        "las clases direccionales tienen menos soporte y mayor ambiguedad."
    )


def _confusion_hypothesis(class_diag_df: pd.DataFrame) -> str:
    neutral_row = class_diag_df[class_diag_df["label"] == "NEUTRAL"]
    buy_row = class_diag_df[class_diag_df["label"] == "BUY"]
    sell_row = class_diag_df[class_diag_df["label"] == "SELL"]
    if neutral_row.empty or buy_row.empty or sell_row.empty:
        return "No se pudo inferir el patron de confusion por clase."
    return (
        "La matriz de confusion muestra que el modelo no aprende bien la frontera entre direccion y no-direccion: "
        f"`NEUTRAL` tiene recall {_format_float(float(neutral_row.iloc[0]['recall']))}, mientras `BUY` y `SELL` "
        f"quedan en {_format_float(float(buy_row.iloc[0]['recall']))} y {_format_float(float(sell_row.iloc[0]['recall']))}. "
        "La mayor parte del error ocurre confundiendo las clases direccionales con `NEUTRAL`."
    )


def _temporal_hypothesis(walk_forward_df: pd.DataFrame) -> str:
    valid = walk_forward_df.dropna(subset=["f1_macro"])
    if valid.empty:
        return "No hubo folds validos suficientes para evaluar estabilidad temporal."
    spread = float(valid["f1_macro"].max() - valid["f1_macro"].min())
    return (
        f"El spread temporal de `f1_macro` entre folds fue de {spread:.4f}. "
        "Si este rango es amplio, el problema no es solo de capacidad del modelo sino de estabilidad del regimen de mercado."
    )


def build_markdown_report(
    run_id: str,
    summary: dict[str, Any],
    target_audit_df: pd.DataFrame,
    best_class_diag_df: pd.DataFrame,
    feature_importance_df: pd.DataFrame,
    univariate_df: pd.DataFrame,
    redundancy_df: pd.DataFrame,
    walk_forward_df: pd.DataFrame,
) -> str:
    """Build a concise but technical markdown report."""
    best_model = summary["best_model_name"]
    comparison_df = pd.DataFrame(summary["comparison"])
    best_row = comparison_df.iloc[0]
    top_features = feature_importance_df.head(5)["feature"].tolist()
    weak_features = ", ".join(feature_importance_df.tail(5)["feature"].tolist())
    high_corr_pairs = (
        redundancy_df.head(5)
        .apply(lambda row: f"{row['feature_a']} ~ {row['feature_b']} ({row['abs_correlation']:.2f})", axis=1)
        .tolist()
    )
    top_univariate = univariate_df.head(5)["feature"].tolist()

    report = f"""# Baltasar Diagnostic Report

## Executive Summary

- Run diagnosticada: `{run_id}`
- Mejor modelo actual: `{best_model}`
- Accuracy: {_format_float(float(best_row['accuracy']))}
- F1 macro: {_format_float(float(best_row['f1_macro']))}
- Filas etiquetadas: {summary['dataset_summary']['rows']}
- Clases observadas: {summary['dataset_summary']['target_distribution']}

## Main Hypotheses

1. {_dominant_target_hypothesis(target_audit_df)}
2. {_confusion_hypothesis(best_class_diag_df)}
3. Las features mas utiles parecen concentrarse en pocas senales de contexto (`{", ".join(top_features[:3])}`), mientras varias variables aportan poco o nada (`{weak_features}`).
4. {_temporal_hypothesis(walk_forward_df)}

## Target Audit

Se evaluaron {len(target_audit_df)} configuraciones de target derivado modificando horizonte y thresholds.

{target_audit_df.to_string(index=False)}

Lectura:
- Si thresholds mas laxos reducen el desbalance pero no mejoran `f1_macro`, el problema probablemente es ruido del label y no solo soporte por clase.
- Si horizontes mas largos cambian mucho la distribucion, la definicion actual del target puede no estar alineada con la escala informativa de las features.

## Class Diagnosis

Metricas por clase para el mejor modelo:

{best_class_diag_df.to_string(index=False)}

Interpretacion:
- El modelo actual esta dominado por errores entre `BUY/SELL` y `NEUTRAL`.
- Una accuracy baja junto con precision macro mayor que f1 macro suele indicar que el clasificador acierta algunos nichos pero no generaliza de forma balanceada.

## Feature Diagnosis

Top features por importancia:
- {", ".join(top_features)}

Top features por score univariado:
- {", ".join(top_univariate)}

Pares numericos altamente correlacionados:
- {"; ".join(high_corr_pairs) if high_corr_pairs else "No se detectaron pares por encima del umbral configurado."}

## Temporal Validation

Resumen walk-forward:

{walk_forward_df.to_string(index=False)}

Lectura:
- Variaciones marcadas entre folds apoyan la hipotesis de inestabilidad temporal.
- Si un modelo mantiene una media similar pero con alta dispersion, hace falta robustecer el label y la evaluacion antes de pensar en tuning.

## Prioritized Recommendations

1. Revisar la definicion del target antes de tocar hiperparametros, especialmente thresholds y horizonte.
2. Reducir o transformar features redundantes, en especial familias de EMAs y niveles poco informativos si se confirma su baja utilidad.
3. Mantener la validacion temporal como criterio principal; no confiar en una sola particion holdout.
4. Agregar analisis de regimen temporal y persistencia de senales antes de introducir modelos mas complejos.
5. Solo despues de estabilizar target y evaluacion, considerar ajustes de clase o costo.

## Next Suggested Steps

- Probar etiquetas derivadas con reglas de evento mas cercanas a la semantica de trading real.
- Incorporar features de cambio o slope en lugar de snapshots crudos cuando la interpretabilidad lo permita.
- Evaluar por mes o por tramo de mercado para detectar donde Baltasar aprende algo util y donde no.
"""
    return report


def write_report(markdown: str, output_path: Path) -> None:
    """Persist a markdown report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
