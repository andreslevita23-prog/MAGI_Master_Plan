from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


INPUT_DECISIONS = Path("artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv")
OUTPUT_DIR = Path("artifacts/ceo_magi_v3")
DETAIL_CSV = OUTPUT_DIR / "stress_months_trade_audit_full.csv"
MONTHLY_CSV = OUTPUT_DIR / "stress_months_monthly_summary_full.csv"
REPORT_MD = OUTPUT_DIR / "stress_months_trade_audit_full.md"

STRESS_MONTHS = ["2020-03", "2022-04", "2026-04"]
STRESS_LABELS = {
    "2020-03": "pandemia pico",
    "2022-04": "inflacion alta",
    "2026-04": "periodo problematico reciente; datos parciales disponibles",
}
SL_PIPS = 10.0


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trades = load_enter_trades()
    detail = build_detail(trades)
    monthly = build_monthly_summary(detail)

    detail.to_csv(DETAIL_CSV, index=False)
    monthly.to_csv(MONTHLY_CSV, index=False)
    REPORT_MD.write_text(markdown_report(monthly, detail), encoding="utf-8")

    print(f"stress_months={','.join(STRESS_MONTHS)}")
    print(f"detail_rows={len(detail)}")
    print(f"monthly_rows={len(monthly)}")
    print(f"output_detail={DETAIL_CSV}")
    print(f"output_monthly={MONTHLY_CSV}")
    print(f"output_report={REPORT_MD}")


