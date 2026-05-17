from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from validate_scenario_c_realistic import max_drawdown, round_float


INPUT_TRADES = Path("artifacts/magi_validation/online_priority_scoring_trades.csv")
OUTPUT_DIR = Path("artifacts/magi_validation")
AUDIT_MD = OUTPUT_DIR / "online_priority_scoring_deep_audit.md"
TEMPORAL_CSV = OUTPUT_DIR / "online_priority_scoring_temporal.csv"
SCORE_BUCKETS_CSV = OUTPUT_DIR / "online_priority_scoring_score_buckets.csv"
DIRECTION_CSV = OUTPUT_DIR / "online_priority_scoring_direction_breakdown.csv"

STRATEGY = "C_scoring_online_causal"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trades = load_trades()

    temporal = build_temporal(trades)
    score_buckets = build_score_buckets(trades)
    direction = build_direction_breakdown(trades)
    q2 = build_q2_detail(trades)
    month_distribution = build_month_distribution(trades)
    drawdown = build_drawdown_temporal(trades)

    temporal.to_csv(TEMPORAL_CSV, index=False)
    score_buckets.to_csv(SCORE_BUCKETS_CSV, index=False)
    direction.to_csv(DIRECTION_CSV, index=False)
    AUDIT_MD.write_text(markdown_report(temporal, score_buckets, direction, q2, month_distribution, drawdown), encoding="utf-8")

    print(f"output_md={AUDIT_MD}")
    print(f"output_temporal={TEMPORAL_CSV}")
    print(f"output_score_buckets={SCORE_BUCKETS_CSV}")
    print(f"output_direction={DIRECTION_CSV}")
    print(temporal[temporal["period_type"].eq("year")].to_string(index=False))
    return 0


def load_trades() -> pd.DataFrame:
    if not INPUT_TRADES.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_TRADES}")
    df = pd.read_csv(INPUT_TRADES)
    df = df[df["priority_strategy"].eq(STRATEGY)].copy()
    if df.empty:
        raise ValueError(f"No trades found for strategy {STRATEGY}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["exit_timestamp"] = pd.to_datetime(df["exit_timestamp"], utc=True, errors="coerce")
    for col in ["adjusted_R", "gross_r", "priority_score", "spread_r", "commission_r", "slippage_r", "gaspar_p_deteriorating", "baltasar_confidence"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["year"] = df["timestamp"].dt.year.astype(str)
    df["quarter"] = df["timestamp"].dt.to_period("Q").astype(str)
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)
    df["date"] = df["timestamp"].dt.date.astype(str)
    df["is_2026q2"] = df["timestamp"].between(
        pd.Timestamp("2026-04-01 00:00:00", tz="UTC"),
        pd.Timestamp("2026-04-14 23:59:59", tz="UTC"),
    )
    return df.sort_values(["timestamp", "symbol", "prediction"]).reset_index(drop=True)


def build_temporal(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period_type, column in [("year", "year"), ("quarter", "quarter"), ("month", "month")]:
        for period, part in trades.groupby(column, dropna=False):
            rows.append(metric_row(period_type, str(period), part))
    rows.append(metric_row("special", "2026Q2", trades[trades["is_2026q2"]]))
    return pd.DataFrame(rows).sort_values(["period_type", "period"]).reset_index(drop=True)


def build_score_buckets(trades: pd.DataFrame) -> pd.DataFrame:
    out = trades.copy()
    quantile_edges = out["priority_score"].quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0]).to_numpy()
    quantile_edges = np.unique(quantile_edges)
    if len(quantile_edges) < 3:
        out["score_bucket"] = "all"
    else:
        out["score_bucket"] = pd.cut(
            out["priority_score"],
            bins=quantile_edges,
            include_lowest=True,
            duplicates="drop",
        ).astype(str)

    rows = []
    for bucket, part in out.groupby("score_bucket", dropna=False):
        row = metric_row("score_bucket", str(bucket), part)
        row["score_min"] = round_float(float(part["priority_score"].min()))
        row["score_max"] = round_float(float(part["priority_score"].max()))
        row["score_mean"] = round_float(float(part["priority_score"].mean()))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("score_min").reset_index(drop=True)


def build_direction_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for direction, part in trades.groupby("prediction", dropna=False):
        rows.append(metric_row("direction", str(direction), part))
    for year_direction, part in trades.groupby(["year", "prediction"], dropna=False):
        year, direction = year_direction
        row = metric_row("year_direction", f"{year}_{direction}", part)
        row["year"] = year
        row["direction"] = direction
        rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


