from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DOC_PATH = Path("docs/ceo_magi_v3_full_report.md")
PDF_PATH = Path("reports/ceo_magi_v3_full_report.pdf")

SUMMARY_METRICS = Path("artifacts/magi_validation/summary_metrics.csv")
ONLINE_METRICS = Path("artifacts/magi_validation/online_priority_scoring_metrics.csv")
THRESHOLD_SWEEP = Path("artifacts/magi_validation/online_priority_threshold_sweep.csv")
COST_VALIDATION = Path("artifacts/magi_validation/online_priority_cost_validation.csv")
CEO_SUMMARY = Path("artifacts/ceo_magi_v3/ceo_magi_v3_summary.json")
RANDOM_MONTHS = Path("artifacts/ceo_magi_v3/random_3_months_monthly_summary.csv")
STRESS_MONTHS = Path("artifacts/ceo_magi_v3/stress_months_monthly_summary_full.csv")
AUDIT_OF_AUDIT = Path("artifacts/ceo_magi_v3/audit_of_audit_report.md")
DRY_RUN = Path("artifacts/ceo_magi_v3/bot_b_dry_run_summary.md")
SCENARIO_ROBUSTNESS_IMG = Path("artifacts/magi_validation/scenario_c_robustness_distribution.png")


def main() -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = load_data()
    markdown = build_markdown(data)
    DOC_PATH.write_text(markdown, encoding="utf-8")
    build_pdf(data)

    print(f"md={DOC_PATH}")
    print(f"pdf={PDF_PATH}")


def load_data() -> dict[str, Any]:
    summary = pd.read_csv(SUMMARY_METRICS)
    online = pd.read_csv(ONLINE_METRICS)
    threshold = pd.read_csv(THRESHOLD_SWEEP)
    costs = pd.read_csv(COST_VALIDATION)
    random_months = pd.read_csv(RANDOM_MONTHS)
    stress = pd.read_csv(STRESS_MONTHS)
    ceo = json.loads(CEO_SUMMARY.read_text(encoding="utf-8"))
    return {
        "summary": summary,
        "online": online,
        "threshold": threshold,
        "costs": costs,
        "random_months": random_months,
        "stress": stress,
        "ceo": ceo,
    }


