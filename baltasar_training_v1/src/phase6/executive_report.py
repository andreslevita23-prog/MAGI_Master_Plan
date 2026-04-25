"""Executive PDF reporting for Baltasar v1.2."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from src.utils import ensure_dir, get_logger, write_json


LOGGER = get_logger("baltasar.phase6.executive")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.4f}"


def _relative_path(base_dir: Path, target_path: Path) -> str:
    return os.path.relpath(target_path, start=base_dir).replace("\\", "/")


def _save_phase_evolution(output_path: Path) -> None:
    phases = ["Initial", "Diagnosed", "v1.1", "v1.2"]
    holdout_f1 = [0.2216, 0.3426, 0.3066, 0.4014]
    walk_mean = [0.2250, 0.3199, 0.3251, 0.3865]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(phases, holdout_f1, marker="o", linewidth=2.5, label="Representative holdout F1")
    ax.plot(phases, walk_mean, marker="s", linewidth=2.5, label="Representative walk-forward F1 mean")
    ax.set_title("Baltasar Laboratory Evolution")
    ax.set_ylabel("Score")
    ax.set_xlabel("Phase")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _save_v11_v12_delta(output_path: Path) -> None:
    labels = ["Tree F1", "Tree WF Mean", "Tree WF Std", "RF F1", "RF WF Mean", "RF WF Std"]
    v11 = [0.3066, 0.3128, 0.0243, 0.3886, 0.3251, 0.0611]
    v12 = [0.3906, 0.3792, 0.0144, 0.4014, 0.3865, 0.0119]
    x = range(len(labels))

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar([i - 0.18 for i in x], v11, width=0.36, label="v1.1", color="#9ca3af")
    ax.bar([i + 0.18 for i in x], v12, width=0.36, label="v1.2", color="#2563eb")
    ax.set_xticks(list(x), labels)
    ax.set_title("v1.1 vs v1.2 Key Metrics")
    ax.set_ylabel("Score")
    ax.legend()
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def build_markdown(
    report_dir: Path,
    figure_paths: dict[str, Path],
    training_summary: dict[str, Any],
    benchmark_df: pd.DataFrame,
    class_rf_df: pd.DataFrame,
    class_tree_df: pd.DataFrame,
) -> str:
    """Build the executive markdown source."""
    baseline = benchmark_df[benchmark_df["role"] == "official_baseline"].iloc[0]
    explanatory = benchmark_df[benchmark_df["role"] == "explanatory_reference"].iloc[0]
    distribution = training_summary["target_distribution"]
    dataset = training_summary["dataset_selection"]

    return f"""# Baltasar v1.2 Executive Report

## Resumen Ejecutivo

Baltasar v1.2 es la nueva base oficial del laboratorio MAGI para clasificacion de direccion de mercado. La nueva base usa target `h12_t03`, features `compact`, `random_forest` como baseline oficial y `baseline_tree` como referencia explicable.

La decision se tomo despues de revisar el target, simplificar el set de features y validar el sistema sobre un dataset extendido de casi 24 meses. El resultado principal es que Baltasar v1.2 mejora al mismo tiempo senal y estabilidad temporal, que era exactamente el punto debil que impedia promover al bosque aleatorio en v1.1.

![Evolucion del laboratorio]({_relative_path(report_dir, figure_paths['phase_evolution'])})

## Que Construyo Codex

- Un laboratorio reproducible de entrenamiento, diagnostico y comparacion para Baltasar.
- Un proceso por fases para revisar target, features, estabilidad temporal y benchmark oficial.
- Dashboards, reportes y artefactos que permiten explicar decisiones tecnicas sin depender de memoria oral.
- La consolidacion oficial de Baltasar v1.2 con baseline, referencia explicable y benchmark versionado.

## Problema Inicial de v1.1

Antes de v1.2, el laboratorio ya habia mejorado mucho frente a la primera corrida, pero todavia tenia una tension importante:

- el target original de etapas tempranas estaba demasiado cargado hacia `NEUTRAL`
- la senal cambiaba mucho segun horizonte y threshold
- el `random_forest` mostraba mejor F1 puntual, pero no era lo bastante estable para ser baseline oficial
- el laboratorio necesitaba probar si esa mejora se sostenia fuera del dataset inicial

## Por que se reviso el target