def build_q2_detail(trades: pd.DataFrame) -> pd.DataFrame:
    q2 = trades[trades["is_2026q2"]].copy()
    rows = [metric_row("special", "2026Q2", q2)]
    for direction, part in q2.groupby("prediction", dropna=False):
        rows.append(metric_row("2026Q2_direction", str(direction), part))
    for date, part in q2.groupby("date", dropna=False):
        rows.append(metric_row("2026Q2_day", str(date), part))
    return pd.DataFrame(rows)


def build_month_distribution(trades: pd.DataFrame) -> pd.DataFrame:
    total = len(trades)
    rows = []
    for month, part in trades.groupby("month", dropna=False):
        row = metric_row("month_distribution", str(month), part)
        row["trade_share"] = round_float(float(len(part) / total) if total else 0.0)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("period").reset_index(drop=True)


def build_drawdown_temporal(trades: pd.DataFrame) -> pd.DataFrame:
    out = trades.sort_values("timestamp").copy()
    out["equity_r"] = out["adjusted_R"].cumsum()
    out["running_peak_r"] = out["equity_r"].cummax().clip(lower=0.0)
    out["drawdown_r"] = out["running_peak_r"] - out["equity_r"]
    out["trade_index"] = np.arange(1, len(out) + 1)
    monthly_dd = (
        out.groupby("month")
        .agg(
            trades=("adjusted_R", "size"),
            period_r=("adjusted_R", "sum"),
            end_equity_r=("equity_r", "last"),
            max_drawdown_seen_r=("drawdown_r", "max"),
        )
        .reset_index()
    )
    for col in ["period_r", "end_equity_r", "max_drawdown_seen_r"]:
        monthly_dd[col] = monthly_dd[col].map(round_float)
    return monthly_dd