def build_markdown(data: dict[str, Any]) -> str:
    ceo_test = data["ceo"]["metrics"]["test"]
    ceo_all = data["ceo"]["metrics"]["all"]
    lines = [
        "# CEO-MAGI v3 Full Validation, Audit and Integration Report",
        "",
        "## 1. Resumen ejecutivo",
        "",
        "MAGI es un sistema personal de decision en trading compuesto por tres modulos especializados y una capa final de decision. "
        "Baltasar evalua direccion, Gaspar evalua contexto, Melchor controla riesgo, el scoring prioriza oportunidades y CEO-MAGI v3 convierte todo en una instruccion ejecutable.",
        "",
        "En esta fase se formalizo CEO-MAGI v3 como politica offline/causal, se validaron costos de ejecucion, se auditaron meses aleatorios y meses de estres, y se probo el contrato JSON con un dry-run de Bot B sin enviar ordenes reales.",
        "",
        f"Resultado final en test para CEO-MAGI v3: PF `{ceo_test['profit_factor']:.4f}`, Avg R `{ceo_test['avg_r']:.4f}`, Max DD `{ceo_test['max_drawdown_r']:.2f}R`, win rate `{ceo_test['win_rate']:.2%}`, `{ceo_test['enter_decisions']}` entradas aprobadas.",
        f"Resultado global offline: PF `{ceo_all['profit_factor']:.4f}`, Avg R `{ceo_all['avg_r']:.4f}`, Max DD `{ceo_all['max_drawdown_r']:.2f}R`, win rate `{ceo_all['win_rate']:.2%}`.",
        "",
        "## 2. Arquitectura del sistema",
        "",
        "- **Baltasar**: modulo direccional. Propone BUY/SELL cuando detecta oportunidad.",
        "- **Gaspar**: modulo contextual. Penaliza deterioro de mercado y ayuda a reducir agresividad.",
        "- **Melchor**: modulo de riesgo. `BLOCK` es veto absoluto.",
        "- **Scoring**: ranking causal de oportunidades usando confianza, deterioro, riesgo y contexto.",
        "- **CEO-MAGI v3**: capa deterministica final. Emite `DO_NOTHING` o `ENTER` con modo `cautious`, `normal` o `premium`.",
        "",
        "## 3. Validacion base",
        "",
        "La validacion A/B/C/D muestra que MAGI mejora de forma clara al sumar Gaspar y Melchor sobre Baltasar puro. En test, Baltasar solo tenia PF `1.1621`, Avg R `0.0932` y DD `266.14R`; el escenario C subio a PF `2.4330`, Avg R `0.5772` y DD `41.16R`.",
        "",
        base_table(data["summary"]),
        "",
        "## 4. Scoring causal",
        "",
        "Primero se detecto que el scoring no causal usaba una ventana futura de 15 minutos para elegir el mejor candidato. Esa version produjo PF muy alto, pero no era ejecutable en vivo. Luego se rehizo la seleccion en modo estrictamente online/causal: procesando timestamps en orden, ignorando nuevas senales mientras hay trade abierto y calculando score solo con informacion disponible en entrada.",
        "",
        scoring_table(data["online"]),
        "",
        "Conclusion: el PF extremo no causal desaparece, pero el scoring causal conserva edge real frente a la base.",
        "",
        "## 5. Threshold sweep",
        "",
        "Se evaluaron thresholds de score entre `0.00` y `0.50`. El punto `0.20` fue seleccionado como candidato operativo porque mejora PF y Avg R sin destruir demasiado el volumen.",
        "",
        threshold_table(data["threshold"]),
        "",
        "Tradeoff principal: thresholds mas altos suben PF, pero reducen cobertura y cantidad de operaciones. `0.20` mantiene 372 trades en test con PF `4.0284` y Avg R `0.8315` antes de costos.",
        "",
        "## 6. Validacion con costos",
        "",
        "Con `min_score = 0.20`, la validacion con costos confirma que el edge sobrevive en escenarios bajo, medio y stress, aunque 2026Q2 queda debil bajo costos altos.",
        "",
        costs_table(data["costs"]),
        "",
        "Conclusion de robustez: el sistema conserva PF > 1 bajo costos altos/stress en el conjunto test, pero debe monitorear regimenes similares a 2026Q2.",
        "",
        "## 7. Auditoria de meses aleatorios (3 meses)",
        "",
        "Se seleccionaron tres meses aleatorios no continuos: `2020-12`, `2022-01` y `2025-10`. La auditoria uso solo operaciones `ENTER` aprobadas por CEO-MAGI v3 y calculo pips como `realized_R * 10`.",
        "",
        monthly_table(data["random_months"], include_label=False),
        "",
        "Comportamiento operativo: los tres meses fueron positivos, con duraciones promedio entre 1h 51m y 2h 16m. La auditoria posterior confirmo que no habia diferencias aritmeticas ni duplicados.",
        "",
        "## 8. Auditoria de meses de estres (3 meses)",
        "",
        "Meses analizados: `2020-03`, `2022-04`, `2026-04`.",
        "",
        stress_table(data["stress"]),
        "",
        "**Nota importante:** El mes 2026-04 contiene datos parciales (~10 dias) en el dataset, por lo tanto sus resultados no deben considerarse representativos ni comparables con meses completos.",
        "",
        "Comportamiento del sistema: sobrevive en 2020-03 y 2022-04; 2026-04 falla en la muestra parcial con solo 3 entradas, PF `0.6311`, Avg R negativo y `-9.7` pips netos.",
        "",
        "## 9. Auditoria de la auditoria",
        "",
        "La auditoria de consistencia recalculo operaciones, win rate, pips, duracion, duplicados y faltantes. Resultado: `0` diferencias, `0` errores criticos y `0` warnings. No se detecto inflacion matematica ni sesgo fuerte en la muestra aleatoria.",
        "",
        "Limitaciones: `exit_price` no esta disponible; los pips son derivados de R con SL fijo de 10 pips; una muestra de tres meses no reemplaza una validacion walk-forward completa.",
        "",
        "## 10. Dry-run Bot B",
        "",
        "Se genero el contrato JSON de CEO-MAGI v3 y se probo con un dry-run de Bot B. No se tocaron Bot B real, MT5 ni conectores de broker.",
        "",
        dry_run_table(),
        "",
        "Resultado: contrato estructuralmente ejecutable para una fase de shadow/runtime adapter.",
        "",
        "## 11. Limitaciones actuales",
        "",
        "- Pips derivados de R, no pips broker reales.",
        "- Falta ejecucion en tiempo real.",
        "- Falta slippage real medido en MT5.",
        "- Falta validacion demo/live.",
        "- `exit_price` no esta disponible en los artefactos actuales.",
        "- 2026-04 tiene datos parciales y debe tratarse como alerta, no como mes completo.",
        "",
        "## 12. Conclusion final",
        "",
        "MAGI v3 es un sistema viable: mejora significativamente sobre Baltasar puro, mantiene edge cuando se vuelve causal, conserva robustez bajo costos realistas y emite un contrato JSON validado por dry-run de Bot B. Tambien queda claro que el sistema no debe pasar a live sin fase demo controlada, especialmente por la debilidad observada en 2026Q2/2026-04.",
        "",
        "Conclusion operativa: MAGI esta listo para fase demo controlada, con monitoreo estricto y sin riesgo real inicial.",
        "",
        "## 13. Proximos pasos",
        "",
        "1. Implementar runtime adapter entre CEO-MAGI v3 y Bot B en modo shadow.",
        "2. Ejecutar demo sin riesgo con logs completos de decisiones y rechazos.",
        "3. Monitorear en vivo PF, Avg R, DD, slippage real, latencia y regimenes tipo 2026Q2.",
        "4. Agregar captura de `exit_price` y datos broker reales.",
        "5. Evaluar futura expansion multi-par solo despues de estabilidad demo.",
        "",
        "## Artefactos principales",
        "",
        "- `docs/ceo_magi_v3_decision_logic.md`",
        "- `artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv`",
        "- `artifacts/ceo_magi_v3/ceo_magi_v3_decisions.jsonl`",
        "- `artifacts/ceo_magi_v3/bot_b_dry_run_summary.md`",
        "- `artifacts/ceo_magi_v3/random_3_months_trade_audit.md`",
        "- `artifacts/ceo_magi_v3/stress_months_trade_audit_full.md`",
        "- `reports/ceo_magi_v3_full_report.pdf`",
        "",
    ]
    return "\n".join(lines)