La fase de diagnostico mostro que el target estaba explicando una parte muy grande del problema. Por eso se hizo un barrido sistematico de horizontes y thresholds y luego una validacion cruzada entre `baseline_tree` y `random_forest`.

La conclusion fue que `h12_t03` superaba a `h18_t05` porque:

- reparte mejor las clases
- sostiene mejor la senal al cambiar de modelo
- mantiene una estabilidad temporal razonable
- funciona mejor como base para escalar a una muestra mas larga

## Por que `h12_t03` reemplaza a `h18_t05`

`h18_t05` fue una buena solucion para Baltasar v1.1, pero `h12_t03` mostro mejor consistencia cuando se puso a prueba con dos modelos distintos y despues sobre el dataset extendido.

En terminos ejecutivos:

- `h18_t05` resolvio el problema de desbalance inicial
- `h12_t03` resolvio mejor el problema de generalizacion

## Por que se uso el dataset extendido de 24 meses

La pregunta clave ya no era solo “cual target se ve mejor”, sino “cual configuracion aguanta mejor cuando la muestra crece”.

El dataset extendido usado para v1.2 fue:

- fuente: `{dataset['run_name']}`
- cobertura: `{dataset['timestamp_min']}` a `{dataset['timestamp_max']}`
- filas brutas: `{dataset['rows']}`
- columnas: `{dataset['columns']}`
- archivos CSV: `{dataset['csv_files']}`

Esto permitio medir estabilidad sobre mas regimenes de mercado y reducir el riesgo de sobreinterpretar una ventana corta.

## Distribucion del target oficial

La distribucion del target `h12_t03` sobre el dataset extendido quedo mucho mas sana:

- `NEUTRAL`: {distribution['NEUTRAL']:.2%}
- `BUY`: {distribution['BUY']:.2%}
- `SELL`: {distribution['SELL']:.2%}

![Distribucion del target]({_relative_path(report_dir, figure_paths['target_distribution'])})

Lectura ejecutiva: el sistema deja de depender de una clase dominante y eso hace que `F1 macro` tenga mucho mas valor real.

## Comparacion v1.1 vs v1.2

La mejora mas importante no es solo el numero puntual, sino la combinacion entre mejora de F1 y caida de dispersion temporal.

- `baseline_tree` v1.1 -> v1.2
  - `f1_macro`: `0.3066` -> `0.3906`
  - `walk_forward_f1_mean`: `0.3128` -> `0.3792`
  - `walk_forward_f1_std`: `0.0243` -> `0.0144`
- `random_forest` v1.1 -> v1.2
  - `f1_macro`: `0.3886` -> `0.4014`
  - `walk_forward_f1_mean`: `0.3251` -> `0.3865`
  - `walk_forward_f1_std`: `0.0611` -> `0.0119`

![Comparacion v1.1 vs v1.2]({_relative_path(report_dir, figure_paths['v11_v12_delta'])})

![Benchmark oficial]({_relative_path(report_dir, figure_paths['v12_vs_v11'])})

## Por que `random_forest` ahora si fue promovido a baseline oficial

En v1.1 el `random_forest` no se promovio porque su ventaja de F1 venia acompañada de una dispersion temporal mucho mayor. En otras palabras: parecia mejor en una foto, pero no en comportamiento entre tramos.

En v1.2 eso cambia:

- `f1_macro`: {_fmt(baseline['f1_macro'])}
- `accuracy`: {_fmt(baseline['accuracy'])}
- `walk_forward_f1_mean`: {_fmt(baseline['walk_forward_f1_mean'])}
- `walk_forward_f1_std`: {_fmt(baseline['walk_forward_f1_std'])}

La razon de la promocion es simple: el bosque ya no solo gana en senal, tambien gana en estabilidad. Esa era la condicion que faltaba para convertirlo en baseline oficial.

![Walk-forward v1.2]({_relative_path(report_dir, figure_paths['walk_forward'])})

## Papel del `baseline_tree` como referencia explicable

El arbol sigue siendo una pieza importante del laboratorio. No es el baseline oficial, pero si la referencia explicable:

- `f1_macro`: {_fmt(explanatory['f1_macro'])}
- `accuracy`: {_fmt(explanatory['accuracy'])}
- `walk_forward_f1_mean`: {_fmt(explanatory['walk_forward_f1_mean'])}
- `walk_forward_f1_std`: {_fmt(explanatory['walk_forward_f1_std'])}

Su valor ejecutivo es claro:

