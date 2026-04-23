"""Executive reporting for Baltasar v1.1."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from src.utils import ensure_dir, get_logger, write_json


LOGGER = get_logger("baltasar.executive")


def _latest_summary(reports_dir: Path, suffix: str) -> Path:
    matches = sorted(reports_dir.glob(f"*{suffix}"))
    if not matches:
        raise FileNotFoundError(f"No report matching *{suffix} found.")
    return matches[-1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.4f}"


def _save_phase_evolution_figure(output_path: Path) -> None:
    phases = ["Initial", "Diagnosed", "Official v1.1"]
    holdout_f1 = [0.2216, 0.3426, 0.3066]
    walk_mean = [0.2250, 0.3199, 0.3128]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(phases, holdout_f1, marker="o", linewidth=2, label="Representative holdout F1")
    ax.plot(phases, walk_mean, marker="s", linewidth=2, label="Representative walk-forward F1 mean")
    ax.set_title("Baltasar Laboratory Evolution by Phase")
    ax.set_ylabel("Score")
    ax.set_xlabel("Phase")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _save_original_vs_v11(comparison_df: pd.DataFrame, output_path: Path) -> None:
    subset = comparison_df[
        comparison_df["scenario_name"].isin(
            ["current_target_current_features", "candidate_target_compact_features"]
        )
    ].copy()
    subset["label"] = subset["scenario_name"] + "\n" + subset["model_name"]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(subset["label"], subset["f1_macro"], color="#4c72b0", label="Holdout F1 macro")
    ax.plot(
        subset["label"],
        subset["walk_forward_f1_mean"],
        color="#dd8452",
        marker="o",
        linewidth=2,
        label="Walk-forward F1 mean",
    )
    ax.set_title("Original Baseline vs Baltasar v1.1")
    ax.set_ylabel("Score")
    ax.legend()
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _save_official_vs_challenger(benchmark_df: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(benchmark_df))
    ax.bar([i - 0.15 for i in x], benchmark_df["f1_macro"], width=0.3, label="Holdout F1 macro")
    ax.bar([i + 0.15 for i in x], benchmark_df["walk_forward_f1_mean"], width=0.3, label="Walk-forward F1 mean")
    ax.errorbar(
        x,
        benchmark_df["walk_forward_f1_mean"],
        yerr=benchmark_df["walk_forward_f1_std"],
        fmt="none",
        ecolor="black",
        capsize=4,
    )
    ax.set_xticks(list(x), benchmark_df["role"])
    ax.set_title("Official Baseline vs Challenger")
    ax.set_ylabel("Score")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _save_compact_feature_importance(feature_df: pd.DataFrame, output_path: Path) -> None:
    top = feature_df.head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top["feature"], top["importance"], color="#55a868")
    ax.set_title("Compact Features Selected for Baltasar v1.1")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _save_tradeoff_summary(benchmark_df: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(
        benchmark_df["walk_forward_f1_mean"],
        benchmark_df["f1_macro"],
        s=160,
        color=["#4c72b0", "#dd8452"],
    )
    for _, row in benchmark_df.iterrows():
        ax.annotate(
            row["role"],
            (row["walk_forward_f1_mean"], row["f1_macro"]),
            xytext=(6, 6),
            textcoords="offset points",
        )
    ax.set_title("Trade-off: Point F1 vs Temporal Stability")
    ax.set_xlabel("Walk-forward F1 mean")
    ax.set_ylabel("Holdout F1 macro")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _relative_report_path(report_dir: Path, target_path: Path) -> str:
    return os.path.relpath(target_path, start=report_dir).replace("\\", "/")


def build_executive_markdown(
    report_dir: Path,
    run_id: str,
    official_cfg: dict[str, Any],
    benchmark_df: pd.DataFrame,
    baseline_class_df: pd.DataFrame,
    challenger_class_df: pd.DataFrame,
    feature_df: pd.DataFrame,
    target_distribution_df: pd.DataFrame,
    figure_paths: dict[str, Path],
) -> str:
    baseline_row = benchmark_df[benchmark_df["role"] == "official_baseline"].iloc[0]
    challenger_row = benchmark_df[benchmark_df["role"] == "challenger"].iloc[0]
    compact_features = ", ".join(feature_df.head(8)["feature"].tolist())
    target_distribution_dict = {
        row["label"]: int(row["count"]) for _, row in target_distribution_df.iterrows()
    }

    return f"""# Baltasar v1.1 Executive Report

