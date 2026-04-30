from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "output" / "ceo_training" / "20260429T141153Z_magi_v01_phase2"
REPORTS_DIR = ROOT / "reports"
ASSETS_DIR = REPORTS_DIR / "magi_ceo_v2_and_mages_retraining_assets"
MD_PATH = REPORTS_DIR / "magi_ceo_v2_and_mages_retraining_report.md"
PDF_PATH = REPORTS_DIR / "magi_ceo_v2_and_mages_retraining_report.pdf"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def pct(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def num(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return f"{value:,}"
    return f"{float(value):,.{digits}f}"


def safe_get(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = d
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def save_bar_chart(path: Path, labels: list[str], values: list[float], title: str, ylabel: str, color: str = "#2f6f73") -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.bar(labels, values, color=color)
    ax.set_title(title, fontsize=12, pad=10)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    for idx, value in enumerate(values):
        label = f"{value:,.0f}" if max(values) > 100 else f"{value:.1f}%"
        ax.text(idx, value, label, ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def build_charts(summary: dict[str, Any], model_metrics: dict[str, Any], wf: dict[str, Any], r_metrics: dict[str, Any]) -> dict[str, Path]:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    charts: dict[str, Path] = {}

    target_dist = summary["target_distribution"]
    charts["labels"] = ASSETS_DIR / "tradeable_label_distribution.png"
    save_bar_chart(
        charts["labels"],
        ["DO_NOTHING", "ENTER_BUY", "ENTER_SELL"],
        [target_dist.get("DO_NOTHING", 0), target_dist.get("ENTER_BUY", 0), target_dist.get("ENTER_SELL", 0)],
        "Distribucion del target tradeable",
        "Filas",
        "#315f72",
    )

    thresholds = ["0.50", "0.60", "0.70"]
    fig, ax1 = plt.subplots(figsize=(7.2, 3.4))
    val_precision = [safe_get(model_metrics, "threshold_metrics", "validation", t, "trade_precision", default=0) * 100 for t in thresholds]
    test_precision = [safe_get(model_metrics, "threshold_metrics", "test", t, "trade_precision", default=0) * 100 for t in thresholds]
    val_coverage = [safe_get(model_metrics, "threshold_metrics", "validation", t, "coverage", default=0) * 100 for t in thresholds]
    test_coverage = [safe_get(model_metrics, "threshold_metrics", "test", t, "coverage", default=0) * 100 for t in thresholds]
    x = range(len(thresholds))
    ax1.plot(x, val_precision, marker="o", label="Precision validation", color="#276749")
    ax1.plot(x, test_precision, marker="o", label="Precision test", color="#1f4e79")
    ax1.set_xticks(list(x), thresholds)
    ax1.set_ylabel("Trade precision (%)")
    ax1.set_title("CEO v2: precision por umbral")
    ax1.grid(axis="y", alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(x, val_coverage, marker="s", linestyle="--", label="Coverage validation", color="#b7791f")
    ax2.plot(x, test_coverage, marker="s", linestyle="--", label="Coverage test", color="#9b2c2c")
    ax2.set_ylabel("Coverage (%)")
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper right", fontsize=8)
    fig.tight_layout()
    charts["thresholds"] = ASSETS_DIR / "threshold_precision_coverage.png"
    fig.savefig(charts["thresholds"], dpi=160)
    plt.close(fig)

    yearly = wf["yearly"]
    charts["yearly"] = ASSETS_DIR / "walk_forward_yearly_precision.png"
    save_bar_chart(
        charts["yearly"],
        [str(row["period"]) for row in yearly],
        [row["trade_precision"] * 100 for row in yearly],
        "Walk-forward anual: precision de trades",
        "Precision (%)",
        "#4a5568",
    )

    rr_rows = r_metrics["by_rr"]
    rr_profiles = ["rr_1_1", "rr_1_1_5", "rr_1_2"]
    rr_labels = ["1:1", "1:1.5", "1:2"]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    width = 0.35
    xs = list(range(len(rr_profiles)))
    conservative = [next(r for r in rr_rows if r["rr_profile"] == rr and r["scenario"] == "conservative")["avg_r"] for rr in rr_profiles]
    optimistic = [next(r for r in rr_rows if r["rr_profile"] == rr and r["scenario"] == "optimistic")["avg_r"] for rr in rr_profiles]
    ax.bar([i - width / 2 for i in xs], conservative, width, label="Conservative", color="#9b2c2c")
    ax.bar([i + width / 2 for i in xs], optimistic, width, label="Optimistic", color="#276749")
    ax.axhline(0, color="#222222", linewidth=0.8)
    ax.set_xticks(xs, rr_labels)
    ax.set_ylabel("Avg R")
    ax.set_title("Simulacion proxy: avg R por perfil RR")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    charts["rr_avg"] = ASSETS_DIR / "rr_avg_r_comparison.png"
    fig.savefig(charts["rr_avg"], dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    dd_conservative = [next(r for r in rr_rows if r["rr_profile"] == rr and r["scenario"] == "conservative")["max_drawdown_r"] for rr in rr_profiles]
    dd_optimistic = [next(r for r in rr_rows if r["rr_profile"] == rr and r["scenario"] == "optimistic")["max_drawdown_r"] for rr in rr_profiles]
    ax.bar([i - width / 2 for i in xs], dd_conservative, width, label="Conservative", color="#9b2c2c")
    ax.bar([i + width / 2 for i in xs], dd_optimistic, width, label="Optimistic", color="#276749")
    ax.set_xticks(xs, rr_labels)
    ax.set_ylabel("Max drawdown (R)")
    ax.set_title("Drawdown maximo proxy por perfil RR")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    charts["rr_drawdown"] = ASSETS_DIR / "rr_drawdown_comparison.png"
    fig.savefig(charts["rr_drawdown"], dpi=160)
    plt.close(fig)

    return charts


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(out)


def build_markdown(
    summary: dict[str, Any],
    model_metrics: dict[str, Any],
    policy_metrics: dict[str, Any],
    wf: dict[str, Any],
    r_metrics: dict[str, Any],
    audit: dict[str, Any],
    charts: dict[str, Path],
) -> None:
    temporal_start = summary["temporal_range"].get("min_timestamp") or summary["temporal_range"].get("start")
    temporal_end = summary["temporal_range"].get("max_timestamp") or summary["temporal_range"].get("end")
    target_rows = [[k, f"{v:,}", pct(v / summary["rows"])] for k, v in summary["target_distribution"].items()]
    threshold_rows: list[list[str]] = []
    for split in ["validation", "test"]:
        for th in ["0.60", "0.70"]:
            m = model_metrics["threshold_metrics"][split][th]
            threshold_rows.append([split, th, num(m["trades_taken"], 0), pct(m["coverage"]), pct(m["trade_precision"]), pct(m.get("buy_precision")), pct(m.get("sell_precision"))])

    policy_rows: list[list[str]] = []
    for split in ["validation", "test"]:
        pure = policy_metrics[split]["threshold_070_pure"]
        core = policy_metrics[split]["conservative_core"]
        for name, m in [("threshold_070_pure", pure), ("conservative_core", core)]:
            policy_rows.append([split, name, num(m["trades_taken"], 0), pct(m["coverage"]), pct(m["trade_precision"]), pct(m.get("buy_precision")), pct(m.get("sell_precision"))])

    wf_rows = [[str(r["period"]), num(r["trades_taken"], 0), pct(r["coverage"]), pct(r["trade_precision"])] for r in wf["yearly"]]
    rr_rows = [[
        r["rr_profile"].replace("rr_1_1_5", "1:1.5").replace("rr_1_1", "1:1").replace("rr_1_2", "1:2"),
        r["scenario"],
        num(r["trades"], 0),
        pct(r["win_rate"]),
        num(r["avg_r"], 4),
        num(r["total_r"], 2),
        num(r["profit_factor"], 4),
        num(r["max_drawdown_r"], 2),
        num(r["ambiguous_trades"], 0),
    ] for r in r_metrics["by_rr"]]

    monthly_conservative_rr2 = [r for r in r_metrics["by_month"] if r["rr_profile"] == "rr_1_2" and r["scenario"] == "conservative"]
    worst_months = sorted(monthly_conservative_rr2, key=lambda r: r["total_r"])[:5]
    best_months = sorted(monthly_conservative_rr2, key=lambda r: r["total_r"], reverse=True)[:5]
    month_rows = [[r["period"], num(r["trades"], 0), num(r["total_r"], 2), num(r["avg_r"], 4), num(r["max_drawdown_r"], 2)] for r in worst_months + best_months]

    rel = lambda p: str(p.relative_to(ROOT)).replace("\\", "/")
    content = f"""# Informe ejecutivo MAGI: CEO v2 y reentrenamiento de magos

Fecha: 2026-04-29  
Alcance: estado actual de CEO-MAGI v2, simulacion operativa proxy y plan tecnico para reentrenar Melchor, Baltasar y Gaspar.

## 1. Resumen ejecutivo

MAGI ya cuenta con una base experimental completa para CEO-MAGI: dataset tabular, splits temporales, baselines sin ML, CEO v1, auditoria de labels, CEO v2 con target tradeable, analisis por segmentos, auditoria de politica, walk-forward y simulacion proxy R/SL/TP.

El hallazgo central es claro: CEO v2 aprendio abstencion contextual. La politica `conservative_core` redujo cobertura y mejoro la precision del set test frente a Baltasar y CEO v1 cuando se mide contra el target tradeable. Sin embargo, la simulacion proxy en R no valida rentabilidad operativa bajo el escenario conservador. Por tanto, CEO v2 no esta listo para demo operativa.

La siguiente fase no debe empezar por mas ML. Debe empezar por mejorar la simulacion con first-touch intrabar, construir labels RR 1:2 mas institucionales y despues reentrenar magos v2.

## 2. Que se construyo

- Dataset CEO final: {summary['rows']:,} registros entre {temporal_start} y {temporal_end}.
- Pipeline tabular final con senales, contexto, regimen, votos, confianza y outcomes H12/H48/H96/H288.
- Baselines operativos sin ML: `always_do_nothing`, `baltasar_only`, `gaspar_only`, `baltasar_gaspar_aligned`, `high_confidence_alignment`.
- CEO v1 con RandomForest: replico `baltasar_only`, lo que confirmo dependencia del target original.
- Auditoria de labels: midio acoplamiento con Baltasar y disponibilidad real de campos MFE/MAE/return.
- CEO v2 tradeable: target conservador `ceo_label_h48_tradeable`.
- Segment analysis, policy audit, walk-forward y simulacion proxy con RR 1:1, 1:1.5 y 1:2.

## 3. Hallazgos principales

- CEO v1 no aprendio una funcion CEO real: copio la regla de Baltasar porque `ceo_label_h48` estaba acoplado a `baltasar_signal`.
- La dependencia label vs Baltasar fue alta: mutual information {audit['dependency_label_vs_baltasar']['mutual_information']:.4f}; accuracy de una regla simple basada solo en Baltasar {pct(audit['dependency_label_vs_baltasar']['simple_baltasar_rule_accuracy'])}.
- El target tradeable hizo que CEO v2 filtrara operaciones y aprendiera abstencion contextual.
- `conservative_core` mejoro precision en test a cambio de menor cobertura.
- La zona `daily_range_position > 0.85` debe bloquearse: aparecio como segmento de precision muy pobre.
- RR 1:2 fue el perfil proxy mas prometedor, pero aun negativo en escenario conservador.
- La diferencia entre escenarios conservative y optimistic demuestra que falta first-touch intrabar.

## 4. Resultados clave

### Distribucion del target tradeable

![Distribucion target tradeable]({rel(charts['labels'])})

{md_table(["Clase", "Filas", "Peso"], target_rows)}

### CEO v2 por threshold

![Precision por threshold]({rel(charts['thresholds'])})

{md_table(["Split", "Threshold", "Trades", "Coverage", "Trade precision", "BUY precision", "SELL precision"], threshold_rows)}

### Policy audit

{md_table(["Split", "Politica", "Trades", "Coverage", "Trade precision", "BUY precision", "SELL precision"], policy_rows)}

### Walk-forward anual

![Walk-forward anual]({rel(charts['yearly'])})

{md_table(["Ano", "Trades", "Coverage", "Trade precision"], wf_rows)}

### Simulacion proxy R/SL/TP

![Avg R por RR]({rel(charts['rr_avg'])})

![Drawdown por RR]({rel(charts['rr_drawdown'])})

{md_table(["RR", "Escenario", "Trades", "Win rate", "Avg R", "Total R", "PF", "Max DD R", "Ambiguous"], rr_rows)}

### Meses mas relevantes en RR 1:2 conservative

{md_table(["Mes", "Trades", "Total R", "Avg R", "Max DD R"], month_rows)}

## 5. Diagnostico tecnico

CEO v2 no debe pasar a demo operativa todavia. El sistema muestra capacidad para filtrar senales, pero no demuestra edge operativo validado. La precision de label mejoro; la rentabilidad proxy conservadora no.

La brecha entre conservative y optimistic no es un detalle menor: significa que muchas operaciones pudieron tocar TP y SL dentro del horizonte H48, pero no sabemos cual ocurrio primero. Sin orden intrabar, el resultado real no se puede afirmar.

La prioridad tecnica es mejorar la verdad de simulacion. Luego se deben construir labels de entrenamiento que optimicen EV, R, drawdown y ambiguedad, no accuracy direccional.

## 6. Plan de accion

1. Enriquecer simulador con first-touch intrabar M1/M5 si existen datos.
2. Construir labels RR 1:2 con costo, spread, MFE, MAE y orden de toque.
3. Reentrenar Baltasar v2 para direccion operable.
4. Reentrenar Gaspar v2 para calidad de contexto.
5. Reentrenar Melchor v2 para riesgo operativo.
6. Entrenar CEO v3 solo con magos v2.
7. Ejecutar backtest institucional con no solapamiento, costos, slippage, sizing y equity curve.

## 7. Baltasar v2

Objetivo: mejorar senal direccional operable, no solo direccion futura. El target sugerido es `tradeable_direction_rr2` o `expected_R_proxy`. Debe usar MFE/MAE, `future_return_pips`, spread y first-touch cuando este disponible.

Metricas de aceptacion: precision de trades, avg R proxy, profit factor, drawdown y estabilidad temporal. Baltasar v2 debe dejar de optimizar labels de direccion simple.

## 8. Gaspar v2

Objetivo: clasificar contexto operable/no operable. Gaspar no debe votar direccion; debe votar calidad de contexto.

Targets sugeridos: `context_quality_rr2` y `ambiguity_risk`. Features clave: session, bucket ATR, posicion en rango diario, estructura H4/D1, alineacion, volatilidad y regimen.

## 9. Melchor v2

Objetivo: riesgo operativo. Salida esperada: `APPROVE`, `CAUTION`, `BLOCK`.

Target sugerido: `risk_block_rr2`. Debe aprender bloqueos por spread, MAE, drawdown, ambiguedad TP/SL, rangos extremos y condiciones donde operar destruye EV.

## 10. CEO v3

CEO v3 debe entrenarse despues de magos v2. Input: votos nuevos, probabilidades y contexto. Output: `ENTER_BUY`, `ENTER_SELL`, `DO_NOTHING`.

El objetivo de CEO v3 no sera accuracy. Sera EV positivo, cobertura razonable, drawdown controlado y estabilidad fuera de muestra.

## 11. Riesgos y controles

- Sobreajuste por segmentos: controlar con walk-forward y ventanas futuras.
- Leakage: prohibir outcomes futuros como features.
- Meses malos: medir dispersion mensual y bloquear contextos si corresponde.
- Dependencia de proxy: no declarar rentabilidad hasta tener first-touch intrabar.
- Labels mal disenados: validar que no repliquen a Baltasar ni a una regla trivial.
- Falsas mejoras: comparar siempre contra `baltasar_only`, CEO v1 y `always_do_nothing`.

## 12. Proxima decision tecnica

La recomendacion es mejorar first-touch intrabar antes de reentrenar formalmente a los magos. Si se decide avanzar en paralelo, el primer mago debe ser Baltasar v2 con target RR 1:2, porque la direccion operable es la base para que Gaspar y Melchor aprendan contexto y riesgo con mejor verdad de mercado.

Scripts reutilizables: `build_ceo_v2_tradeable_dataset.py`, `train_ceo_v2_tradeable_model.py`, `evaluate_ceo_v2_policy.py`, `walk_forward_ceo_v2_policy.py`, `simulate_ceo_v2_r_trades.py`.

Archivos nuevos recomendados: `build_rr2_first_touch_labels.py`, `train_baltasar_v2_rr2.py`, `train_gaspar_v2_context.py`, `train_melchor_v2_risk.py`, `train_ceo_v3.py`, `backtest_magi_v3_institutional.py`.

## Conclusion

MAGI tiene una base tecnica solida para continuar, pero el resultado honesto es que CEO v2 todavia no demuestra rentabilidad operativa. La senal existe y la abstencion contextual mejoro, pero falta transformar la simulacion proxy en una verdad operativa mas confiable. El siguiente paso correcto es first-touch intrabar y labels RR 1:2 antes de CEO v3.
"""
    MD_PATH.write_text(content, encoding="utf-8")


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("&", "&amp;"), style)


def bullet_list(items: list[str], styles: dict[str, ParagraphStyle]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item, styles["body"]), leftIndent=8) for item in items],
        bulletType="bullet",
        leftIndent=12,
        bulletFontSize=7,
    )


def pdf_table(headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> Table:
    data = [headers] + rows
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243746")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d8dee4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fa")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def chart(path: Path, width: float = 6.6 * inch) -> Image:
    img = Image(str(path))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = width
    img.drawHeight = width * ratio
    return img


def build_pdf(
    summary: dict[str, Any],
    model_metrics: dict[str, Any],
    policy_metrics: dict[str, Any],
    wf: dict[str, Any],
    r_metrics: dict[str, Any],
    audit: dict[str, Any],
    charts: dict[str, Path],
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.42 * inch,
        bottomMargin=0.42 * inch,
    )

    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("Title", parent=base["Title"], fontSize=18, leading=22, alignment=TA_LEFT, spaceAfter=8, textColor=colors.HexColor("#17202a")),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontSize=12.5, leading=15, spaceBefore=8, spaceAfter=5, textColor=colors.HexColor("#243746")),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=4, textColor=colors.HexColor("#315f72")),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontSize=8.6, leading=11.2, spaceAfter=4),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontSize=7.5, leading=9.5, spaceAfter=3),
        "callout": ParagraphStyle("Callout", parent=base["BodyText"], fontSize=9, leading=12, spaceAfter=5, leftIndent=6, borderColor=colors.HexColor("#d0d7de"), borderWidth=0.5, borderPadding=6, backColor=colors.HexColor("#f6f8fa")),
    }

    def on_page(canvas, doc_obj):
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawRightString(7.95 * inch, 0.22 * inch, f"Pagina {doc_obj.page}")

    temporal_start = summary["temporal_range"].get("min_timestamp") or summary["temporal_range"].get("start")
    temporal_end = summary["temporal_range"].get("max_timestamp") or summary["temporal_range"].get("end")
    target_rows = [[k, f"{v:,}", pct(v / summary["rows"])] for k, v in summary["target_distribution"].items()]
    threshold_rows = []
    for split in ["validation", "test"]:
        for th in ["0.60", "0.70"]:
            m = model_metrics["threshold_metrics"][split][th]
            threshold_rows.append([split, th, num(m["trades_taken"], 0), pct(m["coverage"]), pct(m["trade_precision"]), pct(m.get("buy_precision")), pct(m.get("sell_precision"))])
    policy_rows = []
    for split in ["validation", "test"]:
        for name in ["threshold_070_pure", "conservative_core"]:
            m = policy_metrics[split][name]
            policy_rows.append([split, name.replace("_", " "), num(m["trades_taken"], 0), pct(m["coverage"]), pct(m["trade_precision"]), pct(m.get("buy_precision")), pct(m.get("sell_precision"))])
    wf_rows = [[str(r["period"]), num(r["trades_taken"], 0), pct(r["coverage"]), pct(r["trade_precision"])] for r in wf["yearly"]]
    rr_rows = [[
        r["rr_profile"].replace("rr_1_1_5", "1:1.5").replace("rr_1_1", "1:1").replace("rr_1_2", "1:2"),
        r["scenario"],
        num(r["trades"], 0),
        pct(r["win_rate"]),
        num(r["avg_r"], 4),
        num(r["total_r"], 0),
        num(r["profit_factor"], 3),
        num(r["max_drawdown_r"], 0),
        num(r["ambiguous_trades"], 0),
    ] for r in r_metrics["by_rr"]]
    monthly_conservative_rr2 = [r for r in r_metrics["by_month"] if r["rr_profile"] == "rr_1_2" and r["scenario"] == "conservative"]
    worst = sorted(monthly_conservative_rr2, key=lambda r: r["total_r"])[:5]
    best = sorted(monthly_conservative_rr2, key=lambda r: r["total_r"], reverse=True)[:5]
    month_rows = [[r["period"], num(r["trades"], 0), num(r["total_r"], 1), num(r["avg_r"], 4), num(r["max_drawdown_r"], 1)] for r in worst + best]

    story: list[Any] = []
    story.append(p("Informe ejecutivo MAGI: CEO v2 y reentrenamiento de magos", styles["title"]))
    story.append(p("Fecha: 2026-04-29 | Sin portada | Alcance: estado actual, hallazgos, simulacion proxy y plan de accion.", styles["small"]))
    story.append(p("1. Resumen ejecutivo", styles["h1"]))
    story.append(p("MAGI ya cuenta con una base experimental completa para CEO-MAGI: dataset tabular, splits temporales, baselines, CEO v1, auditoria de labels, CEO v2 tradeable, analisis por segmentos, policy audit, walk-forward y simulacion proxy R/SL/TP.", styles["body"]))
    story.append(p("El hallazgo central es claro: CEO v2 aprendio abstencion contextual. La politica conservative_core redujo cobertura y mejoro precision en test frente a Baltasar y CEO v1 cuando se mide contra el target tradeable. Sin embargo, la simulacion proxy en R no valida rentabilidad operativa bajo el escenario conservador.", styles["callout"]))
    story.append(p("La siguiente fase debe priorizar first-touch intrabar, labels RR 1:2 y reentrenamiento de magos v2 antes de entrenar CEO v3.", styles["body"]))

    story.append(p("2. Que se construyo", styles["h1"]))
    story.append(bullet_list([
        f"Dataset CEO final: {summary['rows']:,} registros entre {temporal_start} y {temporal_end}.",
        "Pipeline tabular final con senales, contexto, regimen, votos, confianza y outcomes H12/H48/H96/H288.",
        "Baselines sin ML, CEO v1, auditoria de labels, CEO v2 tradeable, segment analysis, policy audit, walk-forward y simulacion proxy R.",
    ], styles))

    story.append(p("3. Hallazgos principales", styles["h1"]))
    story.append(bullet_list([
        "CEO v1 copio a Baltasar; el target original estaba demasiado acoplado.",
        f"Mutual information label vs Baltasar: {audit['dependency_label_vs_baltasar']['mutual_information']:.4f}; accuracy de regla Baltasar: {pct(audit['dependency_label_vs_baltasar']['simple_baltasar_rule_accuracy'])}.",
        "El target tradeable permitio que CEO v2 filtrara mas y operara menos.",
        "daily_range_position > 0.85 debe bloquearse por comportamiento pobre.",
        "RR 1:2 fue el perfil proxy mas prometedor, pero sigue negativo bajo escenario conservative.",
    ], styles))

    story.append(PageBreak())
    story.append(p("4. Resultados clave", styles["h1"]))
    story.append(p("Distribucion del target tradeable", styles["h2"]))
    story.append(KeepTogether([chart(charts["labels"], 6.1 * inch), pdf_table(["Clase", "Filas", "Peso"], target_rows, [2.0 * inch, 1.4 * inch, 1.0 * inch])]))
    story.append(Spacer(1, 5))
    story.append(p("CEO v2 por threshold", styles["h2"]))
    story.append(KeepTogether([chart(charts["thresholds"], 6.1 * inch), pdf_table(["Split", "Threshold", "Trades", "Coverage", "Trade precision", "BUY precision", "SELL precision"], threshold_rows)]))

    story.append(PageBreak())
    story.append(p("Policy audit y walk-forward", styles["h1"]))
    story.append(pdf_table(["Split", "Politica", "Trades", "Coverage", "Trade precision", "BUY precision", "SELL precision"], policy_rows))
    story.append(Spacer(1, 6))
    story.append(chart(charts["yearly"], 6.1 * inch))
    story.append(pdf_table(["Ano", "Trades", "Coverage", "Trade precision"], wf_rows, [1.0 * inch, 1.1 * inch, 1.1 * inch, 1.3 * inch]))

    story.append(PageBreak())
    story.append(p("Simulacion proxy R/SL/TP", styles["h1"]))
    story.append(p("Esto es una simulacion proxy. No hay orden intrabar real, por lo que las operaciones donde pudieron tocarse TP y SL se separan en escenario conservative y optimistic.", styles["body"]))
    story.append(chart(charts["rr_avg"], 6.1 * inch))
    story.append(chart(charts["rr_drawdown"], 6.1 * inch))
    story.append(pdf_table(["RR", "Escenario", "Trades", "Win", "Avg R", "Total R", "PF", "Max DD", "Ambig."], rr_rows))
    story.append(Spacer(1, 4))
    story.append(p("Meses mas relevantes en RR 1:2 conservative", styles["h2"]))
    story.append(pdf_table(["Mes", "Trades", "Total R", "Avg R", "Max DD"], month_rows))

    story.append(PageBreak())
    story.append(p("5. Diagnostico tecnico", styles["h1"]))
    story.append(p("CEO v2 no debe pasar a demo operativa. El sistema muestra capacidad para filtrar senales, pero no demuestra edge operativo validado. La precision de label mejoro; la rentabilidad proxy conservadora no.", styles["body"]))
    story.append(p("La brecha conservative vs optimistic significa que muchas operaciones pudieron tocar TP y SL dentro del horizonte H48, pero no sabemos cual ocurrio primero. Sin first-touch intrabar, el resultado real no se puede afirmar.", styles["body"]))
    story.append(p("6. Plan de accion", styles["h1"]))
    story.append(bullet_list([
        "Enriquecer simulador con first-touch intrabar M1/M5 si existen datos.",
        "Construir labels RR 1:2 con costos, spread, MFE, MAE y orden de toque.",
        "Reentrenar Baltasar v2, Gaspar v2 y Melchor v2 con objetivos separados.",
        "Entrenar CEO v3 solo despues de magos v2.",
        "Ejecutar backtest institucional con no solapamiento, costos, slippage, sizing y equity curve.",
    ], styles))

    story.append(p("7. Baltasar v2", styles["h1"]))
    story.append(p("Objetivo: direccion operable, no solo direccion futura. Target sugerido: tradeable_direction_rr2 o expected_R_proxy. Metricas: precision de trades, avg R, profit factor, drawdown y estabilidad temporal.", styles["body"]))
    story.append(p("8. Gaspar v2", styles["h1"]))
    story.append(p("Objetivo: contexto operable/no operable. Gaspar no debe votar direccion; debe votar calidad de contexto. Targets sugeridos: context_quality_rr2 y ambiguity_risk.", styles["body"]))
    story.append(p("9. Melchor v2", styles["h1"]))
    story.append(p("Objetivo: riesgo operativo. Salida esperada: APPROVE / CAUTION / BLOCK. Target sugerido: risk_block_rr2 para bloquear spread, MAE, drawdown, ambiguedad TP/SL y rangos extremos.", styles["body"]))
    story.append(p("10. CEO v3", styles["h1"]))
    story.append(p("CEO v3 debe entrenarse despues de magos v2. Su objetivo no sera accuracy: sera EV positivo, cobertura razonable, drawdown controlado y estabilidad fuera de muestra.", styles["body"]))
    story.append(p("11. Riesgos y controles", styles["h1"]))
    story.append(bullet_list([
        "Sobreajuste por segmentos: controlar con walk-forward y ventanas futuras.",
        "Leakage: prohibir outcomes futuros como features.",
        "Meses malos: medir dispersion mensual y definir bloqueos.",
        "Dependencia de proxy: no declarar rentabilidad hasta tener first-touch.",
        "Labels mal disenados: validar que no repliquen a Baltasar ni reglas triviales.",
    ], styles))
    story.append(p("12. Proxima decision tecnica", styles["h1"]))
    story.append(p("La recomendacion es mejorar first-touch intrabar antes de reentrenar formalmente a los magos. Si se avanza en paralelo, el primer mago debe ser Baltasar v2 con target RR 1:2.", styles["callout"]))
    story.append(p("Scripts reutilizables: build_ceo_v2_tradeable_dataset.py, train_ceo_v2_tradeable_model.py, evaluate_ceo_v2_policy.py, walk_forward_ceo_v2_policy.py, simulate_ceo_v2_r_trades.py.", styles["body"]))
    story.append(p("Archivos nuevos recomendados: build_rr2_first_touch_labels.py, train_baltasar_v2_rr2.py, train_gaspar_v2_context.py, train_melchor_v2_risk.py, train_ceo_v3.py, backtest_magi_v3_institutional.py.", styles["body"]))
    story.append(p("Conclusion honesta", styles["h1"]))
    story.append(p("MAGI tiene base tecnica solida, pero CEO v2 todavia no demuestra rentabilidad operativa. La senal existe y la abstencion contextual mejoro; falta convertir la simulacion proxy en verdad operativa confiable antes de CEO v3.", styles["body"]))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = load_json(DATA_ROOT / "ceo_v2_tradeable" / "ceo_v2_tradeable_summary.json")
    model_metrics = load_json(DATA_ROOT / "ceo_v2_tradeable" / "ceo_v2_tradeable_metrics.json")
    policy_metrics = load_json(DATA_ROOT / "ceo_v2_tradeable" / "policy" / "ceo_v2_policy_metrics.json")
    wf = load_json(DATA_ROOT / "ceo_v2_tradeable" / "walk_forward_policy" / "walk_forward_metrics.json")
    r_metrics = load_json(DATA_ROOT / "ceo_v2_tradeable" / "r_simulation" / "r_simulation_metrics.json")
    audit = load_json(DATA_ROOT / "label_audit" / "label_audit_metrics.json")

    charts = build_charts(summary, model_metrics, wf, r_metrics)
    build_markdown(summary, model_metrics, policy_metrics, wf, r_metrics, audit, charts)
    build_pdf(summary, model_metrics, policy_metrics, wf, r_metrics, audit, charts)
    print(f"markdown={MD_PATH}")
    print(f"pdf={PDF_PATH}")


if __name__ == "__main__":
    main()