def load_enter_trades() -> pd.DataFrame:
    if not INPUT_DECISIONS.exists():
        raise FileNotFoundError(f"Missing CEO-MAGI v3 decisions CSV: {INPUT_DECISIONS}")

    df = pd.read_csv(INPUT_DECISIONS)
    df = df[df["action"].eq("ENTER")].copy()
    if df.empty:
        raise ValueError("No ENTER decisions found in CEO-MAGI v3 decisions CSV.")

    df["entry_time"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["exit_time"] = pd.to_datetime(df["exit_timestamp"], utc=True, errors="coerce")
    df["month"] = df["entry_time"].dt.tz_convert(None).dt.to_period("M").astype(str)
    df = df[df["month"].isin(STRESS_MONTHS)].copy()

    for col in ["realized_R", "gross_r", "entry_price", "score"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["net_pips"] = df["realized_R"] * SL_PIPS
    df["gross_pips"] = df["gross_r"] * SL_PIPS
    df["duration_minutes"] = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / 60.0
    df["duration"] = df["duration_minutes"].apply(format_duration)
    df["result"] = df["realized_R"].apply(result_label)
    return df.sort_values("entry_time").reset_index(drop=True)


def build_detail(trades: pd.DataFrame) -> pd.DataFrame:
    out = trades.copy()
    out["entry_datetime"] = out["entry_time"].dt.strftime("%Y-%m-%d %H:%M:%S%z")
    out["reason_codes"] = out["reason_code"].apply(lambda value: f"[{value}]")

    columns = [
        "month",
        "entry_datetime",
        "symbol",
        "direction",
        "entry_price",
        "result",
        "net_pips",
        "duration",
        "duration_minutes",
        "score",
        "aggression_mode",
        "reason_codes",
        "decision_id",
        "split",
        "realized_R",
        "gross_r",
        "gross_pips",
    ]
    return out[columns].sort_values(["month", "entry_datetime"]).reset_index(drop=True)


def build_monthly_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for month in STRESS_MONTHS:
        part = detail[detail["month"].eq(month)].copy()
        wins = int(part["result"].eq("WIN").sum())
        losses = int(part["result"].eq("LOSS").sum())
        be = int(part["result"].eq("BE").sum())
        trades = int(len(part))
        gross_pips = pd.to_numeric(part["gross_pips"], errors="coerce").fillna(0.0)
        net_pips = pd.to_numeric(part["net_pips"], errors="coerce").fillna(0.0)
        duration = pd.to_numeric(part["duration_minutes"], errors="coerce").dropna()
        rows.append(
            {
                "month": month,
                "stress_label": STRESS_LABELS[month],
                "trades_executed": trades,
                "winning_trades": wins,
                "losing_trades": losses,
                "breakeven_trades": be,
                "win_rate": round_float(wins / trades if trades else 0.0),
                "gross_winning_pips": round_float(float(gross_pips[gross_pips > 0].sum())),
                "gross_losing_pips": round_float(float(gross_pips[gross_pips < 0].sum())),
                "net_pips_month": round_float(float(net_pips.sum())),
                "avg_duration": format_duration(float(duration.mean()) if len(duration) else None),
                "min_duration": format_duration(float(duration.min()) if len(duration) else None),
                "max_duration": format_duration(float(duration.max()) if len(duration) else None),
                "avg_duration_minutes": round_float(float(duration.mean()) if len(duration) else 0.0),
                "min_duration_minutes": round_float(float(duration.min()) if len(duration) else 0.0),
                "max_duration_minutes": round_float(float(duration.max()) if len(duration) else 0.0),
            }
        )
    return pd.DataFrame(rows)


def markdown_report(monthly: pd.DataFrame, detail: pd.DataFrame) -> str:
    lines = [
        "# Auditoria de Meses de Estres - CEO-MAGI v3",
        "",
        "## Confirmacion de Formato",
        "",
        "- Usa el mismo formato operativo que `random_3_months_trade_audit`.",
        f"- Usa la misma convencion de pips: `net_pips = realized_R * {SL_PIPS:.0f}`.",
        "- Usa los mismos calculos de duracion: `exit_timestamp - timestamp`.",
        "- Usa solo operaciones `ENTER` aprobadas por CEO-MAGI v3.",
        "- No modifica modelos, reglas, Bot B ni MT5.",
        "",
        "## Meses Analizados",
        "",
        "- `2020-03`: pandemia pico.",
        "- `2022-04`: inflacion alta.",
        "- `2026-04`: periodo problematico reciente; datos parciales disponibles.",
        "",
        "## Resumen Mensual Completo",
        "",
        monthly_table(monthly),
        "",
        "## Detalle de Trades",
        "",
    ]
    for month in STRESS_MONTHS:
        part = detail[detail["month"].eq(month)]
        lines.extend([f"### {month}", "", detail_table(part), ""])

    lines.extend(
        [
            "## Limitaciones",
            "",
            "- `exit_price` no se incluye porque no existe en `ceo_magi_v3_decisions.csv` ni fue requerido en este formato rehecho.",
            f"- Los pips son equivalentes derivados de R con SL fijo de `{SL_PIPS:.0f}` pips; no son pips reportados por broker.",
            "- `2026-04` tiene datos parciales: en el universo disponible solo hay operaciones hasta mediados de abril y solo 3 entradas aprobadas por CEO-MAGI v3.",
            "- La duracion depende de `exit_timestamp`; si un trade fue timeout, la duracion refleja el cierre usado por la validacion offline.",
            "",
            "## Archivos Generados",
            "",
            f"- `{DETAIL_CSV}`",
            f"- `{MONTHLY_CSV}`",
            f"- `{REPORT_MD}`",
            "",
        ]
    )
    return "\n".join(lines)


def monthly_table(monthly: pd.DataFrame) -> str:
    rows = [
        "| Mes | Contexto | Ops | Ganadoras | Perdedoras | BE | Win rate | Pips ganados brutos | Pips perdidos brutos | Pips netos | Duracion prom. | Min. | Max. |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for _, row in monthly.iterrows():
        rows.append(
            f"| `{row['month']}` | {row['stress_label']} | {int(row['trades_executed'])} | "
            f"{int(row['winning_trades'])} | {int(row['losing_trades'])} | {int(row['breakeven_trades'])} | "
            f"{row['win_rate']:.2%} | {row['gross_winning_pips']:.1f} | {row['gross_losing_pips']:.1f} | "
            f"{row['net_pips_month']:.1f} | {row['avg_duration']} | {row['min_duration']} | {row['max_duration']} |"
        )
    return "\n".join(rows)


def detail_table(part: pd.DataFrame) -> str:
    rows = [
        "| Timestamp entrada | Simbolo | Direccion | Entry price | Resultado | Net pips | Duracion | Score | Aggression mode | Reason codes |",
        "| --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- |",
    ]
    if part.empty:
        rows.append("| _sin operaciones ENTER aprobadas_ |  |  |  |  |  |  |  |  |  |")
        return "\n".join(rows)

    for _, row in part.iterrows():
        rows.append(
            f"| `{row['entry_datetime']}` | `{row['symbol']}` | `{row['direction']}` | {row['entry_price']:.5f} | "
            f"`{row['result']}` | {row['net_pips']:.1f} | {row['duration']} | {row['score']:.4f} | "
            f"`{row['aggression_mode']}` | `{row['reason_codes']}` |"
        )
    return "\n".join(rows)


def result_label(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if number > 0:
        return "WIN"
    if number < 0:
        return "LOSS"
    return "BE"


def format_duration(minutes: Any) -> str:
    if minutes is None or pd.isna(minutes):
        return ""
    total = int(round(float(minutes)))
    hours, mins = divmod(total, 60)
    if hours:
        return f"{hours}h {mins:02d}m"
    return f"{mins}m"


def round_float(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


if __name__ == "__main__":
    main()
