from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from simulate_magi_guardrails_v1 import (
    ACCOUNT,
    GLOBAL_FILE,
    PIP_VALUE_PER_LOT,
    REPORTS,
    STRESS_FILE,
    Trade,
    is_loss,
    is_win,
    load_trades,
    op_day,
    simulate,
    table,
)


MONTHS = ["2020-03", "2022-04", "2020-09", "2021-08", "2022-08", "2024-06", "2024-10"]
SCENARIOS = [
    ("baseline", "baseline", 1),
    ("cluster_only_3sl", "cluster_only_3sl", 1),
    ("guardrails_completos", "guardrails_v1_friday_sl1", 1),
]
LOTS = [0.6, 1.0]

DAILY_06 = REPORTS / "magi_daily_breakdown_0_6.csv"
DAILY_10 = REPORTS / "magi_daily_breakdown_1_0.csv"
EQUITY_CSV = REPORTS / "magi_equity_curves.csv"
DD_CSV = REPORTS / "magi_drawdown_analysis.csv"
REPORT_MD = REPORTS / "magi_daily_equity_analysis_2026-05-15.md"
CHART_DIR = REPORTS / "charts"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def money(value: float) -> str:
    return f"{value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def month_dates(month: str, executed: list[Trade], blocked: list[dict[str, Any]]) -> list[str]:
    days = {op_day(t.exit_time) for t in executed}
    days.update(str(b.get("entry_time", ""))[:10] for b in blocked if str(b.get("entry_time", "")).startswith(month))
    if not days:
        year, mo = map(int, month.split("-"))
        return [date(year, mo, 1).isoformat()]
    return sorted(days)