def metric_row(period_type: str, period: str, frame: pd.DataFrame) -> dict[str, Any]:
    metrics = trade_metrics(frame)
    return {
        "period_type": period_type,
        "period": period,
        "trades": metrics["trades"],
        "avg_r": metrics["avg_r"],
        "total_r": metrics["total_r"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_r": metrics["max_drawdown_r"],
        "win_rate": metrics["win_rate"],
        "mean_score": round_float(float(frame["priority_score"].mean()) if len(frame) else 0.0),
        "mean_baltasar_confidence": round_float(float(frame["baltasar_confidence"].mean()) if len(frame) else 0.0),
        "mean_gaspar_p_deteriorating": round_float(float(frame["gaspar_p_deteriorating"].mean()) if len(frame) else 0.0),
    }


def trade_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    r = pd.to_numeric(frame.get("adjusted_R", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    trades = int(len(r))
    wins = r[r > 0]
    losses = r[r < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (math.inf if gross_profit > 0 else 0.0)
    return {
        "trades": trades,
        "avg_r": round_float(float(r.mean()) if trades else 0.0),
        "total_r": round_float(float(r.sum())),
        "profit_factor": round_float(pf),
        "max_drawdown_r": round_float(max_drawdown(r)),
        "win_rate": round_float(float((r > 0).mean()) if trades else 0.0),
    }


def markdown_report(
    temporal: pd.DataFrame,
    score_buckets: pd.DataFrame,
    direction: pd.DataFrame,
    q2: pd.DataFrame,
    month_distribution: pd.DataFrame,
    drawdown: pd.DataFrame,
) -> str:
    lines = [
        "# Online Priority Scoring Deep Audit",
        "",
        "## Scope",
        "",
        f"- Input: `{INPUT_TRADES}`.",
        f"- Strategy audited: `{STRATEGY}`.",
        "- Reglas sin cambios; solo diagnostico.",
        "",
        "## Por Año",
        "",
        table(temporal[temporal["period_type"].eq("year")]),
        "",
        "## Por Trimestre",
        "",
        table(temporal[temporal["period_type"].eq("quarter")]),
        "",
        "## Por Mes",
        "",
        table(temporal[temporal["period_type"].eq("month")]),
        "",
        "## BUY vs SELL",
        "",
        table(direction[direction["period_type"].eq("direction")]),
        "",
        "## Buckets de Score",
        "",
        score_bucket_table(score_buckets),
        "",
        "## 2026Q2 Detallado",
        "",
        table(q2),
        "",
        "## Distribucion de Trades por Mes",
        "",
        month_distribution_table(month_distribution),
        "",
        "## Drawdown Temporal",
        "",
        drawdown_table(drawdown),
        "",
        "## Lectura",
        "",
        interpretation(temporal, score_buckets, direction, q2, month_distribution, drawdown),
    ]
    return "\n".join(lines) + "\n"


def table(frame: pd.DataFrame) -> str:
    rows = ["| Segmento | Trades | PF | Avg R | DD | Win rate | Total R | Mean score |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['period']}` | {int(row['trades']):,} | {row['profit_factor']:.4f} | {row['avg_r']:.4f} | "
            f"{row['max_drawdown_r']:.2f} | {row['win_rate']:.2%} | {row['total_r']:.2f} | {row['mean_score']:.4f} |"
        )
    return "\n".join(rows)


def score_bucket_table(frame: pd.DataFrame) -> str:
    rows = [
        "| Bucket | Score min | Score max | Trades | PF | Avg R | DD | Total R |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['period']}` | {row['score_min']:.4f} | {row['score_max']:.4f} | {int(row['trades'])} | "
            f"{row['profit_factor']:.4f} | {row['avg_r']:.4f} | {row['max_drawdown_r']:.2f} | {row['total_r']:.2f} |"
        )
    return "\n".join(rows)


def month_distribution_table(frame: pd.DataFrame) -> str:
    rows = ["| Mes | Trades | Share | PF | Avg R | Total R |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['period']}` | {int(row['trades'])} | {row['trade_share']:.2%} | "
            f"{row['profit_factor']:.4f} | {row['avg_r']:.4f} | {row['total_r']:.2f} |"
        )
    return "\n".join(rows)


def drawdown_table(frame: pd.DataFrame) -> str:
    rows = ["| Mes | Trades | Period R | End equity R | Max DD seen |", "| --- | ---: | ---: | ---: | ---: |"]
    for _, row in frame.iterrows():
        rows.append(
            f"| `{row['month']}` | {int(row['trades'])} | {row['period_r']:.2f} | "
            f"{row['end_equity_r']:.2f} | {row['max_drawdown_seen_r']:.2f} |"
        )
    return "\n".join(rows)


def interpretation(
    temporal: pd.DataFrame,
    score_buckets: pd.DataFrame,
    direction: pd.DataFrame,
    q2: pd.DataFrame,
    month_distribution: pd.DataFrame,
    drawdown: pd.DataFrame,
) -> str:
    year = temporal[temporal["period_type"].eq("year")].sort_values("profit_factor", ascending=False)
    weak_quarter = temporal[temporal["period_type"].eq("quarter")].sort_values("profit_factor").iloc[0]
    weak_month = temporal[temporal["period_type"].eq("month")].sort_values("profit_factor").iloc[0]
    best_bucket = score_buckets.sort_values("profit_factor", ascending=False).iloc[0]
    worst_bucket = score_buckets.sort_values("profit_factor").iloc[0]
    q2_all = q2[q2["period"].eq("2026Q2")].iloc[0]
    max_dd_month = drawdown.sort_values("max_drawdown_seen_r", ascending=False).iloc[0]

    return (
        f"El edge aparece en ambos años de test: mejor año `{year.iloc[0]['period']}` con PF `{year.iloc[0]['profit_factor']:.4f}` "
        f"y peor año `{year.iloc[-1]['period']}` con PF `{year.iloc[-1]['profit_factor']:.4f}`. "
        f"Se debilita especialmente en `{weak_quarter['period']}` por trimestre y `{weak_month['period']}` por mes. "
        f"El mejor bucket de score fue `{best_bucket['period']}` con PF `{best_bucket['profit_factor']:.4f}`, mientras el peor fue "
        f"`{worst_bucket['period']}` con PF `{worst_bucket['profit_factor']:.4f}`. "
        f"2026Q2 queda casi plano: PF `{q2_all['profit_factor']:.4f}`, Avg R `{q2_all['avg_r']:.4f}`, Total R `{q2_all['total_r']:.2f}`. "
        f"El drawdown temporal maximo se observa alrededor de `{max_dd_month['month']}` con DD visto `{max_dd_month['max_drawdown_seen_r']:.2f}`."
    )


if __name__ == "__main__":
    raise SystemExit(main())