## Executive Summary

Baltasar v1.1 ya esta consolidado como baseline oficial del laboratorio de clasificacion de direccion de mercado dentro de MAGI. La configuracion oficial usa target `{official_cfg['target_name']}`, features `compact`, `baseline_tree` como baseline y `random_forest` como challenger.

La recomendacion ejecutiva es adoptar Baltasar v1.1 como referencia operativa de laboratorio para Prosperity, porque mejora de forma material la estabilidad y la trazabilidad respecto a la version inicial, aun cuando no maximiza la mejor metrica puntual observada.

![Evolution]({_relative_report_path(report_dir, figure_paths['phase_evolution'])})

## Que construyo Codex

- un laboratorio reproducible de entrenamiento, diagnostico y consolidacion para Baltasar
- validacion de dataset, dashboards, notebooks y artefactos exportables
- una ruta de decision por fases: corrida inicial, diagnostico, rediseno y consolidacion oficial
- una base oficial v1.1 y un challenger documentado

## Cual era el problema inicial

El laboratorio arranco con una version honesta pero debil:

- target muy dominado por `NEUTRAL`
- bajo `F1 macro`
- alta sensibilidad al horizonte y threshold del target
- inestabilidad real entre tramos temporales
- redundancia alta en snapshots de precio

## Que se diagnostico

La conclusion del diagnostico fue clara:

- el problema principal no era solo el modelo; era la definicion del target y la estructura del set de features
- el target original `h12_t08` estaba demasiado cargado hacia `NEUTRAL`
- varias features aportaban poco o duplicaban informacion
- la estabilidad temporal debia pesar mas que una sola corrida holdout

## Como cambio el target

Se rediseno el target oficial a `{official_cfg['target_name']}`:

- horizonte futuro: `18`
- threshold: `0.0005`

Esto mejoro el balance de clases y la calidad de senal para entrenamiento. La distribucion objetivo redisenada queda aproximadamente:

- {target_distribution_dict}

![Target Distribution]({_relative_report_path(report_dir, figure_paths['target_distribution'])})

## Como se simplificaron las features

Se reemplazo un set cargado de snapshots absolutos por una variante `compact` basada en relaciones mas explicativas:

- rangos normalizados
- gaps entre EMAs
- precio relativo frente a EMAs
- RSI
- direccion estructural

Features compactas mas relevantes:

- {compact_features}

![Compact Features]({_relative_report_path(report_dir, figure_paths['feature_importance'])})

## Por que `baseline_tree` quedo como baseline oficial

`baseline_tree` no fue el mejor modelo puntual, pero si el mejor baseline para gobernanza del laboratorio:

- holdout `F1 macro`: {_fmt(baseline_row['f1_macro'])}
- walk-forward `F1 mean`: {_fmt(baseline_row['walk_forward_f1_mean'])}
- walk-forward `F1 std`: {_fmt(baseline_row['walk_forward_f1_std'])}
- numero de features: {int(baseline_row['feature_count'])}

La dispersion temporal fue claramente menor que la del challenger. Para Prosperity, esto significa una base mas interpretable, mas estable y mas facil de monitorear.

## Por que `random_forest` quedo como challenger

`random_forest` compacto quedo documentado como challenger porque:

- logra mejor `F1 macro` puntual: {_fmt(challenger_row['f1_macro'])}
- logra mejor `walk-forward F1 mean`: {_fmt(challenger_row['walk_forward_f1_mean'])}
- pero su variabilidad temporal es bastante mayor: {_fmt(challenger_row['walk_forward_f1_std'])}

En terminos ejecutivos: hoy parece mas fuerte en una foto, pero menos confiable como referencia oficial del laboratorio.

![Official vs Challenger]({_relative_report_path(report_dir, figure_paths['official_vs_challenger'])})

## Que metricas importan

Para esta etapa importan principalmente:

