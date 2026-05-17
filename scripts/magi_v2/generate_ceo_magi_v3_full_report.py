from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


DOC_PATH = Path("docs/ceo_magi_v3_full_report.md")
PDF_PATH = Path("reports/ceo_magi_v3_full_report.pdf")
ASSET_DIR = Path("reports/ceo_magi_v3_assets")

SUMMARY_METRICS = Path("artifacts/magi_validation/summary_metrics.csv")
ONLINE_METRICS = Path("artifacts/magi_validation/online_priority_scoring_metrics.csv")
THRESHOLD_SWEEP = Path("artifacts/magi_validation/online_priority_threshold_sweep.csv")
COST_VALIDATION = Path("artifacts/magi_validation/online_priority_cost_validation.csv")
CEO_SUMMARY = Path("artifacts/ceo_magi_v3/ceo_magi_v3_summary.json")
RANDOM_MONTHS = Path("artifacts/ceo_magi_v3/random_3_months_monthly_summary.csv")
STRESS_MONTHS = Path("artifacts/ceo_magi_v3/stress_months_monthly_summary_full.csv")
DRY_RUN_SUMMARY = Path("artifacts/ceo_magi_v3/bot_b_dry_run_summary.md")


def main() -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    data = load_data()
    chart_paths = build_charts(data)
    markdown = build_markdown(data, chart_paths)
    DOC_PATH.write_text(markdown, encoding="utf-8")
    build_pdf(data, chart_paths)

    print(f"reporte_md={DOC_PATH}")
    print(f"reporte_pdf={PDF_PATH}")
    for name, path in chart_paths.items():
        print(f"grafico_{name}={path}")


def load_data() -> dict[str, Any]:
    return {
        "summary": pd.read_csv(SUMMARY_METRICS),
        "online": pd.read_csv(ONLINE_METRICS),
        "threshold": pd.read_csv(THRESHOLD_SWEEP),
        "costs": pd.read_csv(COST_VALIDATION),
        "ceo": json.loads(CEO_SUMMARY.read_text(encoding="utf-8")),
        "random_months": pd.read_csv(RANDOM_MONTHS),
        "stress": pd.read_csv(STRESS_MONTHS),
    }


def build_charts(data: dict[str, Any]) -> dict[str, Path]:
    plt.style.use("seaborn-v0_8-whitegrid")
    paths = {
        "base_pf_dd": ASSET_DIR / "ceo_magi_v3_base_pf_dd.png",
        "threshold_tradeoff": ASSET_DIR / "ceo_magi_v3_threshold_tradeoff.png",
        "costs": ASSET_DIR / "ceo_magi_v3_cost_validation.png",
        "stress": ASSET_DIR / "ceo_magi_v3_stress_months.png",
    }
    chart_base_pf_dd(data["summary"], paths["base_pf_dd"])
    chart_threshold(data["threshold"], paths["threshold_tradeoff"])
    chart_costs(data["costs"], paths["costs"])
    chart_stress(data["stress"], paths["stress"])
    return paths


