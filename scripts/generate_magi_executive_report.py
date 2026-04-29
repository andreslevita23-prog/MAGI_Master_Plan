from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import wrap

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


DEFAULT_RUN_DIR = Path("data/output/ceo_training/20260429T002335Z_magi_v01_phase2")
DEFAULT_OUTPUT = Path("reports/magi_executive_report.pdf")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MAGI executive PDF report.")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR), help="CEO training analysis run directory.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="PDF output path.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    training = load_json(run_dir / "ceo_training_summary.json")
    individual = load_json(run_dir / "ceo_individual_vote_analysis.json")
    monthly = load_json(run_dir / "ceo_monthly_vote_analysis.json")
    vote = load_json(run_dir / "ceo_vote_analysis.json")

    with PdfPages(output) as pdf:
        page_context(pdf, training)
        page_key_results(pdf, individual, monthly)
        page_baltasar_charts(pdf, monthly)
        page_monthly_charts(pdf, monthly)
        page_gaspar_charts(pdf, monthly)
        page_outcome_distribution(pdf, individual)
        page_conclusion(pdf, vote, monthly)

    print(output)
    return 0


def page_context(pdf: PdfPages, training: dict) -> None:
    fig = text_page(
        "Contexto",
        [
            "MAGI es un sistema multiagente de trading compuesto por Melchor, Baltasar, Gaspar y el futuro CEO-MAGI.",
            "En esta fase se implementó y ejecutó el simulador MAGI v0.5 para generar un dataset de entrenamiento del futuro CEO-MAGI.",
            "El dataset no depende de una estrategia fija con SL/TP. Cada registro combina snapshot histórico, votos reales de los tres magos y outcomes futuros crudos del precio.",
            "Datos utilizados:",
            f"- Fuente: Bot A sub3, EURUSD.",
            f"- Snapshots cargados: {training['snapshots_received']:,}.",
            f"- Snapshots válidos: {training['quality_summary']['valid_snapshots']:,}.",
            f"- Registros CEO generados: {training['records_generated']:,}.",
            f"- Horizontes: {training['config']['horizons_bars']} barras M5.",
            f"- Periodo observado: diciembre 2025 a abril 2026.",
        ],
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_key_results(pdf: PdfPages, individual: dict, monthly: dict) -> None:
    h48 = individual["baltasar"]["BUY"]["horizons"]["48"]
    sell48 = individual["baltasar"]["SELL"]["horizons"]["48"]
    buy_good = monthly["gaspar_good_cross_by_horizon"]["48"]["BUY_GOOD"]
    sell_good = monthly["gaspar_good_cross_by_horizon"]["48"]["SELL_GOOD"]
    fig = text_page(
        "Hallazgos principales",
        [
            f"Baltasar BUY tuvo hit rate H48 de {pct(h48['directional_hit_rate'])} y net directional pips promedio de {num(h48['avg_future_return_pips'])}.",
            f"Baltasar SELL tuvo hit rate H48 de {pct(sell48['directional_hit_rate'])}; medido como net direccional equivale a {num(monthly['baltasar_by_horizon']['48']['sell']['avg_net_directional_pips'])} pips.",
            f"Gaspar GOOD potenció BUY: BUY + GOOD tuvo {buy_good['cases']} casos, {pct(buy_good['hit_rate'])} hit rate y {num(buy_good['avg_net_directional_pips'])} net pips H48.",
            f"Gaspar GOOD no estabilizó SELL: SELL + GOOD tuvo {sell_good['cases']} casos, {pct(sell_good['hit_rate'])} hit rate y {num(sell_good['avg_net_directional_pips'])} net pips H48.",
            "La variación mensual fue relevante: enero fue el mes más fuerte; abril degradó SELL y SELL + GOOD.",
            "El análisis es descriptivo. No se entrenó CEO-MAGI, no se modificaron modelos y no se evaluó ejecución de trades.",
        ],
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_baltasar_charts(pdf: PdfPages, monthly: dict) -> None:
    horizons = monthly["horizons"]
    buy_hit = [monthly["baltasar_by_horizon"][h]["buy"]["hit_rate"] * 100 for h in horizons]
    sell_hit = [monthly["baltasar_by_horizon"][h]["sell"]["hit_rate"] * 100 for h in horizons]
    buy_net = [monthly["baltasar_by_horizon"][h]["buy"]["avg_net_directional_pips"] for h in horizons]
    sell_net = [monthly["baltasar_by_horizon"][h]["sell"]["avg_net_directional_pips"] for h in horizons]

    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    x = range(len(horizons))
    axes[0].bar([i - 0.2 for i in x], buy_hit, width=0.4, label="BUY")
    axes[0].bar([i + 0.2 for i in x], sell_hit, width=0.4, label="SELL")
    axes[0].set_title("Hit rate BUY vs SELL")
    axes[0].set_xticks(list(x), horizons)
    axes[0].set_ylabel("Hit rate (%)")
    axes[0].legend()

    axes[1].bar([i - 0.2 for i in x], buy_net, width=0.4, label="BUY")
    axes[1].bar([i + 0.2 for i in x], sell_net, width=0.4, label="SELL")
    axes[1].set_title("Avg net directional pips")
    axes[1].set_xticks(list(x), horizons)
    axes[1].set_ylabel("Pips")
    axes[1].legend()
    fig.suptitle("Baltasar: resultados por horizonte", fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    pdf.savefig(fig)
    plt.close(fig)


def page_monthly_charts(pdf: PdfPages, monthly: dict) -> None:
    rows = monthly["monthly_h48"]
    months = list(rows)
    buy_net = [rows[m]["buy"]["avg_net_directional_pips"] for m in months]
    sell_net = [rows[m]["sell"]["avg_net_directional_pips"] for m in months]
    buy_hit = [rows[m]["buy"]["hit_rate"] * 100 for m in months]
    sell_hit = [rows[m]["sell"]["hit_rate"] * 100 for m in months]

    fig, axes = plt.subplots(2, 1, figsize=(11, 8.5))
    axes[0].plot(months, buy_net, marker="o", label="BUY")
    axes[0].plot(months, sell_net, marker="o", label="SELL")
    axes[0].set_title("Evolución mensual H48: net directional pips")
    axes[0].set_ylabel("Pips")
    axes[0].legend()

    axes[1].plot(months, buy_hit, marker="o", label="BUY")
    axes[1].plot(months, sell_hit, marker="o", label="SELL")
    axes[1].set_title("Evolución mensual H48: hit rate")
    axes[1].set_ylabel("Hit rate (%)")
    axes[1].legend()
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def page_gaspar_charts(pdf: PdfPages, monthly: dict) -> None:
    rows = monthly["monthly_h48"]
    months = list(rows)
    buy = [rows[m]["buy"]["avg_net_directional_pips"] for m in months]
    buy_good = [rows[m]["buy_good"]["avg_net_directional_pips"] for m in months]
    sell = [rows[m]["sell"]["avg_net_directional_pips"] for m in months]
    sell_good = [rows[m]["sell_good"]["avg_net_directional_pips"] for m in months]

    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    axes[0].plot(months, buy, marker="o", label="BUY")
    axes[0].plot(months, buy_good, marker="o", label="BUY + GOOD")
    axes[0].set_title("BUY vs BUY + GOOD")
    axes[0].set_ylabel("Net pips H48")
    axes[0].tick_params(axis="x", rotation=30)
    axes[0].legend()

    axes[1].plot(months, sell, marker="o", label="SELL")
    axes[1].plot(months, sell_good, marker="o", label="SELL + GOOD")
    axes[1].set_title("SELL vs SELL + GOOD")
    axes[1].set_ylabel("Net pips H48")
    axes[1].tick_params(axis="x", rotation=30)
    axes[1].legend()
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def page_outcome_distribution(pdf: PdfPages, individual: dict) -> None:
    horizons = individual["horizons"]
    buy = []
    sell = []
    flat = []
    for h in horizons:
        dist_buy = individual["baltasar"]["BUY"]["horizons"][h]["real_direction_distribution"]
        dist_sell = individual["baltasar"]["SELL"]["horizons"][h]["real_direction_distribution"]
        buy.append(dist_buy.get("BUY", 0) + dist_sell.get("BUY", 0))
        sell.append(dist_buy.get("SELL", 0) + dist_sell.get("SELL", 0))
        flat.append(dist_buy.get("FLAT", 0) + dist_sell.get("FLAT", 0))

    fig, ax = plt.subplots(figsize=(11, 8.5))
    x = range(len(horizons))
    ax.bar(x, buy, label="Outcome BUY")
    ax.bar(x, sell, bottom=buy, label="Outcome SELL")
    bottom = [buy[i] + sell[i] for i in x]
    ax.bar(x, flat, bottom=bottom, label="Outcome FLAT")
    ax.set_title("Distribución de outcomes por horizonte en señales direccionales")
    ax.set_xticks(list(x), horizons)
    ax.set_xlabel("Horizonte M5")
    ax.set_ylabel("Casos")
    ax.legend()
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def page_conclusion(pdf: PdfPages, vote: dict, monthly: dict) -> None:
    hom = monthly["homogeneity_h48"]
    fig = text_page(
        "Conclusión y siguiente paso",
        [
            "Qué funciona:",
            "- Baltasar aporta señal direccional medible, especialmente en BUY H48.",
            "- Gaspar GOOD mejora notablemente BUY cuando coincide, aunque la muestra es limitada.",
            "- El pipeline genera registros auditables con leakage guard y outcomes crudos.",
            "Qué no funciona aún:",
            "- Gaspar GOOD no mejora SELL de forma estable.",
            "- SELL presenta sensibilidad fuerte al régimen mensual.",
            "- El periodo analizado es corto y de un solo símbolo.",
            "Riesgos:",
            f"- BUY+GOOD tiene alta media mensual ({num(hom['buy_good']['monthly_mean'])}) pero alta desviación ({num(hom['buy_good']['monthly_std'])}).",
            f"- SELL+GOOD concentra {pct(hom['sell_good']['best_month_total_concentration'])} del resultado en su mejor mes total.",
            "- Enero concentra parte relevante del resultado; abril muestra degradación de SELL.",
            "Siguiente paso recomendado:",
            "- Validar fuera de muestra con el histórico amplio de seis años antes de entrenar CEO-MAGI.",
            "- Separar validación por sesión, régimen y dirección.",
            "- Solo después entrenar un primer CEO supervisado con splits temporales y walk-forward.",
        ],
    )
    pdf.savefig(fig)
    plt.close(fig)


def text_page(title: str, paragraphs: list[str]):
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.07, 0.93, title, fontsize=18, weight="bold", va="top")
    y = 0.86
    for paragraph in paragraphs:
        lines = wrap(paragraph, 105) or [""]
        for line in lines:
            fig.text(0.08, y, line, fontsize=11, va="top")
            y -= 0.035
        y -= 0.015
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