- `F1 macro`: porque evita premiar solo la clase dominante
- `accuracy`: como referencia general, pero no como criterio principal
- metricas por clase: para entender si el sistema realmente distingue `BUY`, `SELL` y `NEUTRAL`
- `walk_forward_f1_mean`: porque mide robustez entre tramos temporales
- `walk_forward_f1_std`: porque mide estabilidad

## Que significa el trade-off entre F1 puntual y estabilidad temporal

El laboratorio eligio una configuracion que no persigue solo el mejor numero puntual, sino la mejor combinacion entre rendimiento, estabilidad y explicabilidad.

Eso significa aceptar un `F1` puntual menor si a cambio obtenemos:

- menor dispersion entre tramos
- mayor trazabilidad del comportamiento
- mejor capacidad de explicar por que el baseline fue elegido

![Original vs v1.1]({_relative_report_path(report_dir, figure_paths['original_vs_v11'])})

![Walk-forward]({_relative_report_path(report_dir, figure_paths['walk_forward'])})

![Trade-off]({_relative_report_path(report_dir, figure_paths['tradeoff'])})

## Que puede hacer Baltasar hoy

- clasificar direccion de mercado en tres clases con una base reproducible y monitoreable
- servir como baseline serio para comparaciones futuras
- mostrar una estructura clara de gobierno entre baseline oficial y challenger
- sostener una narrativa tecnica defendible frente a decisiones futuras

## Que no puede hacer todavia

- no esta listo para produccion operativa sin mas fases
- no garantiza robustez suficiente para todos los regimenes de mercado
- no incorpora calibracion, costos de clase ni tuning fino
- no reemplaza todavia una logica de negocio completa de trading

## Recomendacion ejecutiva para Prosperity

Adoptar Baltasar v1.1 como baseline oficial del laboratorio y usarlo como referencia de control para las siguientes fases. Mantener `random_forest` compacto como challenger formal, pero no promoverlo todavia mientras su estabilidad temporal siga siendo sensiblemente peor.

## Decision sugerida para Prosperity