def chart_base_pf_dd(summary: pd.DataFrame, path: Path) -> None:
    rows = summary[(summary["split"].eq("test")) & (summary["direction"].eq("ALL"))].copy()
    rows["short"] = ["A", "B", "C", "D"]
    fig, ax1 = plt.subplots(figsize=(8, 4.2))
    ax2 = ax1.twinx()
    ax1.bar(rows["short"], rows["profit_factor"], color="#2563EB", alpha=0.82, label="Profit Factor")
    ax2.plot(rows["short"], rows["max_drawdown_r"], color="#DC2626", marker="o", linewidth=2.2, label="Drawdown")
    ax1.set_ylabel("Profit Factor")
    ax2.set_ylabel("Drawdown máximo (R)")
    ax1.set_title("Validación base: mejora de eficiencia y reducción de riesgo")
    ax1.set_ylim(0, max(rows["profit_factor"]) * 1.35)
    ax2.set_ylim(0, max(rows["max_drawdown_r"]) * 1.15)
    for x, pf in zip(rows["short"], rows["profit_factor"]):
        ax1.text(x, pf + 0.08, f"{pf:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def chart_threshold(threshold: pd.DataFrame, path: Path) -> None:
    fig, ax1 = plt.subplots(figsize=(8, 4.2))
    ax2 = ax1.twinx()
    ax1.plot(threshold["min_score"], threshold["profit_factor"], color="#059669", marker="o", label="PF")
    ax2.bar(threshold["min_score"].astype(str), threshold["trades"], color="#94A3B8", alpha=0.55, label="Trades")
    ax1.axvline(0.20, color="#111827", linestyle="--", linewidth=1)
    ax1.text(0.205, max(threshold["profit_factor"]) * 0.72, "Umbral operativo 0.20", fontsize=9)
    ax1.set_xlabel("Umbral mínimo de score")
    ax1.set_ylabel("Profit Factor")
    ax2.set_ylabel("Número de trades")
    ax1.set_title("Tradeoff entre calidad y volumen")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def chart_costs(costs: pd.DataFrame, path: Path) -> None:
    rows = costs[(costs["segment_type"].eq("test")) & (costs["segment"].eq("ALL"))].copy()
    wanted = ["comparison_score_0_20_no_costs", "low_costs", "medium_costs", "high_costs_stress"]
    rows = rows[rows["cost_scenario"].isin(wanted)].copy()
    labels = ["Sin costos", "Costos bajos", "Costos medios", "Stress"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(labels, rows["profit_factor"], color=["#0F766E", "#2563EB", "#7C3AED", "#B45309"])
    ax.axhline(1.0, color="#DC2626", linestyle="--", linewidth=1)
    ax.set_ylabel("Profit Factor")
    ax.set_title("Validación con costos: el edge se reduce, pero sobrevive")
    for i, value in enumerate(rows["profit_factor"]):
        ax.text(i, value + 0.08, f"{value:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def chart_stress(stress: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    colors_ = ["#2563EB" if value >= 0 else "#DC2626" for value in stress["net_pips_month"]]
    ax.bar(stress["month"], stress["net_pips_month"], color=colors_)
    ax.axhline(0, color="#111827", linewidth=1)
    ax.set_ylabel("Pips netos equivalentes")
    ax.set_title("Meses de estrés: resistencia y punto débil reciente")
    for i, value in enumerate(stress["net_pips_month"]):
        ax.text(i, value + (25 if value >= 0 else -35), f"{value:.1f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def build_markdown(data: dict[str, Any], charts: dict[str, Path]) -> str:
    ceo_test = data["ceo"]["metrics"]["test"]
    ceo_all = data["ceo"]["metrics"]["all"]
    base = base_rows(data["summary"])
    scoring = scoring_rows(data["online"])
    threshold = threshold_rows(data["threshold"])
    costs = cost_rows(data["costs"])
    random_months = month_rows(data["random_months"], include_context=False)
    stress = month_rows(data["stress"], include_context=True)

    lines = [
        "# Informe Final CEO-MAGI v3",
        "",
        "## Sección 1 — Resumen Ejecutivo",
        "",
        "MAGI es un sistema de decisión para trading diseñado para responder una pregunta sencilla: cuándo vale la pena operar y cuándo es mejor no hacer nada. No busca aumentar la cantidad de operaciones, sino mejorar la calidad de cada decisión.",
        "",
        "En esta fase se consolidó CEO-MAGI v3, la capa que recibe las señales de los módulos internos, decide si una operación debe ejecutarse y genera un contrato JSON listo para Bot B. El avance principal no fue solo mejorar métricas, sino convertir un conjunto de modelos y reglas en una política operativa auditable.",
        "",
        f"En la muestra de test, CEO-MAGI v3 alcanzó PF `{ceo_test['profit_factor']:.4f}`, Avg R `{ceo_test['avg_r']:.4f}`, drawdown máximo `{ceo_test['max_drawdown_r']:.2f}R` y win rate `{ceo_test['win_rate']:.2%}`. En términos simples: por cada unidad de pérdida, el sistema generó más de dos unidades y media de ganancia bruta, con una pérdida acumulada máxima controlada frente a los escenarios base.",
        "",
        f"En el conjunto completo offline, el sistema cerró con PF `{ceo_all['profit_factor']:.4f}`, Avg R `{ceo_all['avg_r']:.4f}` y win rate `{ceo_all['win_rate']:.2%}`. Estos resultados no garantizan rendimiento futuro, pero sí muestran que la arquitectura tiene una ventaja cuantificable bajo validación histórica y costos simulados.",
        "",
        "**Conclusión ejecutiva:** MAGI se encuentra en una fase pre-live viable. El sistema no debe considerarse terminado ni garantizado, pero sí está suficientemente estructurado, documentado y validado para pasar a una demo controlada sin riesgo real.",
        "",
        "## Sección 2 — Problema y Enfoque",
        "",
        "El problema central del trading tradicional no es solo predecir dirección. Muchos sistemas fallan porque operan demasiado, ignoran el contexto, subestiman costos reales o mantienen exposición en condiciones adversas. En la práctica, una estrategia puede acertar varias veces y aun así perder dinero si toma demasiadas operaciones de baja calidad o no controla el drawdown.",
        "",
        "La mayoría de participantes pierde porque confunde actividad con ventaja. Más trades no significa mejor sistema. Un enfoque serio debe filtrar, priorizar y abstenerse cuando el entorno no compensa el riesgo.",
        "",
        "MAGI aborda este problema separando responsabilidades. Un módulo identifica oportunidad, otro evalúa contexto, otro controla riesgo, y una capa final decide. Esta separación reduce la dependencia de una única señal y permite auditar qué parte del sistema aporta valor o protege capital.",
        "",
        "## Sección 3 — Arquitectura del Sistema",
        "",
        "- **Baltasar** evalúa dirección. Su función es detectar si existe una oportunidad BUY o SELL.",
        "- **Gaspar** evalúa contexto. Su papel es advertir si el mercado se está deteriorando o si el entorno es menos favorable.",
        "- **Melchor** evalúa riesgo. Cuando Melchor marca `BLOCK`, CEO-MAGI no debe operar.",
        "- **Scoring** ordena la calidad de las oportunidades usando variables disponibles al momento de entrada.",
        "- **CEO-MAGI v3** toma la decisión final: no operar, operar en modo cauteloso, operar normal u operar premium.",
        "",
        "El sistema es modular. Esto es importante porque permite mejorar o auditar cada componente sin cambiar todo el conjunto. En esta fase, no se entrenaron nuevos modelos para forzar resultados; se formalizó la decisión final usando reglas y scores ya validados.",
        "",
        "## Sección 4 — Metodología de Validación",
        "",
        "La validación se realizó sobre un periodo multianual entre 2020 y 2026. Esto incluye entornos de mercado distintos: pandemia, inflación, periodos normales y un tramo reciente problemático en 2026.",
        "",
        "Se evaluaron escenarios progresivos:",
        "",
        "- **A:** Baltasar solo.",
        "- **B:** Baltasar + Gaspar.",
        "- **C:** Baltasar + Gaspar + Melchor con regla principal de riesgo.",
        "- **D:** Variante más conservadora enfocada en proxy de régimen problemático.",
        "",
        "También se eliminó un sesgo importante: una versión inicial de scoring seleccionaba la mejor señal dentro de una ventana futura de 15 minutos. Esa lógica no es ejecutable en vivo. Por eso se rehizo el scoring en modo estrictamente online: el sistema solo puede decidir con información disponible en ese instante.",
        "",
        "Finalmente, se validó el desempeño con costos bajos, medios y de estrés. Esto aproxima el impacto de spread, comisión y slippage, aunque todavía no reemplaza una ejecución real en MT5.",
        "",
        "## Sección 5 — Resultados Interpretados",
        "",
        "Antes de leer las tablas, conviene traducir las métricas:",
        "",
        "- **Profit Factor (PF):** mide cuánto gana el sistema por cada unidad que pierde. Un PF superior a 1 indica ventaja bruta; cuanto más alto, mejor, siempre que no venga de una muestra demasiado pequeña.",
        "- **Avg R:** mide el resultado promedio por operación en unidades de riesgo. Un Avg R positivo significa que cada operación aprobada aporta valor esperado.",
        "- **Drawdown:** mide la caída máxima acumulada. Es una medida de dolor operativo y riesgo psicológico.",
        "- **Win rate:** mide porcentaje de operaciones ganadoras. No basta por sí solo: un sistema puede ganar poco y perder mucho.",
        "",
        "### Validación A/B/C/D",
        "",
        markdown_table(["Escenario", "Trades", "PF", "Avg R", "Drawdown", "Win rate"], base),
        "",
        "La lectura es clara: Baltasar solo encuentra oportunidades, pero su drawdown es demasiado alto. Al incorporar Gaspar hay una mejora moderada. El salto importante llega al incorporar Melchor: el escenario C reduce el drawdown de `266.14R` a `41.16R` y eleva el PF de `1.1621` a `2.4330` en test. Esto sugiere que el control de riesgo no es accesorio; es central para que MAGI sea operable.",
        "",
        f"![Validación base]({charts['base_pf_dd'].as_posix()})",
        "",
        "El gráfico muestra dos cosas a la vez: el PF sube cuando el sistema se vuelve más selectivo, y el drawdown cae de forma significativa. Para un inversionista, esta combinación es más importante que una simple mejora de aciertos.",
        "",
        "### Scoring causal",
        "",
        markdown_table(["Estrategia", "Trades", "PF", "Avg R", "Drawdown", "Win rate"], scoring),
        "",
        "La versión no causal muestra un PF extraordinario, pero no debe usarse como referencia operativa porque miraba una ventana futura. La versión online causal reduce ese PF, como era esperable, pero mantiene una mejora real frente a la base: PF `2.2310` versus `1.2119` y Avg R `0.5296` versus `0.1313`. Esto indica que el edge no dependía completamente del sesgo inicial.",
        "",
        "## Sección 6 — Robustez del Sistema",
        "",
        "La robustez se evaluó desde tres ángulos: sensibilidad al umbral de score, costos de ejecución y comportamiento en meses específicos.",
        "",
        "### Umbral operativo",
        "",
        markdown_table(["Score mínimo", "Trades", "PF", "Avg R", "Drawdown", "Total R"], threshold),
        "",
        "Subir el umbral mejora PF porque el sistema opera menos y elige señales más fuertes. Pero demasiada exigencia reduce volumen y puede hacer que las métricas dependan de pocas operaciones. El umbral `0.20` ofrece un equilibrio razonable: mejora calidad sin vaciar el sistema.",
        "",
        f"![Tradeoff de umbral]({charts['threshold_tradeoff'].as_posix()})",
        "",
        "La curva muestra el tradeoff natural entre calidad y volumen. La recomendación de `0.20` no se basa en maximizar PF, sino en conservar suficientes operaciones para que el sistema siga siendo evaluable.",
        "",
        "### Validación con costos",
        "",
        markdown_table(["Escenario", "Trades", "PF", "Avg R", "Drawdown", "Total R"], costs),
        "",
        "Los costos reducen el rendimiento, como deben hacerlo en una validación honesta. Aun así, el sistema mantiene PF superior a 1 incluso en el escenario de estrés. Esto no elimina el riesgo de ejecución real, pero sí indica que el edge no desaparece inmediatamente al introducir fricción.",
        "",
        f"![Validación con costos]({charts['costs'].as_posix()})",
        "",
        "### Meses normales y meses de estrés",
        "",
        "La auditoría de tres meses aleatorios no continuos mostró meses positivos y aritméticamente consistentes:",
        "",
        markdown_table(["Mes", "Ops", "Ganadoras", "Perdedoras", "Win rate", "Pips netos", "Duración prom."], random_months),
        "",
        "En meses de estrés, el resultado es más matizado:",
        "",
        markdown_table(["Mes", "Contexto", "Ops", "Ganadoras", "Perdedoras", "Win rate", "Pips netos", "Duración prom."], stress),
        "",
        f"![Meses de estrés]({charts['stress'].as_posix()})",
        "",
        "El sistema sobrevive en marzo de 2020 y abril de 2022, dos entornos difíciles. Sin embargo, abril de 2026 muestra pérdida. Esta observación no debe ocultarse: es una alerta útil para monitoreo de régimen.",
        "",
        "**Nota explícita:** El mes 2026-04 contiene datos parciales (~10 días) en el dataset, por lo tanto sus resultados no deben considerarse representativos ni comparables con meses completos.",
        "",
        "## Sección 7 — Limitaciones Actuales",
        "",
        "La validación aún no equivale a producción real. Las principales limitaciones son:",
        "",
        "- Los pips son derivados de R con SL fijo de 10 pips; no son pips reportados por broker.",
        "- El slippage fue simulado, no medido en ejecución real.",
        "- El spread histórico se aproximó desde el dataset, pero falta validación broker a broker.",
        "- No existe todavía ejecución real en MT5.",
        "- Falta validación demo/live con latencia, rechazos, recotizaciones y condiciones reales.",
        "- `exit_price` no está disponible en los artefactos actuales, por lo que no se audita geometría exacta de salida.",
        "",
        "Estas limitaciones no invalidan el sistema; delimitan correctamente la siguiente fase.",
        "",
        "## Sección 8 — Estado Operativo",
        "",
        "CEO-MAGI v3 genera un contrato JSON para Bot B. Ese contrato fue probado en dry-run: se leyeron 6,539 decisiones, con 3,346 instrucciones ejecutables, 3,193 instrucciones de no operar, 0 rechazos y 0 warnings contractuales.",
        "",
        markdown_table(["Métrica", "Resultado"], dry_run_rows()),
        "",
        "Esto significa que el sistema ya puede comunicarse de forma estructurada con una capa de ejecución simulada. No significa que esté listo para enviar dinero real al mercado. El paso correcto es un runtime adapter en modo shadow o demo, donde cada decisión se registre y se compare contra la ejecución real sin riesgo.",
        "",
        "## Sección 9 — Conclusión Estratégica",
        "",
        "MAGI no debe presentarse como un sistema perfecto ni garantizado. Esa sería una lectura incorrecta y poco profesional. Lo que sí puede afirmarse es que la arquitectura muestra una ventaja histórica consistente, que el control de riesgo mejora materialmente el comportamiento del sistema, y que la capa CEO-MAGI v3 convierte la investigación en una política operativa auditable.",
        "",
        "**Conclusión final:** MAGI es viable en fase pre-live, con alto potencial, pendiente de validación en entorno real. El siguiente paso no es live directo; es demo controlada con medición estricta de ejecución, slippage, estabilidad por régimen y comportamiento de Bot B.",
        "",
        "## Próximo paso recomendado",
        "",
        "Implementar un runtime adapter en modo shadow/demo, sin riesgo real, que conecte CEO-MAGI v3 con Bot B, registre cada decisión y compare la ejecución teórica contra condiciones reales de broker.",
        "",
    ]
    return "\n".join(lines)


def base_rows(summary: pd.DataFrame) -> list[list[Any]]:
    rows = summary[(summary["split"].eq("test")) & (summary["direction"].eq("ALL"))].copy()
    return [
        [
            label_short(row["scenario_label"]),
            int(row["trades"]),
            f"{row['profit_factor']:.4f}",
            f"{row['avg_r']:.4f}",
            f"{row['max_drawdown_r']:.2f}R",
            f"{row['win_rate']:.2%}",
        ]
        for _, row in rows.iterrows()
    ]


def scoring_rows(online: pd.DataFrame) -> list[list[Any]]:
    rows = online[(online["segment_type"].eq("split")) & (online["segment"].eq("test"))].copy()
    labels = {
        "A_base_scenario_c": "Base C realista",
        "B_scoring_simple_noncausal": "Scoring no causal",
        "C_scoring_online_causal": "Scoring online causal",
    }
    return [
        [
            labels.get(row["strategy"], row["strategy"]),
            int(row["trades"]),
            f"{row['profit_factor']:.4f}",
            f"{row['avg_r']:.4f}",
            f"{row['max_drawdown_r']:.2f}R",
            f"{row['win_rate']:.2%}",
        ]
        for _, row in rows.iterrows()
    ]


def threshold_rows(threshold: pd.DataFrame) -> list[list[Any]]:
    shown = threshold[threshold["min_score"].isin([0.0, 0.1, 0.2, 0.3, 0.4])].copy()
    return [
        [
            f"{row['min_score']:.2f}",
            int(row["trades"]),
            f"{row['profit_factor']:.4f}",
            f"{row['avg_r']:.4f}",
            f"{row['max_drawdown_r']:.2f}R",
            f"{row['total_r']:.2f}",
        ]
        for _, row in shown.iterrows()
    ]


def cost_rows(costs: pd.DataFrame) -> list[list[Any]]:
    rows = costs[(costs["segment_type"].eq("test")) & (costs["segment"].eq("ALL"))].copy()
    wanted = ["comparison_score_0_20_no_costs", "low_costs", "medium_costs", "high_costs_stress"]
    rows = rows[rows["cost_scenario"].isin(wanted)]
    label_map = {
        "comparison_score_0_20_no_costs": "Sin costos",
        "low_costs": "Costos bajos",
        "medium_costs": "Costos medios",
        "high_costs_stress": "Costos altos / stress",
    }
    return [
        [
            label_map.get(row["cost_scenario"], row["label"]),
            int(row["trades"]),
            f"{row['profit_factor']:.4f}",
            f"{row['avg_r']:.4f}",
            f"{row['max_drawdown_r']:.2f}R",
            f"{row['total_r']:.2f}",
        ]
        for _, row in rows.iterrows()
    ]


def month_rows(frame: pd.DataFrame, include_context: bool) -> list[list[Any]]:
    rows = []
    for _, row in frame.iterrows():
        item = [
            row["month"],
            int(row["trades_executed"]),
            int(row["winning_trades"]),
            int(row["losing_trades"]),
            f"{row['win_rate']:.2%}",
            f"{row['net_pips_month']:.1f}",
            row["avg_duration"],
        ]
        if include_context:
            item.insert(1, row["stress_label"])
        rows.append(item)
    return rows


def dry_run_rows() -> list[list[str]]:
    return [
        ["Decisiones leídas", "6,539"],
        ["ACK_EXECUTABLE", "3,346"],
        ["ACK_DO_NOTHING", "3,193"],
        ["Rechazos", "0"],
        ["Warnings contractuales", "0"],
        ["Órdenes enviadas", "0"],
    ]


def label_short(label: str) -> str:
    if label == "Baltasar solo":
        return "A — Baltasar solo"
    if label == "Baltasar + Gaspar":
        return "B — Baltasar + Gaspar"
    if "combined_risk_rule" in label:
        return "C — MAGI con Melchor"
    return "D — Variante conservadora"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        output.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(output)


def build_pdf(data: dict[str, Any], charts: dict[str, Path]) -> None:
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )
    story: list[Any] = []
    add_title(story, styles)
    add_section_1(story, styles, data)
    add_section_2(story, styles)
    add_section_3(story, styles)
    add_section_4(story, styles)
    add_section_5(story, styles, data, charts)
    add_section_6(story, styles, data, charts)
    add_section_7(story, styles)
    add_section_8(story, styles)
    add_section_9(story, styles)
    doc.build(story)


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Titulo",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#111827"),
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "Seccion",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15,
            textColor=colors.HexColor("#111827"),
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Cuerpo",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.2,
            alignment=TA_JUSTIFY,
            spaceAfter=5,
        ),
        "note": ParagraphStyle(
            "Nota",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.3,
            leading=10.5,
            textColor=colors.HexColor("#374151"),
            spaceAfter=5,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=6,
        ),
    }


