from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import wrap

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


RUN_DIR = Path("data/output/ceo_training/20260429T141153Z_magi_v01_phase2")
AUDIT_DIR = Path("reports/bot_a_sub3_audits")
OUTPUT = Path("reports/magi_full_phase_report.pdf")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate full MAGI phase PDF report.")
    parser.add_argument("--run-dir", default=str(RUN_DIR))
    parser.add_argument("--audit-dir", default=str(AUDIT_DIR))
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    audit_dir = Path(args.audit_dir)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    summary = read_json(run_dir / "ceo_training_summary.json")
    individual = read_json(run_dir / "ceo_individual_vote_analysis.json")
    monthly = read_json(run_dir / "ceo_monthly_vote_analysis.json")
    regime = read_json(run_dir / "ceo_regime_analysis.json")
    audit = read_json(audit_dir / "data_quality_full_audit.json")

    with PdfPages(output) as pdf:
        page_summary(pdf, summary)
        page_dataset_quality(pdf, audit, summary)
        page_global_results(pdf, summary, individual)
        page_short_vs_long(pdf)
        page_baltasar(pdf, individual, monthly)
        page_gaspar(pdf, summary, individual)
        page_interaction(pdf, individual)
        page_regime_best(pdf, regime)
        page_regime_worst(pdf, regime)
        page_ceo_implications(pdf)
        page_retraining(pdf)
        page_split(pdf)
        page_risks_next_steps(pdf)

    print(output)
    return 0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def page_summary(pdf: PdfPages, summary: dict) -> None:
    fig = text_page(
        "1. Resumen ejecutivo",
        [
            "Se cerró la fase de validación histórica de MAGI sobre el dataset limpio Bot A sub3 2020-2026.",
            f"Se procesaron {summary['snapshots_received']:,} snapshots y se generaron {summary['records_generated']:,} registros CEO-MAGI.",
            "Se usaron Melchor real, Baltasar real y Gaspar real. Los horizontes fueron 12, 48, 96 y 288 barras M5.",
            "El hallazgo central es claro: los votos aislados no sostienen una señal robusta global. La señal aparece en votos + régimen.",
            "El futuro CEO-MAGI debe aprender cuándo confiar en los magos según sesión, hora, spread, rango, estructuras H4/D1, ATR consumido y posición en rango D1.",
            "No se entrenó CEO-MAGI, no se optimizaron reglas y no se modificaron modelos.",
        ],
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_dataset_quality(pdf: PdfPages, audit: dict, summary: dict) -> None:
    inv = audit["inventory"]
    quality = audit["quality"]
    rows = [
        ["Snapshots únicos limpios", f"{inv['unique_snapshots']:,}"],
        ["Registros CEO", f"{summary['records_generated']:,}"],
        ["Periodo", f"{inv['first_anchor_bar_timestamp'][:10]} a {inv['last_anchor_bar_timestamp'][:10]}"],
        ["Símbolo/timeframe", "EURUSD / M5"],
        ["Parse errors", str(quality["parse_errors_count"])],
        ["Duplicados finales", "0"],
        ["High spread", f"{quality['spread_extreme_gt_5_pips']:,}"],
        ["Features completas", f"{quality['features_complete_pct']}%"],
    ]
    fig, ax = table_page("2. Dataset usado y calidad", ["Métrica", "Valor"], rows)
    pdf.savefig(fig)
    plt.close(fig)


def page_global_results(pdf: PdfPages, summary: dict, individual: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
    baltasar_counts = {
        "BUY": summary["vote_counts"]["baltasar_BUY"],
        "SELL": summary["vote_counts"]["baltasar_SELL"],
        "NEUTRAL": summary["vote_counts"]["baltasar_NEUTRAL"],
    }
    gaspar_counts = {
        "GOOD": summary["vote_counts"]["gaspar_GOOD"],
        "FAIR": summary["vote_counts"]["gaspar_FAIR"],
        "POOR": summary["vote_counts"]["gaspar_POOR"],
    }
    axes[0, 0].bar(baltasar_counts.keys(), baltasar_counts.values())
    axes[0, 0].set_title("Distribución votos Baltasar")
    axes[0, 1].bar(gaspar_counts.keys(), gaspar_counts.values())
    axes[0, 1].set_title("Distribución votos Gaspar")
    hit = [
        individual["baltasar"]["BUY"]["horizons"]["48"]["directional_hit_rate"] * 100,
        individual["baltasar"]["SELL"]["horizons"]["48"]["directional_hit_rate"] * 100,
    ]
    axes[1, 0].bar(["BUY", "SELL"], hit)
    axes[1, 0].set_title("BUY vs SELL hit rate H48")
    axes[1, 0].set_ylabel("%")
    net = [
        individual["baltasar"]["BUY"]["horizons"]["48"]["avg_favorable_pips"] - individual["baltasar"]["BUY"]["horizons"]["48"]["avg_adverse_pips"],
        individual["baltasar"]["SELL"]["horizons"]["48"]["avg_favorable_pips"] - individual["baltasar"]["SELL"]["horizons"]["48"]["avg_adverse_pips"],
    ]
    axes[1, 1].bar(["BUY", "SELL"], net)
    axes[1, 1].set_title("BUY vs SELL net pips H48")
    axes[1, 1].set_ylabel("pips")
    fig.suptitle("3. Resultados globales 2020-2026", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    pdf.savefig(fig)
    plt.close(fig)


def page_short_vs_long(pdf: PdfPages) -> None:
    rows = [
        ["BUY H48 hit rate", "60.35%", "45.13%", "Se degrada"],
        ["BUY+GOOD H48 hit rate", "78.12%", "47.73%", "Se degrada fuerte"],
        ["SELL H48 hit rate", "56.76%", "44.15%", "Se debilita"],
        ["Gaspar GOOD", "Prometedor", "No robusto global", "Recalibrar"],
    ]
    fig, ax = table_page("4. Comparación 4 meses vs 6 años", ["Métrica", "4 meses", "6 años", "Lectura"], rows)
    pdf.savefig(fig)
    plt.close(fig)


def page_baltasar(pdf: PdfPages, individual: dict, monthly: dict) -> None:
    horizons = monthly["horizons"]
    buy_hit = [monthly["baltasar_by_horizon"][h]["buy"]["hit_rate"] * 100 for h in horizons]
    sell_hit = [monthly["baltasar_by_horizon"][h]["sell"]["hit_rate"] * 100 for h in horizons]
    buy_net = [monthly["baltasar_by_horizon"][h]["buy"]["avg_net_directional_pips"] for h in horizons]
    sell_net = [monthly["baltasar_by_horizon"][h]["sell"]["avg_net_directional_pips"] for h in horizons]
    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    x = range(len(horizons))
    axes[0].bar([i - 0.2 for i in x], buy_hit, width=0.4, label="BUY")
    axes[0].bar([i + 0.2 for i in x], sell_hit, width=0.4, label="SELL")
    axes[0].set_xticks(list(x), horizons)
    axes[0].set_title("Baltasar hit rate por horizonte")
    axes[0].legend()
    axes[1].bar([i - 0.2 for i in x], buy_net, width=0.4, label="BUY")
    axes[1].bar([i + 0.2 for i in x], sell_net, width=0.4, label="SELL")
    axes[1].set_xticks(list(x), horizons)
    axes[1].set_title("Baltasar net pips por horizonte")
    axes[1].legend()
    fig.suptitle("5. Comportamiento de Baltasar", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    pdf.savefig(fig)
    plt.close(fig)


def page_gaspar(pdf: PdfPages, summary: dict, individual: dict) -> None:
    rows = []
    for quality in ["GOOD", "FAIR", "POOR"]:
        h = individual["gaspar"][quality]["horizons"]["48"]
        rows.append([quality, f"{h['records']:,}", pct(h["directional_hit_rate"]), num(h["avg_future_return_pips"]), num(h["median_return_pips"])])
    fig, ax = table_page("6. Comportamiento de Gaspar H48", ["Calidad", "Casos", "Hit direccional", "Avg return", "Mediana"], rows)
    pdf.savefig(fig)
    plt.close(fig)


def page_interaction(pdf: PdfPages, individual: dict) -> None:
    groups = ["BUY_FAIR", "BUY_GOOD", "BUY_POOR", "SELL_FAIR", "SELL_GOOD"]
    values = [individual["baltasar_gaspar_cross"][g]["horizons"]["48"]["avg_future_return_pips"] for g in groups]
    hit = [individual["baltasar_gaspar_cross"][g]["horizons"]["48"]["directional_hit_rate"] * 100 for g in groups]
    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    axes[0].bar(groups, values)
    axes[0].set_title("Interacción: avg return H48")
    axes[0].tick_params(axis="x", rotation=30)
    axes[1].bar(groups, hit)
    axes[1].set_title("Interacción: hit rate H48")
    axes[1].tick_params(axis="x", rotation=30)
    fig.suptitle("7. Interacción Baltasar + Gaspar", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    pdf.savefig(fig)
    plt.close(fig)


def page_regime_best(pdf: PdfPages, regime: dict) -> None:
    rows = []
    for item in regime["best_segments_h48"][:10]:
        h = item["horizons"]["48"]
        rows.append([item["segment_type"], item["segment_value"], item["signal"], f"{h['directional_cases']:,}", pct(h["hit_rate"]), num(h["avg_net_directional_pips"])])
    fig, ax = table_page("8. Mejores segmentos por régimen H48", ["Segmento", "Valor", "Señal", "Casos", "Hit", "Net"], rows)
    pdf.savefig(fig)
    plt.close(fig)


def page_regime_worst(pdf: PdfPages, regime: dict) -> None:
    rows = []
    for item in regime["worst_segments_h48"][:10]:
        h = item["horizons"]["48"]
        rows.append([item["segment_type"], item["segment_value"], item["signal"], f"{h['directional_cases']:,}", pct(h["hit_rate"]), num(h["avg_net_directional_pips"])])
    fig, ax = table_page("8b. Peores segmentos por régimen H48", ["Segmento", "Valor", "Señal", "Casos", "Hit", "Net"], rows)
    pdf.savefig(fig)
    plt.close(fig)


def page_ceo_implications(pdf: PdfPages) -> None:
    fig = text_page(
        "9. Qué significa esto para CEO-MAGI",
        [
            "CEO-MAGI no debe ser un votador simple. Los votos aislados muestran una media débil e inestable.",
            "La decisión debe aprender interacciones: votos + confianza + régimen + riesgo.",
            "Features obligatorias: active_session, hora UTC, spread, rango M5, H4/D1 structure, directional_alignment, daily_atr_consumed_pct y position_in_d1_range.",
            "Melchor debe aportar riesgo operativo y bloqueo, no predicción direccional.",
            "La salida recomendada es ENTER_BUY, ENTER_SELL, HOLD, AVOID y LOW_CONFIDENCE.",
        ],
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_retraining(pdf: PdfPages) -> None:
    rows = [
        ["Baltasar", "BUY/SELL/NEUTRAL", "F1 macro, precision/recall, matriz confusión, estabilidad temporal"],
        ["Gaspar", "GOOD/FAIR/POOR", "calibración, lift por régimen, performance por dirección"],
        ["Melchor", "riesgo operativo", "bloqueos correctos, horarios, spread, condiciones prohibidas"],
        ["CEO-MAGI", "confiar o evitar", "outcome H48, MFE/MAE, estabilidad walk-forward"],
    ]
    fig, ax = table_page("10. Plan de reentrenamiento", ["Módulo", "Objetivo", "Métricas"], rows)
    pdf.savefig(fig)
    plt.close(fig)


def page_split(pdf: PdfPages) -> None:
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.set_title("11. Separación train / validation / test", fontsize=15)
    ax.set_xlim(2020, 2026.4)
    ax.set_ylim(0, 1)
    ax.barh([0.65], [4.0], left=[2020.0], height=0.18, label="Train 2020-01 a 2023-12")
    ax.barh([0.65], [1.0], left=[2024.0], height=0.18, label="Validation 2024")
    ax.barh([0.65], [1.33], left=[2025.0], height=0.18, label="Test final 2025-01 a 2026-04")
    ax.set_yticks([])
    ax.set_xlabel("Año")
    ax.legend(loc="lower center")
    ax.text(2020.05, 0.35, "Walk-forward: entrenar 18 meses, validar 3 meses, test forward 3 meses, avanzar ventana.", fontsize=11)
    ax.text(2020.05, 0.25, "Nunca usar split aleatorio simple. Transformadores y normalización se ajustan solo en train.", fontsize=11)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def page_risks_next_steps(pdf: PdfPages) -> None:
    fig = text_page(
        "12-13. Riesgos técnicos y próximos pasos",
        [
            "Hallazgos confirmados: votos aislados son insuficientes; régimen es obligatorio; Gaspar GOOD requiere recalibración; SELL es sensible a horarios y spread.",
            "Señales débiles: BUY+GOOD conserva ventaja relativa, pero no robusta globalmente. SELL+GOOD funciona en algunos meses y falla fuerte en otros.",
            "Hipótesis pendientes: segmentación por sesión y volatilidad puede mejorar el CEO; separar Gaspar por dirección puede estabilizar GOOD/FAIR/POOR.",
            "Riesgos: sobreajuste temporal, leakage en transformaciones, regímenes no representados, spread extremo, y dependencia de meses específicos.",
            "Próximo paso: entrenar baseline CEO interpretable con split temporal, reportería por régimen y validación walk-forward antes de cualquier demo.",
        ],
    )
    pdf.savefig(fig)
    plt.close(fig)


def table_page(title: str, columns: list[str], rows: list[list[str]]):
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    ax.set_title(title, fontsize=15, loc="left", pad=16)
    table = ax.table(cellText=rows, colLabels=columns, loc="center", cellLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.45)
    for (row, _col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold")
    fig.tight_layout()
    return fig, ax


def text_page(title: str, paragraphs: list[str]):
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.07, 0.93, title, fontsize=17, weight="bold", va="top")
    y = 0.86
    for paragraph in paragraphs:
        for line in wrap(paragraph, 112):
            fig.text(0.08, y, line, fontsize=11, va="top")
            y -= 0.035
        y -= 0.02
    return fig


def pct(value) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def num(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
