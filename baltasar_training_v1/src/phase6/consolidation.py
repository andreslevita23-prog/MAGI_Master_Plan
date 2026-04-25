"""Official consolidation for Baltasar v1.2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.utils import ensure_dir, write_json


def build_v12_consolidation_report(
    config: dict[str, Any],
    benchmark_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    baseline_class_df: pd.DataFrame,
    explanatory_class_df: pd.DataFrame,
    training_summary: dict[str, Any],
) -> str:
    """Create the official Baltasar v1.2 consolidation report."""
    official_cfg = config["official_baseline"]
    baseline_row = benchmark_df[benchmark_df["role"] == "official_baseline"].iloc[0]
    explanatory_row = benchmark_df[benchmark_df["role"] == "explanatory_reference"].iloc[0]

    return f"""# Baltasar v1.2 Consolidation

## Official Status

- Version: `{official_cfg['version']}`
- Official target: `{official_cfg['target_name']}`
- Official feature variant: `{official_cfg['feature_variant']}`
- Official baseline model: `{official_cfg['baseline_model']}`
- Explanatory reference model: `{official_cfg['challenger_model']}`
- Extended dataset run: `{training_summary['dataset_selection']['run_name']}`

## Benchmark Oficial v1.2

{benchmark_df.to_string(index=False)}

## Comparacion v1.1 vs v1.2

{comparison_df.to_string(index=False)}

## Por que cambia la baseline

- En v1.1 el `random_forest` era challenger porque tenia mejor F1 puntual pero peor estabilidad temporal.
- En v1.2, sobre 24 meses, `random_forest` mejora a la vez `f1_macro`, `walk_forward_f1_mean` y `walk_forward_f1_std`.
- Eso elimina la principal objecion tecnica que impedia promoverlo.
- `baseline_tree` se mantiene como referencia explicable porque sigue siendo mas facil de auditar y comunicar.

## Analisis de estabilidad

- Baseline oficial v1.2 (`random_forest`): holdout F1 `{baseline_row['f1_macro']:.4f}`, walk-forward mean `{baseline_row['walk_forward_f1_mean']:.4f}`, walk-forward std `{baseline_row['walk_forward_f1_std']:.4f}`.
- Referencia explicable (`baseline_tree`): holdout F1 `{explanatory_row['f1_macro']:.4f}`, walk-forward mean `{explanatory_row['walk_forward_f1_mean']:.4f}`, walk-forward std `{explanatory_row['walk_forward_f1_std']:.4f}`.
- Frente a v1.1, ambos modelos mejoran estabilidad, pero `random_forest` deja de ser un modelo de alto F1 con alta dispersion y pasa a ser el mejor equilibrio general.

## Metricas por clase

Baseline oficial:

{baseline_class_df.to_string(index=False)}

Referencia explicable:

{explanatory_class_df.to_string(index=False)}

## Riesgos actuales

- El target sigue siendo derivado, no una etiqueta final de negocio.
- El dataset extendido vive fuera del repo, en la ruta de `Common Files` de MT5, asi que la reproducibilidad depende de esa ubicacion local.
- Existen 110 gaps superiores a 8 horas; son razonables para mercado, pero conviene seguir monitoreando segmentacion temporal.
- No hubo tuning ni calibracion; esta consolidacion formaliza la base actual, no el techo de rendimiento.
- Las columnas de posicion (`entry_price`, `sl`, `tp`, `floating_pnl`, `position_type`) siguen con missing alto y deben seguir tratandose como evidencia secundaria.

## Decision documentada

- Se promueve `random_forest` como baseline oficial de Baltasar v1.2.
- Se conserva `baseline_tree` como modelo explicativo de referencia.
- No se cambian hiperparametros ni se introducen modelos nuevos en esta consolidacion.
"""


def run_v12_consolidation(config: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Create the official benchmark and report for Baltasar v1.2."""
    artifacts_cfg = config["artifacts"]
    metrics_dir = ensure_dir(project_root / artifacts_cfg["metrics_dir"])
    reports_dir = ensure_dir(project_root / artifacts_cfg["reports_dir"])

    metrics_df = pd.read_csv(metrics_dir / "baltasar_v12_metrics.csv")
    comparison_df = pd.read_csv(metrics_dir / "baltasar_v12_vs_v11.csv")
    baseline_class_df = pd.read_csv(metrics_dir / "baltasar_v12_random_forest_class_metrics.csv")
    explanatory_class_df = pd.read_csv(metrics_dir / "baltasar_v12_baseline_tree_class_metrics.csv")
    training_summary = pd.read_json(reports_dir / "baltasar_v12_training_summary.json", typ="series").to_dict()

    benchmark_df = pd.DataFrame(
        [
            {
                "role": "official_baseline",
                "version": config["official_baseline"]["version"],
                "target_name": "h12_t03",
                "feature_variant": "compact",
                "model_name": "random_forest",
                "feature_count": int(metrics_df.loc[metrics_df["model_name"] == "random_forest", "feature_count"].iloc[0]),
                "accuracy": float(metrics_df.loc[metrics_df["model_name"] == "random_forest", "accuracy"].iloc[0]),
                "f1_macro": float(metrics_df.loc[metrics_df["model_name"] == "random_forest", "f1_macro"].iloc[0]),
                "walk_forward_f1_mean": float(metrics_df.loc[metrics_df["model_name"] == "random_forest", "walk_forward_f1_mean"].iloc[0]),
                "walk_forward_f1_std": float(metrics_df.loc[metrics_df["model_name"] == "random_forest", "walk_forward_f1_std"].iloc[0]),
                "trade_off": "Promoted because the 24-month run improved both signal and temporal stability.",
            },
            {
                "role": "explanatory_reference",
                "version": config["official_baseline"]["version"],
                "target_name": "h12_t03",
                "feature_variant": "compact",
                "model_name": "baseline_tree",
                "feature_count": int(metrics_df.loc[metrics_df["model_name"] == "baseline_tree", "feature_count"].iloc[0]),
                "accuracy": float(metrics_df.loc[metrics_df["model_name"] == "baseline_tree", "accuracy"].iloc[0]),
                "f1_macro": float(metrics_df.loc[metrics_df["model_name"] == "baseline_tree", "f1_macro"].iloc[0]),
                "walk_forward_f1_mean": float(metrics_df.loc[metrics_df["model_name"] == "baseline_tree", "walk_forward_f1_mean"].iloc[0]),
                "walk_forward_f1_std": float(metrics_df.loc[metrics_df["model_name"] == "baseline_tree", "walk_forward_f1_std"].iloc[0]),
                "trade_off": "Retained as the explanatory reference because it is simpler to interpret and audit.",
            },
        ]
    )
    benchmark_path = metrics_dir / "official_v12_benchmark.csv"
    benchmark_df.to_csv(benchmark_path, index=False)

    report_markdown = build_v12_consolidation_report(
        config=config,
        benchmark_df=benchmark_df,
        comparison_df=comparison_df,
        baseline_class_df=baseline_class_df,
        explanatory_class_df=explanatory_class_df,
        training_summary=training_summary,
    )
    report_path = reports_dir / "baltasar_v12_consolidation.md"
    report_path.write_text(report_markdown, encoding="utf-8")

    summary = {
        "version": config["official_baseline"]["version"],
        "benchmark_path": str(benchmark_path),
        "report_path": str(report_path),
        "baseline": benchmark_df.iloc[0].to_dict(),
        "explanatory_reference": benchmark_df.iloc[1].to_dict(),
    }
    write_json(summary, reports_dir / "baltasar_v12_consolidation_summary.json")
    return summary