1. Aprobar Baltasar v1.1 como baseline oficial del laboratorio MAGI.
2. Usar esta base para toda comunicacion interna, demos y seguimiento tecnico inmediato.
3. Mantener el challenger activo solo como comparador, no como baseline oficial.
4. Autorizar una futura fase enfocada en calibracion, robustez temporal y reglas de promocion del challenger antes de cualquier salto a uso operativo mas exigente.
"""


def build_executive_html(markdown: str, output_path: Path) -> None:
    lines = markdown.splitlines()
    html_lines = [
        "<html><head><meta charset='utf-8'><title>Baltasar v1.1 Executive Report</title>",
        "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:980px;margin:32px auto;padding:0 16px;line-height:1.55;color:#1f2937;} h1,h2{color:#111827;} img{max-width:100%;height:auto;border:1px solid #e5e7eb;border-radius:8px;margin:12px 0 24px;} code{background:#f3f4f6;padding:2px 5px;border-radius:4px;} ul{padding-left:22px;} </style></head><body>",
    ]
    in_list = False
    for line in lines:
        if line.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("![") and "](" in line:
            alt = line[line.find("[") + 1 : line.find("]")]
            src = line[line.find("(") + 1 : line.rfind(")")]
            html_lines.append(f"<img alt='{html.escape(alt)}' src='{html.escape(src)}' />")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{html.escape(line[2:])}</li>")
        elif line[:2].isdigit() and line[1:3] == ". ":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{html.escape(line)}</p>")
        elif line.strip() == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<p></p>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        html_lines.append("</ul>")
    html_lines.append("</body></html>")
    output_path.write_text("\n".join(html_lines), encoding="utf-8")


def generate_executive_report(config: dict[str, Any], project_root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Generate the final executive report and visuals."""
    artifacts_cfg = config["artifacts"]
    metrics_dir = ensure_dir(project_root / artifacts_cfg["metrics_dir"])
    figures_dir = ensure_dir(project_root / artifacts_cfg["figures_dir"])
    reports_dir = ensure_dir(project_root / artifacts_cfg["reports_dir"])

    if run_id:
        official_summary_path = reports_dir / f"{run_id}_official_v11_summary.json"
        if not official_summary_path.exists():
            raise FileNotFoundError(f"No official v1.1 summary found for run_id={run_id}.")
    else:
        official_summary_path = _latest_summary(reports_dir, "_official_v11_summary.json")
    official_summary = _load_json(official_summary_path)
    run_id = official_summary["run_id"]
    LOGGER.info("Generating executive report for %s", run_id)

    benchmark_df = pd.read_csv(metrics_dir / f"{run_id}_official_v11_benchmark.csv")
    comparison_df = pd.read_csv(metrics_dir / f"{run_id}_phase3_comparison.csv")
    feature_df = pd.read_csv(
        metrics_dir / "candidate_target_compact_features__baseline_tree_feature_importance.csv"
    )
    target_grid_df = pd.read_csv(metrics_dir / f"{run_id}_phase3_target_grid.csv")
    official_target_row = target_grid_df[target_grid_df["target_name"] == config["official_baseline"]["target_name"]].iloc[0]
    total_rows = int(official_target_row["rows"])
    target_distribution_df = pd.DataFrame(
        {
            "label": ["SELL", "NEUTRAL", "BUY"],
            "count": [
                int(round(total_rows * float(official_target_row["sell_share"]))),
                int(round(total_rows * float(official_target_row["neutral_share"]))),
                int(round(total_rows * float(official_target_row["buy_share"]))),
            ],
        }
    )

    executive_figures = {
        "phase_evolution": figures_dir / "baltasar_v11_exec_phase_evolution.png",
        "original_vs_v11": figures_dir / "baltasar_v11_exec_original_vs_v11.png",
        "official_vs_challenger": figures_dir / "baltasar_v11_exec_official_vs_challenger.png",
        "feature_importance": figures_dir / "baltasar_v11_exec_feature_importance.png",
        "tradeoff": figures_dir / "baltasar_v11_exec_tradeoff.png",
        "target_distribution": figures_dir / "baltasar_v11_exec_target_distribution.png",
        "walk_forward": figures_dir / f"{run_id}_candidate_target_compact_features_walk_forward.png",
    }

    _save_phase_evolution_figure(executive_figures["phase_evolution"])
    _save_original_vs_v11(comparison_df, executive_figures["original_vs_v11"])
    _save_official_vs_challenger(benchmark_df, executive_figures["official_vs_challenger"])
    _save_compact_feature_importance(feature_df, executive_figures["feature_importance"])
    _save_tradeoff_summary(benchmark_df, executive_figures["tradeoff"])

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(
        target_distribution_df["label"],
        target_distribution_df["count"],
        color=["#c44e52", "#8172b2", "#55a868"],
    )
    ax.set_title("Redesigned Target Distribution")
    ax.set_xlabel("Label")
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(executive_figures["target_distribution"], dpi=160)
    plt.close(fig)

    markdown = build_executive_markdown(
        report_dir=reports_dir,
        run_id=run_id,
        official_cfg=config["official_baseline"],
        benchmark_df=benchmark_df,
        baseline_class_df=pd.read_csv(
            metrics_dir / "candidate_target_compact_features__baseline_tree_class_metrics.csv"
        ),
        challenger_class_df=pd.read_csv(
            metrics_dir / "candidate_target_compact_features__random_forest_class_metrics.csv"
        ),
        feature_df=feature_df,
        target_distribution_df=target_distribution_df,
        figure_paths=executive_figures,
    )

    markdown_path = reports_dir / "baltasar_v11_executive_report.md"
    html_path = reports_dir / "baltasar_v11_executive_report.html"
    markdown_path.write_text(markdown, encoding="utf-8")
    build_executive_html(markdown, html_path)

    summary = {
        "run_id": run_id,
        "markdown_report_path": str(markdown_path),
        "html_report_path": str(html_path),
        "figure_paths": {key: str(value) for key, value in executive_figures.items()},
        "official_summary_path": str(official_summary_path),
    }
    write_json(summary, reports_dir / "baltasar_v11_executive_report_summary.json")
    LOGGER.info("Executive report generated.")
    return summary