def base_table(df: pd.DataFrame) -> str:
    rows = df[(df["split"].eq("test")) & (df["direction"].eq("ALL"))].copy()
    return markdown_table(
        ["Escenario", "Trades", "Coverage", "PF", "Avg R", "Max DD", "Win rate"],
        [
            [
                row["scenario_label"],
                int(row["trades"]),
                pct(row["coverage"]),
                f4(row["profit_factor"]),
                f4(row["avg_r"]),
                f"{row['max_drawdown_r']:.2f}",
                pct(row["win_rate"]),
            ]
            for _, row in rows.iterrows()
        ],
    )


def scoring_table(df: pd.DataFrame) -> str:
    rows = df[(df["segment_type"].eq("split")) & (df["segment"].eq("test"))].copy()
    return markdown_table(
        ["Estrategia", "Trades", "Coverage", "PF", "Avg R", "Max DD", "Win rate"],
        [
            [
                row["strategy"],
                int(row["trades"]),
                pct(row["coverage"]),
                f4(row["profit_factor"]),
                f4(row["avg_r"]),
                f"{row['max_drawdown_r']:.2f}",
                pct(row["win_rate"]),
            ]
            for _, row in rows.iterrows()
        ],
    )


def threshold_table(df: pd.DataFrame) -> str:
    return markdown_table(
        ["min_score", "Trades", "Coverage", "PF", "Avg R", "Max DD", "Total R", "2026Q2 PF"],
        [
            [
                f"{row['min_score']:.2f}",
                int(row["trades"]),
                pct(row["coverage"]),
                f4(row["profit_factor"]),
                f4(row["avg_r"]),
                f"{row['max_drawdown_r']:.2f}",
                f"{row['total_r']:.2f}",
                f4(row["q2_profit_factor"]),
            ]
            for _, row in df.iterrows()
        ],
    )