def add_title(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Informe Final CEO-MAGI v3", styles["title"]))
    story.append(Paragraph("Validación, auditoría, costos e integración operativa", styles["note"]))
    story.append(Spacer(1, 0.08 * inch))


def add_section_1(story: list[Any], styles: dict[str, ParagraphStyle], data: dict[str, Any]) -> None:
    ceo_test = data["ceo"]["metrics"]["test"]
    ceo_all = data["ceo"]["metrics"]["all"]
    story.append(Paragraph("Sección 1 — Resumen Ejecutivo", styles["h1"]))
    story.append(Paragraph("MAGI es un sistema de decisión para trading que separa oportunidad, contexto, riesgo y decisión final. Su objetivo no es operar más, sino operar mejor.", styles["body"]))
    story.append(Paragraph("En esta fase se consolidó CEO-MAGI v3 como una política operativa auditable: decide si operar, con qué nivel de agresividad y emite un contrato JSON validado para Bot B.", styles["body"]))
    story.append(Paragraph(f"En test, el sistema alcanzó PF {ceo_test['profit_factor']:.4f}, Avg R {ceo_test['avg_r']:.4f}, drawdown {ceo_test['max_drawdown_r']:.2f}R y win rate {ceo_test['win_rate']:.2%}. En el conjunto offline completo alcanzó PF {ceo_all['profit_factor']:.4f} y Avg R {ceo_all['avg_r']:.4f}.", styles["body"]))
    story.append(Paragraph("Conclusión: MAGI está en fase pre-live viable, con alto potencial, pendiente de validación en entorno real.", styles["body"]))


def add_section_2(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Sección 2 — Problema y Enfoque", styles["h1"]))
    story.append(Paragraph("La mayoría de sistemas de trading falla porque opera demasiado, ignora condiciones de mercado, subestima costos o no controla drawdown. MAGI responde a este problema con una arquitectura modular que filtra señales antes de convertirlas en operaciones.", styles["body"]))
    story.append(Paragraph("El enfoque central es defensivo: abstenerse cuando la calidad no compensa el riesgo. Esto transforma el sistema desde un generador de señales hacia un proceso de decisión.", styles["body"]))


def add_section_3(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Sección 3 — Arquitectura del Sistema", styles["h1"]))
    bullets = [
        "Baltasar: evalúa dirección y propone BUY o SELL.",
        "Gaspar: evalúa contexto y deterioro del mercado.",
        "Melchor: controla riesgo; BLOCK es veto absoluto.",
        "Scoring: prioriza oportunidades con información causal.",
        "CEO-MAGI v3: decide DO_NOTHING o ENTER en modo cauteloso, normal o premium.",
    ]
    for item in bullets:
        story.append(Paragraph(f"- {item}", styles["body"]))
    story.append(Paragraph("La modularidad permite auditar cada contribución y evita depender de una única señal opaca.", styles["body"]))


def add_section_4(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Sección 4 — Metodología de Validación", styles["h1"]))
    story.append(Paragraph("La validación cubre 2020–2026, incluyendo periodos normales, pandemia, inflación y un tramo reciente problemático. Se evaluaron escenarios A/B/C/D para medir el aporte incremental de cada módulo.", styles["body"]))
    story.append(Paragraph("También se eliminó el lookahead: una versión inicial no causal fue reemplazada por una política online que solo decide con datos disponibles al momento de entrada. Finalmente, se probó el sistema con costos bajos, medios y de estrés.", styles["body"]))


def add_section_5(story: list[Any], styles: dict[str, ParagraphStyle], data: dict[str, Any], charts: dict[str, Path]) -> None:
    story.append(Paragraph("Sección 5 — Resultados Interpretados", styles["h1"]))
    story.append(Paragraph("PF mide cuánto gana el sistema por cada unidad perdida. Avg R mide el valor promedio por operación. Drawdown mide la caída máxima acumulada. Win rate mide frecuencia de acierto, pero no basta por sí solo.", styles["body"]))
    add_table(story, ["Escenario", "Trades", "PF", "Avg R", "DD", "WR"], base_rows(data["summary"]))
    story.append(Paragraph("El resultado importante es la combinación: el escenario C mejora PF y reduce drawdown de forma significativa frente a Baltasar solo. Esto indica que Melchor y la selección de riesgo convierten una señal direccional en un sistema más defendible.", styles["body"]))
    add_image(story, charts["base_pf_dd"], "El gráfico muestra que el sistema no solo gana eficiencia; también reduce riesgo acumulado.")
    add_table(story, ["Estrategia", "Trades", "PF", "Avg R", "DD", "WR"], scoring_rows(data["online"]))
    story.append(Paragraph("El scoring no causal no es operativo, pero sirvió para detectar potencial. Al rehacerlo causalmente, el PF baja a niveles realistas y aun así mejora claramente sobre la base.", styles["body"]))


def add_section_6(story: list[Any], styles: dict[str, ParagraphStyle], data: dict[str, Any], charts: dict[str, Path]) -> None:
    story.append(Paragraph("Sección 6 — Robustez del Sistema", styles["h1"]))
    add_table(story, ["Score", "Trades", "PF", "Avg R", "DD", "Total R"], threshold_rows(data["threshold"]))
    story.append(Paragraph("El umbral 0.20 equilibra calidad y volumen. Umbrales más altos elevan PF, pero dejan menos operaciones y aumentan el riesgo de conclusiones frágiles.", styles["body"]))
    add_image(story, charts["threshold_tradeoff"], "El punto 0.20 conserva volumen suficiente sin renunciar a una mejora material de calidad.")
    add_table(story, ["Costos", "Trades", "PF", "Avg R", "DD", "Total R"], cost_rows(data["costs"]))
    story.append(Paragraph("Los costos reducen el edge, como es normal. Lo relevante es que el PF se mantiene por encima de 1 incluso en estrés, aunque 2026Q2 exige monitoreo especial.", styles["body"]))
    add_image(story, charts["costs"], "El gráfico muestra compresión de PF a medida que suben costos, no desaparición total del edge.")
    add_table(story, ["Mes", "Contexto", "Ops", "Wins", "Losses", "WR", "Pips", "Duración"], month_rows(data["stress"], include_context=True))
    story.append(Paragraph("En meses de estrés, MAGI sobrevive 2020-03 y 2022-04. 2026-04 falla en una muestra parcial de solo 3 entradas.", styles["body"]))
    story.append(Paragraph("Nota: 2026-04 contiene datos parciales (~10 días), por lo tanto no debe compararse con meses completos.", styles["note"]))
    add_image(story, charts["stress"], "La caída de 2026-04 funciona como señal de régimen a vigilar antes de live.")


def add_section_7(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Sección 7 — Limitaciones Actuales", styles["h1"]))
    limitations = [
        "Pips derivados de R con SL fijo de 10 pips, no broker real.",
        "Slippage simulado, no medido en MT5.",
        "Spread aproximado desde dataset, no validado broker a broker.",
        "Sin ejecución real ni demo/live todavía.",
        "Sin exit_price en artefactos actuales.",
    ]
    for item in limitations:
        story.append(Paragraph(f"- {item}", styles["body"]))


def add_section_8(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Sección 8 — Estado Operativo", styles["h1"]))
    add_table(story, ["Métrica", "Resultado"], dry_run_rows())
    story.append(Paragraph("El dry-run confirma que Bot B puede leer el contrato JSON sin rechazos ni warnings. Esto habilita una fase shadow/demo, pero no implica autorización para operar capital real.", styles["body"]))


def add_section_9(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Sección 9 — Conclusión Estratégica", styles["h1"]))
    story.append(Paragraph("MAGI no es perfecto ni garantizado. Es un sistema viable en fase pre-live, con alto potencial y pendiente de validación en entorno real. La recomendación es avanzar a demo controlada con monitoreo estricto de ejecución, slippage, latencia, rechazos y comportamiento por régimen.", styles["body"]))


def add_table(story: list[Any], headers: list[str], rows: list[list[Any]]) -> None:
    table = Table([headers] + rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.08 * inch))


def add_image(story: list[Any], path: Path, caption: str) -> None:
    styles = build_styles()
    story.append(KeepTogether([Image(str(path), width=6.5 * inch, height=3.35 * inch), Paragraph(caption, styles["caption"])]))


if __name__ == "__main__":
    main()