- facilita explicacion y auditoria
- permite revisar comportamiento por clase con menos complejidad
- sirve como control interpretable si el baseline oficial cambia en futuras fases

![Confusion matrix - baseline oficial]({_relative_path(report_dir, figure_paths['rf_confusion'])})

Breve lectura: el baseline oficial ya distingue mejor las tres clases y evita el colapso extremo hacia una sola decision.

![Confusion matrix - referencia explicable]({_relative_path(report_dir, figure_paths['tree_confusion'])})

Breve lectura: el arbol sigue siendo muy util para explicar patrones, aunque el bosque quede ligeramente por delante en desempeno total.

## Metricas por clase

Baseline oficial `random_forest`:

{class_rf_df.to_string(index=False)}

Referencia explicable `baseline_tree`:

{class_tree_df.to_string(index=False)}

Lectura ejecutiva: en v1.2 ambos modelos son mas equilibrados que en etapas anteriores, y `random_forest` logra el mejor compromiso global entre `SELL`, `NEUTRAL` y `BUY`.

## Riesgos y limitaciones actuales

- El target sigue siendo derivado; no es todavia una etiqueta final de negocio.
- El dataset extendido vive fuera del repo, en la ruta de `Common Files` de MT5, por lo que la reproducibilidad depende de esa ubicacion local.
- Hay 110 gaps mayores a 8 horas; son compatibles con mercado, pero conviene seguir monitoreando segmentacion temporal.
- No hubo tuning ni calibracion; v1.2 formaliza la mejor base actual, no el techo tecnico del sistema.
- Las variables ligadas a posicion siguen teniendo missing alto y hoy no son el centro de la senal.

## Que puede hacer Baltasar hoy

- Servir como baseline serio y gobernable para clasificacion de direccion de mercado.
- Comparar futuras mejoras sobre una base ya establecida y defendible.
- Entregar senal mejor balanceada y mas estable que en v1.1.

## Que no puede hacer todavia

- No esta listo para despliegue operativo final sin una fase posterior de calibracion y gobierno.
- No sustituye por si solo la logica de negocio completa de Prosperity.
- No incorpora aun costos de error, calibracion probabilistica ni reglas de accion reales.

## Decision sugerida para Prosperity

1. Adoptar Baltasar v1.2 como nueva base oficial del laboratorio.
2. Usar `random_forest` como baseline tecnico de referencia para comparaciones futuras.
3. Mantener `baseline_tree` como modelo explicable para auditoria, demos y analisis de comportamiento.
4. Autorizar una siguiente fase enfocada en calibracion, robustez operacional y criterios de promocion hacia uso mas exigente.

## Proximos pasos recomendados