def costs_table(df: pd.DataFrame) -> str:
    rows = df[(df["segment_type"].eq("test")) & (df["segment"].eq("ALL"))].copy()
    rows = rows[rows["cost_scenario"].isin(["comparison_score_0_20_no_costs", "low_costs", "medium_costs", "high_costs_stress"])]
    return markdown_table(
        ["Escenario", "Trades", "PF", "Avg R", "Max DD", "Total R", "Win rate"],
        [
            [
                row["label"],
                int(row["trades"]),
                f4(row["profit_factor"]),
                f4(row["avg_r"]),
                f"{row['max_drawdown_r']:.2f}",
                f"{row['total_r']:.2f}",
                pct(row["win_rate"]),
            ]
            for _, row in rows.iterrows()
        ],
    )


def monthly_table(df: pd.DataFrame, include_label: bool) -> str:
    headers = ["Mes", "Ops", "Ganadoras", "Perdedoras", "Win rate", "Pips netos", "Duracion prom."]
    if include_label:
        headers.insert(1, "Contexto")
    rows = []
    for _, row in df.iterrows():
        item = [
            row["month"],
            int(row["trades_executed"]),
            int(row["winning_trades"]),
            int(row["losing_trades"]),
            pct(row["win_rate"]),
            f"{row['net_pips_month']:.1f}",
            row["avg_duration"],
        ]
        if include_label:
            item.insert(1, row["stress_label"])
        rows.append(item)
    return markdown_table(headers, rows)


def stress_table(df: pd.DataFrame) -> str:
    return monthly_table(df, include_label=True)


def dry_run_table() -> str:
    return markdown_table(
        ["Metrica", "Resultado"],
        [
            ["Decisiones leidas", "6,539"],
            ["ACK_EXECUTABLE", "3,346"],
            ["ACK_DO_NOTHING", "3,193"],
            ["Rechazos", "0"],
            ["Warnings contractuales", "0"],
            ["Ordenes enviadas", "0"],
        ],
    )


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(out)


def pct(value: Any) -> str:
    return f"{float(value):.2%}"


def f4(value: Any) -> str:
    value = float(value)
    if value == float("inf"):
        return "inf"
    return f"{value:.4f}"