def daily_rows_for(month: str, scenario_label: str, executed: list[Trade], blocked: list[dict[str, Any]], lot: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    trades_by_day: dict[str, list[Trade]] = defaultdict(list)
    for trade in executed:
        trades_by_day[op_day(trade.exit_time)].append(trade)
    blocked_by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in blocked:
        day = str(item.get("entry_time", ""))[:10]
        if day:
            blocked_by_day[day].append(item)

    balance = ACCOUNT
    peak = ACCOUNT
    max_dd = 0.0
    max_dd_day = ""
    current_dd_days = 0
    max_dd_duration_days = 0
    recovery_events = 0
    was_in_dd = False
    daily_rows: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []

    for day in month_dates(month, executed, blocked):
        day_trades = trades_by_day.get(day, [])
        day_pnl = sum(t.net_pips * lot * PIP_VALUE_PER_LOT for t in day_trades)
        balance += day_pnl
        if balance >= peak:
            if was_in_dd:
                recovery_events += 1
            peak = balance
            was_in_dd = False
            current_dd_days = 0
        else:
            was_in_dd = True
            current_dd_days += 1
        drawdown = peak - balance
        if drawdown > max_dd:
            max_dd = drawdown
            max_dd_day = day
        max_dd_duration_days = max(max_dd_duration_days, current_dd_days)
        daily_margin = 0.04 * ACCOUNT + day_pnl
        total_margin = balance - ACCOUNT * 0.92
        danger = "SI" if daily_margin < 0 or total_margin < 0 else "Cerca" if daily_margin <= 1000 or total_margin <= 2000 else "No"
        toxic_reasons = sorted({str(b.get("reason", "")) for b in blocked_by_day.get(day, []) if "cluster" in str(b.get("reason", "")) or "safe_mode" in str(b.get("reason", ""))})
        row = {
            "month": month,
            "scenario": scenario_label,
            "lot": lot,
            "date": day,
            "trades": len(day_trades),
            "tp": sum(1 for t in day_trades if is_win(t)),
            "sl": sum(1 for t in day_trades if is_loss(t)),
            "be": sum(1 for t in day_trades if not is_win(t) and not is_loss(t)),
            "daily_pnl_usd": round(day_pnl, 2),
            "balance_usd": round(balance, 2),
            "drawdown_usd": round(drawdown, 2),
            "drawdown_pct": round(drawdown / ACCOUNT, 6),
            "distance_daily_limit_usd": round(daily_margin, 2),
            "distance_total_limit_usd": round(total_margin, 2),
            "danger_zone": danger,
            "toxic_cluster_detected": bool(toxic_reasons),
            "toxic_cluster_reason": ";".join(toxic_reasons),
        }
        daily_rows.append(row)
        equity_rows.append(
            {
                "month": month,
                "scenario": scenario_label,
                "lot": lot,
                "date": day,
                "balance_usd": round(balance, 2),
                "peak_usd": round(peak, 2),
                "drawdown_usd": round(drawdown, 2),
                "drawdown_pct": round(drawdown / ACCOUNT, 6),
                "daily_pnl_usd": round(day_pnl, 2),
            }
        )
    summary = {
        "month": month,
        "scenario": scenario_label,
        "lot": lot,
        "final_balance_usd": round(balance, 2),
        "net_usd": round(balance - ACCOUNT, 2),
        "max_drawdown_usd": round(max_dd, 2),
        "max_drawdown_pct": round(max_dd / ACCOUNT, 6),
        "max_drawdown_day": max_dd_day,
        "max_drawdown_duration_days": max_dd_duration_days,
        "recovery_events": recovery_events,
        "worst_day_usd": min((r["daily_pnl_usd"] for r in daily_rows), default=0),
        "best_day_usd": max((r["daily_pnl_usd"] for r in daily_rows), default=0),
        "min_daily_limit_margin_usd": min((r["distance_daily_limit_usd"] for r in daily_rows), default=4000),
        "min_total_limit_margin_usd": min((r["distance_total_limit_usd"] for r in daily_rows), default=8000),
        "danger_days": sum(1 for r in daily_rows if r["danger_zone"] != "No"),
    }
    return daily_rows, equity_rows, summary


def load_selected_trades() -> dict[str, list[Trade]]:
    stress = load_trades(STRESS_FILE, "stress_months")
    global_trades = load_trades(GLOBAL_FILE, "ceo_magi_v3_decisions")
    out: dict[str, list[Trade]] = {}
    for month in MONTHS:
        source = stress if month in {"2020-03", "2022-04"} else global_trades
        out[month] = [t for t in source if t.month == month]
    return out


def line_points(values: list[tuple[str, float]], x0: int, y0: int, w: int, h: int, vmin: float, vmax: float) -> list[tuple[int, int]]:
    if len(values) == 1:
        x_positions = [x0 + w // 2]
    else:
        x_positions = [x0 + round(i * w / (len(values) - 1)) for i in range(len(values))]
    span = max(vmax - vmin, 1.0)
    points = []
    for x, (_, value) in zip(x_positions, values):
        y = y0 + h - round((value - vmin) / span * h)
        points.append((x, y))
    return points


def draw_chart(month: str, equity_rows: list[dict[str, Any]]) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    month_rows = [r for r in equity_rows if r["month"] == month]
    if not month_rows:
        return
    width, height = 1280, 760
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()
    left, right = 80, 40
    top1, h1 = 70, 330
    top2, h2 = 470, 210
    plot_w = width - left - right

    draw.text((left, 25), f"MAGI equity diaria - {month}", fill=(20, 20, 20), font=title_font)
    draw.text((left, 45), "Balance arriba; drawdown abajo. Cuenta inicial 100,000 USD.", fill=(80, 80, 80), font=font)

    series: dict[tuple[str, float], list[tuple[str, float]]] = {}
    dd_series: dict[tuple[str, float], list[tuple[str, float]]] = {}
    for scenario, _, _ in SCENARIOS:
        for lot in LOTS:
            rows = sorted([r for r in month_rows if r["scenario"] == scenario and float(r["lot"]) == lot], key=lambda r: r["date"])
            series[(scenario, lot)] = [(str(r["date"]), float(r["balance_usd"])) for r in rows]
            dd_series[(scenario, lot)] = [(str(r["date"]), float(r["drawdown_usd"])) for r in rows]

    balances = [v for values in series.values() for _, v in values] + [ACCOUNT]
    dds = [v for values in dd_series.values() for _, v in values] + [0.0]
    bmin = min(balances) - 500
    bmax = max(balances) + 500
    dmin = 0.0
    dmax = max(dds) + 250
    colors = {
        ("baseline", 0.6): (30, 100, 200),
        ("baseline", 1.0): (5, 50, 145),
        ("cluster_only_3sl", 0.6): (0, 145, 95),
        ("cluster_only_3sl", 1.0): (0, 100, 60),
        ("guardrails_completos", 0.6): (210, 120, 0),
        ("guardrails_completos", 1.0): (170, 70, 0),
    }

    for y0, h, label in [(top1, h1, "Balance USD"), (top2, h2, "Drawdown USD")]:
        draw.rectangle((left, y0, left + plot_w, y0 + h), outline=(180, 180, 180))
        draw.text((20, y0 + 5), label, fill=(40, 40, 40), font=font)
        for frac in [0, 0.25, 0.5, 0.75, 1.0]:
            y = y0 + round(frac * h)
            draw.line((left, y, left + plot_w, y), fill=(235, 235, 235))

    for key, values in series.items():
        if values:
            points = line_points(values, left, top1, plot_w, h1, bmin, bmax)
            draw.line(points, fill=colors[key], width=3 if key[1] == 1.0 else 2)
            for p in points:
                draw.ellipse((p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2), fill=colors[key])
    for key, values in dd_series.items():
        if values:
            points = line_points(values, left, top2, plot_w, h2, dmin, dmax)
            draw.line(points, fill=colors[key], width=3 if key[1] == 1.0 else 2)

    draw.text((left, top1 - 18), f"{money(bmax)}", fill=(80, 80, 80), font=font)
    draw.text((left, top1 + h1 + 4), f"{money(bmin)}", fill=(80, 80, 80), font=font)
    draw.text((left, top2 - 18), f"DD max escala: {money(dmax)}", fill=(80, 80, 80), font=font)

    legend_x, legend_y = left + 20, height - 58
    for idx, key in enumerate(colors):
        x = legend_x + (idx % 3) * 350
        y = legend_y + (idx // 3) * 22
        draw.line((x, y + 5, x + 35, y + 5), fill=colors[key], width=3 if key[1] == 1.0 else 2)
        draw.text((x + 44, y), f"{key[0]} lot {key[1]}", fill=(30, 30, 30), font=font)

    filename = f"equity_curve_{month.replace('-', '_')}.png"
    img.save(CHART_DIR / filename)


def build_report(daily06: list[dict[str, Any]], daily10: list[dict[str, Any]], dd_rows: list[dict[str, Any]]) -> None:
    key_cols = [
        "month",
        "scenario",
        "lot",
        "net_usd",
        "max_drawdown_usd",
        "max_drawdown_pct",
        "max_drawdown_duration_days",
        "worst_day_usd",
        "best_day_usd",
        "min_daily_limit_margin_usd",
        "min_total_limit_margin_usd",
        "danger_days",
    ]
    lot06_summary = [r for r in dd_rows if float(r["lot"]) == 0.6]
    lot10_summary = [r for r in dd_rows if float(r["lot"]) == 1.0]
    worst10 = sorted(lot10_summary, key=lambda r: float(r["max_drawdown_usd"]), reverse=True)[:8]
    report: list[str] = []
    report.append("# Analisis diario de equity MAGI\n")
    report.append("Fecha de corte: 2026-05-15\n")
    report.append("No se modifica codigo operativo. Analisis offline de simulacion historica por dia.\n")
    report.append("## Alcance\n")
    report.append("- Meses: 2020-03, 2022-04, 2020-09, 2021-08, 2022-08, 2024-06, 2024-10.\n")
    report.append("- Escenarios: baseline, cluster_only_3sl, guardrails_completos.\n")
    report.append("- Cuenta inicial: 100,000 USD. Reglas: perdida diaria maxima 4%, perdida total maxima 8%.\n")
    report.append("- PnL convertido desde `net_pips` historico con valor pip estandar: 10 USD por pip por lote.\n")
    report.append("## Lectura ejecutiva\n")
    report.append("- Con lotaje 0.6, las curvas son mas comodas: los peores dias y drawdowns quedan lejos de los limites de fondeo en esta muestra.\n")
    report.append("- Con lotaje 1.0, la muestra tampoco quema cuenta, pero algunos meses ya se sienten mas serruchados y emocionalmente mas exigentes.\n")
    report.append("- El valor `7.52R` del agregado equivale aproximadamente al tramo de drawdown relativo del sistema, pero en dinero real depende de pips/lote: en esta simulacion diaria el dolor visible se evalua mejor con USD y margen restante.\n")
    report.append("- Los guardrails completos suavizan algunos drawdowns, pero tambien cortan ganancia; `cluster_only_3sl` es menos invasivo.\n")
    report.append("## Resumen lotaje 0.6\n")
    report.append(table(lot06_summary, key_cols))
    report.append("\n\n## Resumen lotaje 1.0\n")
    report.append(table(lot10_summary, key_cols))
    report.append("\n\n## Peores tramos por drawdown con lotaje 1.0\n")
    report.append(table(worst10, key_cols))
    report.append("\n\n## Interpretacion operativa\n")
    report.append("- `0.6` parece el lotaje mas sano hoy: deja mas distancia psicologica y tecnica frente a limites diarios/totales.\n")
    report.append("- `1.0` no aparece como quemador en estos meses, pero es menos comodo: aumenta la velocidad del drawdown y exige mas tolerancia a dias negativos.\n")
    report.append("- Los meses que mas asustan son los que combinan varias perdidas cercanas o recuperaciones lentas, no necesariamente los de peor neto mensual.\n")
    report.append("- La curva de MAGI no es lineal; hay recuperaciones, pero la experiencia operativa real incluye serruchos. Eso refuerza operar demo/fondeo conservador antes de escalar.\n")
    report.append("## Recomendacion final\n")
    report.append("El lotaje `0.6` es la opcion prudente para una funded conservadora inicial. `1.0` debe tratarse como agresivo hasta validar mas meses continuos y la gestion activa de BE/drawdown. MAGI sigue prometedor, pero aun no debe evaluarse solo por net R agregado: la curva diaria y la distancia a limites son la metrica operativa principal.\n")
    report.append("## Archivos generados\n")
    for path in [DAILY_06, DAILY_10, EQUITY_CSV, DD_CSV]:
        report.append(f"- `{path.relative_to(REPORTS.parent)}`\n")
    for month in MONTHS:
        report.append(f"- `reports/charts/equity_curve_{month.replace('-', '_')}.png`\n")
    REPORT_MD.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    selected = load_selected_trades()
    daily_by_lot: dict[float, list[dict[str, Any]]] = {0.6: [], 1.0: []}
    equity_rows: list[dict[str, Any]] = []
    dd_rows: list[dict[str, Any]] = []

    for month, trades in selected.items():
        for scenario_label, scenario, friday_threshold in SCENARIOS:
            executed, blocked, _ = simulate(trades, scenario, friday_threshold)
            for lot in LOTS:
                daily_rows, eq_rows, summary = daily_rows_for(month, scenario_label, executed, blocked, lot)
                daily_by_lot[lot].extend(daily_rows)
                equity_rows.extend(eq_rows)
                dd_rows.append(summary)
    write_csv(DAILY_06, daily_by_lot[0.6])
    write_csv(DAILY_10, daily_by_lot[1.0])
    write_csv(EQUITY_CSV, equity_rows)
    write_csv(DD_CSV, dd_rows)
    for month in MONTHS:
        draw_chart(month, equity_rows)
    build_report(daily_by_lot[0.6], daily_by_lot[1.0], dd_rows)


if __name__ == "__main__":
    main()