- consolidar monitoreo recurrente de estabilidad temporal
- revisar calibracion y costos por clase
- definir una etiqueta de negocio mas cercana al resultado operativo real
- establecer reglas formales para futuras promociones de baseline
"""


def build_html(
    report_dir: Path,
    markdown: str,
    output_path: Path,
    figure_paths: dict[str, Path],
    training_summary: dict[str, Any],
    benchmark_df: pd.DataFrame,
) -> None:
    """Build a print-friendly executive HTML report."""
    baseline = benchmark_df[benchmark_df["role"] == "official_baseline"].iloc[0]
    explanatory = benchmark_df[benchmark_df["role"] == "explanatory_reference"].iloc[0]
    distribution = training_summary["target_distribution"]
    dataset = training_summary["dataset_selection"]

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Baltasar v1.2 Executive Report</title>
  <style>
    @page {{
      size: A4;
      margin: 18mm 14mm 18mm 14mm;
    }}
    body {{
      font-family: "Segoe UI", Arial, sans-serif;
      color: #1f2937;
      margin: 0;
      line-height: 1.55;
      background: #f4f1ea;
    }}
    .page {{
      background: white;
      padding: 28px 34px;
      margin: 0 auto 18px auto;
      box-sizing: border-box;
      page-break-after: always;
    }}
    .page:last-child {{ page-break-after: auto; }}
    .cover {{
      min-height: 1000px;
      background: linear-gradient(135deg, #14342b 0%, #255b4d 55%, #d7e6d8 100%);
      color: white;
      position: relative;
      overflow: hidden;
    }}
    .cover h1 {{
      font-size: 34px;
      margin: 0 0 14px 0;
      line-height: 1.1;
    }}
    .cover h2 {{
      font-size: 18px;
      font-weight: 500;
      margin: 0 0 28px 0;
      color: #e6f2ea;
    }}
    .cover .badge {{
      display: inline-block;
      background: rgba(255,255,255,0.14);
      border: 1px solid rgba(255,255,255,0.25);
      border-radius: 999px;
      padding: 8px 14px;
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin-bottom: 22px;
    }}
    .cover .meta {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 28px;
      max-width: 620px;
    }}
    .cover .meta-card {{
      background: rgba(255,255,255,0.12);
      border-radius: 14px;
      padding: 14px 16px;
      border: 1px solid rgba(255,255,255,0.18);
    }}
    .cover .meta-card .label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      opacity: 0.8;
    }}
    .cover .meta-card .value {{
      font-size: 18px;
      font-weight: 700;
      margin-top: 4px;
    }}
    h1, h2, h3 {{
      color: #0f172a;
      margin-top: 0;
    }}
    h1 {{ font-size: 28px; margin-bottom: 12px; }}
    h2 {{
      font-size: 22px;
      margin-top: 26px;
      margin-bottom: 10px;
      border-bottom: 2px solid #dbe7df;
      padding-bottom: 6px;
    }}
    h3 {{
      font-size: 16px;
      margin-top: 18px;
      margin-bottom: 8px;
    }}
    .lead {{
      font-size: 17px;
      color: #334155;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin: 22px 0;
    }}
    .card {{
      background: #f8faf9;
      border: 1px solid #dce8df;
      border-radius: 16px;
      padding: 16px 18px;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin: 18px 0 22px 0;
    }}
    .kpi {{
      background: #f7f8fb;
      border: 1px solid #e1e6ef;
      border-radius: 14px;
      padding: 14px;
    }}
    .kpi .label {{
      font-size: 11px;
      text-transform: uppercase;
      color: #64748b;
      letter-spacing: 0.05em;
    }}
    .kpi .value {{
      font-size: 22px;
      font-weight: 700;
      color: #0f172a;
      margin-top: 4px;
    }}
    .kpi .note {{
      font-size: 12px;
      color: #475569;
      margin-top: 3px;
    }}
    ul {{
      padding-left: 22px;
      margin-top: 8px;
    }}
    li {{
      margin-bottom: 6px;
    }}
    .figure {{
      margin: 20px 0 26px 0;
      page-break-inside: avoid;
    }}
    .figure img {{
      width: 100%;
      border: 1px solid #d6dde7;
      border-radius: 14px;
      display: block;
      background: #fff;
    }}
    .caption {{
      font-size: 13px;
      color: #475569;
      margin-top: 8px;
    }}
    .decision {{
      background: linear-gradient(135deg, #e8f3ed 0%, #f5fbf8 100%);
      border: 1px solid #c6decf;
      border-radius: 18px;
      padding: 20px 22px;
      margin-top: 18px;
    }}
    .decision h2 {{
      border: 0;
      padding-bottom: 0;
      margin-bottom: 10px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0 18px 0;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid #dbe3ec;
      padding: 8px 10px;
      text-align: left;
    }}
    th {{
      background: #f5f8fb;
      color: #0f172a;
    }}
    .small {{
      font-size: 12px;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <section class="page cover">
    <div class="badge">Prosperity · MAGI · Executive Report</div>
    <h1>Baltasar v1.2</h1>
    <h2>Consolidacion ejecutiva desde v1.1 hasta la nueva base oficial</h2>
    <p class="lead">Este documento resume en lenguaje claro que se construyo, que se descubrio, que cambio y por que Baltasar v1.2 quedo promovido como la nueva base oficial del laboratorio.</p>
    <div class="meta">
      <div class="meta-card"><div class="label">Target oficial</div><div class="value">h12_t03</div></div>
      <div class="meta-card"><div class="label">Features</div><div class="value">compact</div></div>
      <div class="meta-card"><div class="label">Baseline oficial</div><div class="value">random_forest</div></div>
      <div class="meta-card"><div class="label">Referencia explicable</div><div class="value">baseline_tree</div></div>
      <div class="meta-card"><div class="label">Dataset extendido</div><div class="value">{dataset['rows']:,} filas</div></div>
      <div class="meta-card"><div class="label">Cobertura</div><div class="value">24 meses</div></div>
    </div>
  </section>

  <section class="page">
    <h1>Resumen Ejecutivo</h1>
    <p class="lead">Baltasar v1.2 es una mejora real sobre v1.1. La nueva configuracion no solo eleva la senal, sino que tambien reduce la dispersion temporal. Esa combinacion es la razon por la que `random_forest` ahora si puede ser promovido como baseline oficial.</p>
    <div class="kpi-grid">
      <div class="kpi"><div class="label">RF F1 macro</div><div class="value">0.4014</div><div class="note">baseline oficial v1.2</div></div>
      <div class="kpi"><div class="label">RF WF mean</div><div class="value">0.3865</div><div class="note">mejor generalizacion</div></div>
      <div class="kpi"><div class="label">RF WF std</div><div class="value">0.0119</div><div class="note">dispersion baja</div></div>
      <div class="kpi"><div class="label">Dataset</div><div class="value">148,551</div><div class="note">filas brutas</div></div>
    </div>
    <div class="summary-grid">
      <div class="card">
        <h3>Lo que cambio</h3>
        <ul>
          <li>El target oficial paso de `h18_t05` a `h12_t03`.</li>
          <li>La muestra crecio desde el dataset inicial a un dataset extendido de casi 24 meses.</li>
          <li>`random_forest` paso de challenger a baseline oficial.</li>
        </ul>
      </div>
      <div class="card">
        <h3>Por que importa</h3>
        <ul>
          <li>Se mejoro `F1 macro` sin empeorar estabilidad.</li>
          <li>La dispersion temporal cayo de forma fuerte.</li>
          <li>El laboratorio queda mejor preparado para una fase posterior de calibracion.</li>
        </ul>
      </div>
    </div>
    <div class="figure">
      <img src="{_relative_path(report_dir, figure_paths['phase_evolution'])}" alt="Evolucion del laboratorio" />
      <div class="caption">La evolucion por fases muestra que Baltasar deja atras la primera corrida debil, consolida v1.1 y da un salto adicional en v1.2 al combinar mejor senal y estabilidad.</div>
    </div>
  </section>

  <section class="page">
    <h2>Que construyo Codex</h2>
    <ul>
      <li>Un laboratorio reproducible de entrenamiento, diagnostico, rediseño y consolidacion.</li>
      <li>Un proceso auditable para revisar target, features, modelos y estabilidad temporal.</li>
      <li>Artefactos ejecutivos, tecnicos y visuales para explicar decisiones sin depender de interpretaciones ad hoc.</li>
    </ul>

    <h2>Problema inicial de v1.1</h2>
    <p>Antes de la nueva consolidacion, el laboratorio ya habia avanzado, pero todavia habia una tension entre rendimiento puntual y estabilidad temporal. La muestra inicial permitia aprender, pero no era suficiente para validar una promocion mas agresiva del baseline.</p>

    <h2>Por que se reviso el target</h2>
    <p>La fase de diagnostico mostro que gran parte del problema estaba en la definicion del target: demasiado peso de `NEUTRAL`, sensibilidad a thresholds y horizonte, e inestabilidad al cambiar de tramo temporal.</p>

    <h2>Por que `h12_t03` reemplaza a `h18_t05`</h2>
    <p>`h18_t05` fue una mejora correcta para v1.1, pero `h12_t03` mostro mejor consistencia cruzando dos modelos y luego sobre el dataset extendido. En pocas palabras: no solo se ve mejor, tambien resiste mejor.</p>
    <div class="figure">
      <img src="{_relative_path(report_dir, figure_paths['target_distribution'])}" alt="Distribucion del target" />
      <div class="caption">La distribucion del target oficial queda mucho mas equilibrada: `NEUTRAL` 39.96%, `BUY` 30.39%, `SELL` 29.65%. Eso hace que `F1 macro` capture mejor valor real.</div>
    </div>
  </section>

  <section class="page">
    <h2>Por que se uso el dataset extendido de 24 meses</h2>
    <p>La decision de negocio no podia apoyarse solo en una muestra corta. Por eso v1.2 se validó sobre un dataset extendido de casi 24 meses, desde {dataset['timestamp_min']} hasta {dataset['timestamp_max']}.</p>
    <table>
      <tr><th>Dato</th><th>Valor</th></tr>
      <tr><td>Run del dataset</td><td>{dataset['run_name']}</td></tr>
      <tr><td>Filas brutas</td><td>{dataset['rows']:,}</td></tr>
      <tr><td>Columnas</td><td>{dataset['columns']}</td></tr>
      <tr><td>CSV diarios</td><td>{dataset['csv_files']}</td></tr>
      <tr><td>Aprox. meses</td><td>{dataset['approx_months']:.2f}</td></tr>
    </table>
    <p class="small">La muestra extendida permite medir mejor robustez entre regimenes de mercado y reduce el riesgo de sobreajustar conclusiones a una ventana corta.</p>

    <h2>Comparacion v1.1 vs v1.2</h2>
    <div class="figure">
      <img src="{_relative_path(report_dir, figure_paths['v11_v12_delta'])}" alt="Comparacion v1.1 vs v1.2" />
      <div class="caption">La mejora en v1.2 no se limita al F1 puntual. Tambien cae la dispersion temporal, especialmente en `random_forest`, que era el gran pendiente de v1.1.</div>
    </div>
    <div class="figure">
      <img src="{_relative_path(report_dir, figure_paths['v12_vs_v11'])}" alt="Benchmark oficial v1.2" />
      <div class="caption">El benchmark final confirma que v1.2 supera a v1.1 tanto en señal promedio como en estabilidad entre tramos.</div>
    </div>
  </section>

  <section class="page">
    <h2>Por que `random_forest` ahora si es baseline oficial</h2>
    <p>En v1.1, el bosque aleatorio parecia mejor en una foto, pero no lo suficiente en estabilidad. En v1.2 esa objecion desaparece: ahora mejora simultaneamente `F1 macro`, `walk-forward mean` y `walk-forward std`.</p>
    <table>
      <tr><th>Modelo</th><th>F1 macro</th><th>Accuracy</th><th>WF mean</th><th>WF std</th></tr>
      <tr><td>random_forest</td><td>{_fmt(baseline['f1_macro'])}</td><td>{_fmt(baseline['accuracy'])}</td><td>{_fmt(baseline['walk_forward_f1_mean'])}</td><td>{_fmt(baseline['walk_forward_f1_std'])}</td></tr>
      <tr><td>baseline_tree</td><td>{_fmt(explanatory['f1_macro'])}</td><td>{_fmt(explanatory['accuracy'])}</td><td>{_fmt(explanatory['walk_forward_f1_mean'])}</td><td>{_fmt(explanatory['walk_forward_f1_std'])}</td></tr>
    </table>
    <div class="figure">
      <img src="{_relative_path(report_dir, figure_paths['walk_forward'])}" alt="Walk-forward v1.2" />
      <div class="caption">El walk-forward de v1.2 muestra que los dos modelos convergen a una zona mucho mas estable. Esa es la base de la promocion del bosque aleatorio.</div>
    </div>

    <h2>Papel del `baseline_tree` como referencia explicable</h2>
    <p>El arbol sigue siendo clave para auditoria, explicacion interna y lectura de comportamiento por clase. No pierde valor por dejar de ser baseline oficial; cambia su funcion dentro del gobierno del laboratorio.</p>
    <div class="summary-grid">
      <div class="figure">
        <img src="{_relative_path(report_dir, figure_paths['rf_confusion'])}" alt="RF confusion" />
        <div class="caption">El baseline oficial reparte mejor la señal entre las tres clases y evita una concentracion excesiva.</div>
      </div>
      <div class="figure">
        <img src="{_relative_path(report_dir, figure_paths['tree_confusion'])}" alt="Tree confusion" />
        <div class="caption">La referencia explicable permite entender mejor decisiones y trade-offs, aun con algo menos de desempeño total.</div>
      </div>
    </div>
  </section>

  <section class="page">
    <h2>Riesgos y limitaciones actuales</h2>
    <ul>
      <li>El target sigue siendo derivado, no una etiqueta final de negocio.</li>
      <li>El dataset extendido vive fuera del repo y depende de la ruta local de `Common Files` de MT5.</li>
      <li>Persisten gaps temporales largos compatibles con mercado, que deben seguir monitoreandose.</li>
      <li>No hubo tuning ni calibracion; esta version consolida una base, no un optimo final.</li>
    </ul>

    <h2>Decision sugerida para Prosperity</h2>
    <div class="decision">
      <h2>Decision sugerida para Prosperity</h2>
      <p>Adoptar Baltasar v1.2 como nueva base oficial del laboratorio MAGI. Usar `random_forest` como baseline tecnico de referencia para comparaciones futuras y mantener `baseline_tree` como modelo explicable para auditoria y comunicacion.</p>
      <p>La siguiente fase recomendada no es cambiar de modelo, sino mejorar calibracion, robustez operacional y definicion de etiqueta de negocio.</p>
    </div>

    <h2>Proximos pasos recomendados</h2>
    <ul>
      <li>Calibracion probabilistica y criterios de confianza por clase.</li>
      <li>Monitoreo recurrente de estabilidad temporal.</li>
      <li>Revision de target hacia una etiqueta mas cercana al resultado operativo real.</li>
      <li>Definicion formal de reglas de promocion para futuras versiones.</li>
    </ul>
  </section>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")


def render_pdf_from_html(project_root: Path, html_path: Path, pdf_path: Path) -> None:
    """Render a local HTML file to PDF using Playwright."""
    node_path = Path(r"C:\Users\Asus\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
    node_modules = Path(r"C:\Users\Asus\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules")
    renderer = project_root / "scripts" / "render_html_to_pdf.js"
    edge_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not edge_path.exists():
        edge_path = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "".join(
            [
                f"$env:NODE_PATH='{node_modules}'; ",
                f"$env:PW_EXECUTABLE_PATH='{edge_path}'; " if edge_path.exists() else "",
                f"& '{node_path}' '{renderer}' '{html_path}' '{pdf_path}'",
            ]
        ),
    ]
    subprocess.run(command, check=True, cwd=str(project_root))


def generate_v12_executive_report(config: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Generate markdown, HTML and PDF executive outputs for Baltasar v1.2."""
    artifacts_cfg = config["artifacts"]
    reports_dir = ensure_dir(project_root / artifacts_cfg["reports_dir"])
    figures_dir = ensure_dir(project_root / artifacts_cfg["figures_dir"])
    metrics_dir = ensure_dir(project_root / artifacts_cfg["metrics_dir"])

    training_summary = _load_json(reports_dir / "baltasar_v12_training_summary.json")
    benchmark_df = pd.read_csv(metrics_dir / "official_v12_benchmark.csv")
    class_rf_df = pd.read_csv(metrics_dir / "baltasar_v12_random_forest_class_metrics.csv")
    class_tree_df = pd.read_csv(metrics_dir / "baltasar_v12_baseline_tree_class_metrics.csv")

    figure_paths = {
        "phase_evolution": figures_dir / "baltasar_v12_exec_phase_evolution.png",
        "v11_v12_delta": figures_dir / "baltasar_v12_exec_v11_v12_delta.png",
        "v12_vs_v11": figures_dir / "baltasar_v12_vs_v11.png",
        "walk_forward": figures_dir / "baltasar_v12_walk_forward.png",
        "target_distribution": figures_dir / "baltasar_v12_target_distribution.png",
        "rf_confusion": figures_dir / "baltasar_v12_random_forest_confusion_matrix.png",
        "tree_confusion": figures_dir / "baltasar_v12_baseline_tree_confusion_matrix.png",
    }
    _save_phase_evolution(figure_paths["phase_evolution"])
    _save_v11_v12_delta(figure_paths["v11_v12_delta"])

    markdown = build_markdown(
        report_dir=reports_dir,
        figure_paths=figure_paths,
        training_summary=training_summary,
        benchmark_df=benchmark_df,
        class_rf_df=class_rf_df,
        class_tree_df=class_tree_df,
    )
    markdown_path = reports_dir / "baltasar_v12_executive_report.md"
    html_path = reports_dir / "baltasar_v12_executive_report.html"
    pdf_path = reports_dir / "baltasar_v12_executive_report.pdf"

    markdown_path.write_text(markdown, encoding="utf-8")
    build_html(
        report_dir=reports_dir,
        markdown=markdown,
        output_path=html_path,
        figure_paths=figure_paths,
        training_summary=training_summary,
        benchmark_df=benchmark_df,
    )
    render_pdf_from_html(project_root, html_path, pdf_path)

    summary = {
        "markdown_report_path": str(markdown_path),
        "html_report_path": str(html_path),
        "pdf_report_path": str(pdf_path),
        "figure_paths": {key: str(value) for key, value in figure_paths.items()},
        "pdf_size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0,
    }
    write_json(summary, reports_dir / "baltasar_v12_executive_report_summary.json")
    LOGGER.info("Baltasar v1.2 executive report generated.")
    return summary