def build_pdf(data: dict[str, Any]) -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#1F2937"))
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=10, textColor=colors.HexColor("#111827"))
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=10)

    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch, topMargin=0.55 * inch, bottomMargin=0.55 * inch)
    story = [
        Paragraph("CEO-MAGI v3 Full Validation, Audit and Integration Report", title),
        Spacer(1, 0.12 * inch),
        Paragraph("Executive summary", h1),
    ]
    ceo_test = data["ceo"]["metrics"]["test"]
    story.append(Paragraph(f"CEO-MAGI v3 closes as an offline causal decision policy with test PF {ceo_test['profit_factor']:.4f}, Avg R {ceo_test['avg_r']:.4f}, Max DD {ceo_test['max_drawdown_r']:.2f}R and win rate {ceo_test['win_rate']:.2%}. The Bot B dry-run produced 0 rejects and 0 warnings.", body))
    story.append(Spacer(1, 0.08 * inch))
    add_pdf_table(story, "Base validation A/B/C/D - test", ["Scenario", "Trades", "PF", "Avg R", "DD", "WR"], pdf_base_rows(data["summary"]), h1)
    add_pdf_table(story, "Scoring causal comparison - test", ["Strategy", "Trades", "PF", "Avg R", "DD", "WR"], pdf_scoring_rows(data["online"]), h1)
    add_pdf_table(story, "Threshold sweep - test", ["Score", "Trades", "PF", "Avg R", "DD", "Total R"], pdf_threshold_rows(data["threshold"]), h1)
    story.append(PageBreak())
    add_pdf_table(story, "Cost validation for min_score 0.20", ["Scenario", "Trades", "PF", "Avg R", "DD", "Total R"], pdf_cost_rows(data["costs"]), h1)
    add_pdf_table(story, "Random 3-month operational audit", ["Month", "Ops", "Wins", "Losses", "WR", "Net pips", "Avg dur"], pdf_month_rows(data["random_months"]), h1)
    add_pdf_table(story, "Stress month operational audit", ["Month", "Ops", "Wins", "Losses", "WR", "Net pips", "Avg dur"], pdf_month_rows(data["stress"]), h1)
    story.append(Paragraph("Important note: 2026-04 contains partial data (~10 days) in the dataset, so its results should not be treated as representative or comparable with full months.", small))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("Bot B dry-run", h1))
    story.append(Paragraph("JSON contract validation read 6,539 decisions: 3,346 ACK_EXECUTABLE, 3,193 ACK_DO_NOTHING, 0 rejects, 0 contractual warnings and 0 orders sent.", body))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("Conclusion", h1))
    story.append(Paragraph("MAGI v3 is viable and ready for a controlled demo/shadow phase. Current limits remain broker-real pips, real-time execution, MT5 slippage measurement and demo/live validation.", body))
    if SCENARIO_ROBUSTNESS_IMG.exists():
        story.append(PageBreak())
        story.append(Paragraph("Existing robustness distribution", h1))
        story.append(Image(str(SCENARIO_ROBUSTNESS_IMG), width=6.5 * inch, height=3.4 * inch))
    doc.build(story)


def add_pdf_table(story: list[Any], heading: str, headers: list[str], rows: list[list[Any]], h1: ParagraphStyle) -> None:
    story.append(Paragraph(heading, h1))
    table = Table([headers] + rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.1 * inch))


def pdf_base_rows(df: pd.DataFrame) -> list[list[Any]]:
    rows = df[(df["split"].eq("test")) & (df["direction"].eq("ALL"))]
    return [[r["scenario"].split("_")[0], int(r["trades"]), f4(r["profit_factor"]), f4(r["avg_r"]), f"{r['max_drawdown_r']:.2f}", pct(r["win_rate"])] for _, r in rows.iterrows()]


def pdf_scoring_rows(df: pd.DataFrame) -> list[list[Any]]:
    rows = df[(df["segment_type"].eq("split")) & (df["segment"].eq("test"))]
    return [[r["strategy"].replace("_", " "), int(r["trades"]), f4(r["profit_factor"]), f4(r["avg_r"]), f"{r['max_drawdown_r']:.2f}", pct(r["win_rate"])] for _, r in rows.iterrows()]


def pdf_threshold_rows(df: pd.DataFrame) -> list[list[Any]]:
    return [[f"{r['min_score']:.2f}", int(r["trades"]), f4(r["profit_factor"]), f4(r["avg_r"]), f"{r['max_drawdown_r']:.2f}", f"{r['total_r']:.1f}"] for _, r in df.iterrows()]


def pdf_cost_rows(df: pd.DataFrame) -> list[list[Any]]:
    rows = df[(df["segment_type"].eq("test")) & (df["segment"].eq("ALL"))]
    rows = rows[rows["cost_scenario"].isin(["comparison_score_0_20_no_costs", "low_costs", "medium_costs", "high_costs_stress"])]
    return [[r["label"], int(r["trades"]), f4(r["profit_factor"]), f4(r["avg_r"]), f"{r['max_drawdown_r']:.2f}", f"{r['total_r']:.1f}"] for _, r in rows.iterrows()]


def pdf_month_rows(df: pd.DataFrame) -> list[list[Any]]:
    return [[r["month"], int(r["trades_executed"]), int(r["winning_trades"]), int(r["losing_trades"]), pct(r["win_rate"]), f"{r['net_pips_month']:.1f}", r["avg_duration"]] for _, r in df.iterrows()]


if __name__ == "__main__":
    main()
