from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pandas as pd


INPUT_DECISIONS = Path("artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv")
OUTPUT_DIR = Path("artifacts/ceo_magi_v3")
DETAIL_CSV = OUTPUT_DIR / "random_3_months_trade_audit.csv"
MONTHLY_CSV = OUTPUT_DIR / "random_3_months_monthly_summary.csv"
REPORT_MD = OUTPUT_DIR / "random_3_months_trade_audit.md"

RANDOM_SEED = 20260501
SL_PIPS = 10.0
MONTHS_TO_SAMPLE = 3


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trades = load_enter_trades()
    selected_months = select_non_continuous_months(trades)
    detail = build_detail(trades, selected_months)
    monthly = build_monthly_summary(detail)

    detail.to_csv(DETAIL_CSV, index=False)
    monthly.to_csv(MONTHLY_CSV, index=False)
    REPORT_MD.write_text(markdown_report(selected_months, monthly, detail), encoding="utf-8")

    print(f"selected_months={','.join(str(month) for month in selected_months)}")
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
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce")
    df["gross_r"] = pd.to_numeric(df["gross_r"], errors="coerce")
    df["net_pips"] = df["realized_R"] * SL_PIPS
    df["gross_pips"] = df["gross_r"] * SL_PIPS
    df["duration_minutes"] = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / 60.0
    df["duration"] = df["duration_minutes"].apply(format_duration)
    df["result"] = df["realized_R"].apply(result_label)
    return df.sort_values("entry_time").reset_index(drop=True)


def select_non_continuous_months(trades: pd.DataFrame) -> list[pd.Period]:
    months = sorted(pd.Period(month, freq="M") for month in trades["month"].dropna().unique())
    if len(months) < MONTHS_TO_SAMPLE:
        raise ValueError(f"Need at least {MONTHS_TO_SAMPLE} available months; found {len(months)}.")

    rng = random.Random(RANDOM_SEED)
    for _ in range(10_000):
        selected = sorted(rng.sample(months, MONTHS_TO_SAMPLE))
        if not has_continuous_months(selected):
            return selected

    raise ValueError("Could not select 3 non-continuous months from available ENTER months.")


def has_continuous_months(months: list[pd.Period]) -> bool:
    ordinals = [month.ordinal for month in months]
    return any((b - a) == 1 for a, b in zip(ordinals, ordinals[1:]))


def build_detail(trades: pd.DataFrame, selected_months: list[pd.Period]) -> pd.DataFrame:
    selected_labels = {str(month) for month in selected_months}
    out = trades[trades["month"].isin(selected_labels)].copy()
    out["entry_datetime"] = out["entry_time"].dt.strftime("%Y-%m-%d %H:%M:%S%z")
    out["exit_price"] = pd.NA
    out["reason_codes"] = out["reason_code"].apply(lambda value: f"[{value}]")

    columns = [
        "month",
        "entry_datetime",
        "symbol",
        "direction",
        "entry_price",
        "exit_price",
        "result",
        "gross_pips",
        "net_pips",
        "duration",
        "duration_minutes",
        "aggression_mode",
        "score",
        "reason_codes",
        "decision_id",
        "split",
        "realized_R",
        "gross_r",
    ]
    return out[columns].sort_values(["month", "entry_datetime"]).reset_index(drop=True)


def build_monthly_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for month, part in detail.groupby("month", sort=True):
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


def markdown_report(selected_months: list[pd.Period], monthly: pd.DataFrame, detail: pd.DataFrame) -> str:
    selected = ", ".join(f"`{month}`" for month in selected_months)
    non_continuous = "sí" if not has_continuous_months(selected_months) else "no"
    lines = [
        "# Auditoría Aleatoria de 3 Meses - CEO-MAGI v3",
        "",
        "## Selección",
        "",
        f"- Meses seleccionados: {selected}",
        f"- Selección reproducible con semilla: `{RANDOM_SEED}`",
        f"- Confirmación de no continuidad mensual: `{non_continuous}`",
        "- Universo: decisiones `ENTER` aprobadas por CEO-MAGI v3.",
        "",
        "## Resumen Mensual",
        "",
        monthly_table(monthly),
        "",
        "## Detalle de Operaciones por Mes",
        "",
    ]
    for month, part in detail.groupby("month", sort=True):
        lines.extend([f"### {month}", "", detail_table(part), ""])

    lines.extend(
        [
            "## Limitaciones de Datos",
            "",
            "- `exit_price` no existe en `ceo_magi_v3_decisions.csv` ni en `scenario_c_realistic_trades.csv`; se reporta vacío.",
            f"- `net_pips` se calcula como `realized_R * {SL_PIPS:.0f}` porque la validación usa SL fijo de `{SL_PIPS:.0f}` pips.",
            f"- `gross_pips` se calcula como `gross_r * {SL_PIPS:.0f}` por la misma convención de SL fijo.",
            "- La duración se calcula con `timestamp` y `exit_timestamp`; no se inventan cierres ni precios de salida.",
            "- La muestra incluye el split original de cada operación para auditoría, pero la selección aleatoria usa todo el universo offline aprobado.",
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
        "| Mes | Ops | Ganadoras | Perdedoras | BE | Win rate | Pips ganados brutos | Pips perdidos brutos | Pips netos | Duración prom. | Mín. | Máx. |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for _, row in monthly.iterrows():
        rows.append(
            f"| `{row['month']}` | {int(row['trades_executed'])} | {int(row['winning_trades'])} | "
            f"{int(row['losing_trades'])} | {int(row['breakeven_trades'])} | {row['win_rate']:.2%} | "
            f"{row['gross_winning_pips']:.1f} | {row['gross_losing_pips']:.1f} | {row['net_pips_month']:.1f} | "
            f"{row['avg_duration']} | {row['min_duration']} | {row['max_duration']} |"
        )
    return "\n".join(rows)


def detail_table(part: pd.DataFrame) -> str:
    rows = [
        "| Entrada | Símbolo | Dir | Entry | Exit | Resultado | Net pips | Duración | Modo | Score | Reason codes |",
        "| --- | --- | --- | ---: | --- | --- | ---: | --- | --- | ---: | --- |",
    ]
    for _, row in part.iterrows():
        exit_price = "" if pd.isna(row["exit_price"]) else str(row["exit_price"])
        rows.append(
            f"| `{row['entry_datetime']}` | `{row['symbol']}` | `{row['direction']}` | "
            f"{row['entry_price']:.5f} | {exit_price} | `{row['result']}` | {row['net_pips']:.1f} | "
            f"{row['duration']} | `{row['aggression_mode']}` | {row['score']:.4f} | `{row['reason_codes']}` |"
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
