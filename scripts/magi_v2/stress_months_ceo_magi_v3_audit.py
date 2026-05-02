from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd


INPUT_DECISIONS = Path("artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv")
OUTPUT_DIR = Path("artifacts/ceo_magi_v3")
AUDIT_CSV = OUTPUT_DIR / "stress_months_audit.csv"
DETAIL_CSV = OUTPUT_DIR / "stress_months_trade_detail.csv"
SUMMARY_MD = OUTPUT_DIR / "stress_months_summary.md"

STRESS_MONTHS = {
    "2020-03": "pandemia pico",
    "2022-04": "inflacion alta",
    "2026-04": "periodo problematico reciente",
}
SL_PIPS = 10.0


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    decisions = load_decisions()
    global_metrics = metrics_for_frame(decisions[decisions["action"].eq("ENTER")], "realized_R")
    monthly_rows = []
    detail_rows = []
    diagnostics: dict[str, dict[str, Any]] = {}

    for month, label in STRESS_MONTHS.items():
        month_all = decisions[decisions["month"].eq(month)].copy()
        month_enter = month_all[month_all["action"].eq("ENTER")].copy()
        baseline = metrics_for_frame(month_all, "hypothetical_adjusted_R")
        ceo = metrics_for_frame(month_enter, "realized_R")
        loss_diag = loss_clustering(month_enter)
        direction = direction_breakdown(month_enter)
        gates = gate_diagnostics(month_all)
        diagnostics[month] = {
            "label": label,
            "baseline": baseline,
            "ceo": ceo,
            "loss_clustering": loss_diag,
            "direction": direction,
            "gates": gates,
        }
        monthly_rows.append(
            {
                "month": month,
                "stress_label": label,
                **prefix("ceo_", ceo),
                **prefix("baseline_", baseline),
                "delta_total_r_vs_baseline": round_float(ceo["total_r"] - baseline["total_r"]),
                "delta_pf_vs_baseline": round_float(ceo["profit_factor"] - baseline["profit_factor"]),
                "delta_dd_vs_baseline": round_float(ceo["max_drawdown_r"] - baseline["max_drawdown_r"]),
                "loss_clusters_2plus": loss_diag["loss_clusters_2plus"],
                "max_loss_streak": loss_diag["max_loss_streak"],
                "melchor_blocks": gates["melchor_blocks"],
                "score_blocks": gates["score_blocks"],
                "gaspar_high_deterioration": gates["gaspar_high_deterioration"],
                "avg_gaspar_p_enter": gates["avg_gaspar_p_enter"],
                "avg_gaspar_p_blocked": gates["avg_gaspar_p_blocked"],
                "verdict": month_verdict(ceo, global_metrics),
            }
        )
        detail_rows.extend(build_detail_rows(month_enter))

    audit = pd.DataFrame(monthly_rows)
    detail = pd.DataFrame(detail_rows)
    audit.to_csv(AUDIT_CSV, index=False)
    detail.to_csv(DETAIL_CSV, index=False)
    SUMMARY_MD.write_text(markdown_report(audit, diagnostics, global_metrics), encoding="utf-8")

    print(f"output_audit={AUDIT_CSV}")
    print(f"output_detail={DETAIL_CSV}")
    print(f"output_summary={SUMMARY_MD}")
    for _, row in audit.iterrows():
        print(
            f"{row['month']} ceo_trades={int(row['ceo_trades'])} ceo_pf={row['ceo_profit_factor']} "
            f"ceo_avg_r={row['ceo_avg_r']} ceo_dd={row['ceo_max_drawdown_r']} verdict={row['verdict']}"
        )


def load_decisions() -> pd.DataFrame:
    if not INPUT_DECISIONS.exists():
        raise FileNotFoundError(f"Missing CEO-MAGI v3 decisions CSV: {INPUT_DECISIONS}")
    df = pd.read_csv(INPUT_DECISIONS)
    df["entry_time"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["exit_time"] = pd.to_datetime(df["exit_timestamp"], utc=True, errors="coerce")
    df["month"] = df["entry_time"].dt.tz_convert(None).dt.to_period("M").astype(str)
    for col in ["realized_R", "hypothetical_adjusted_R", "gross_r", "score", "gaspar_p_deteriorating", "entry_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["duration_minutes"] = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / 60.0
    df["net_pips"] = df["realized_R"] * SL_PIPS
    df["hypothetical_net_pips"] = df["hypothetical_adjusted_R"] * SL_PIPS
    df["gross_pips"] = df["gross_r"] * SL_PIPS
    return df.sort_values("entry_time").reset_index(drop=True)


def metrics_for_frame(frame: pd.DataFrame, r_column: str) -> dict[str, Any]:
    r = pd.to_numeric(frame.get(r_column, pd.Series(dtype=float)), errors="coerce").dropna()
    trades = int(len(r))
    wins = r[r > 0]
    losses = r[r < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (math.inf if gross_profit > 0 else 0.0)
    equity = r.cumsum()
    dd = equity.cummax() - equity
    duration = pd.to_numeric(frame.get("duration_minutes", pd.Series(dtype=float)), errors="coerce").dropna()
    gross_pips = pd.to_numeric(frame.get("gross_pips", pd.Series(dtype=float)), errors="coerce").dropna()
    pips_source = r * SL_PIPS
    return {
        "trades": trades,
        "winning_trades": int((r > 0).sum()),
        "losing_trades": int((r < 0).sum()),
        "breakeven_trades": int((r == 0).sum()),
        "win_rate": round_float(float((r > 0).mean()) if trades else 0.0),
        "gross_winning_pips": round_float(float(gross_pips[gross_pips > 0].sum()) if len(gross_pips) else float((wins * SL_PIPS).sum())),
        "gross_losing_pips": round_float(float(gross_pips[gross_pips < 0].sum()) if len(gross_pips) else float((losses * SL_PIPS).sum())),
        "net_pips": round_float(float(pips_source.sum()) if trades else 0.0),
        "avg_r": round_float(float(r.mean()) if trades else 0.0),
        "total_r": round_float(float(r.sum()) if trades else 0.0),
        "profit_factor": round_float(pf),
        "max_drawdown_r": round_float(float(dd.max()) if trades else 0.0),
        "avg_duration_minutes": round_float(float(duration.mean()) if len(duration) else 0.0),
        "min_duration_minutes": round_float(float(duration.min()) if len(duration) else 0.0),
        "max_duration_minutes": round_float(float(duration.max()) if len(duration) else 0.0),
        "avg_duration": format_duration(float(duration.mean()) if len(duration) else None),
        "min_duration": format_duration(float(duration.min()) if len(duration) else None),
        "max_duration": format_duration(float(duration.max()) if len(duration) else None),
    }


def loss_clustering(frame: pd.DataFrame) -> dict[str, Any]:
    r = pd.to_numeric(frame["realized_R"], errors="coerce").dropna().tolist()
    streaks = []
    current = 0
    for value in r:
        if value < 0:
            current += 1
        else:
            if current:
                streaks.append(current)
            current = 0
    if current:
        streaks.append(current)
    return {
        "loss_clusters_2plus": int(sum(1 for item in streaks if item >= 2)),
        "max_loss_streak": int(max(streaks) if streaks else 0),
        "loss_streaks": streaks,
    }


def direction_breakdown(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    out = {}
    for direction in ["BUY", "SELL"]:
        out[direction] = metrics_for_frame(frame[frame["direction"].eq(direction)], "realized_R")
    return out


def gate_diagnostics(month_all: pd.DataFrame) -> dict[str, Any]:
    blocked = month_all[month_all["action"].eq("DO_NOTHING")]
    enter = month_all[month_all["action"].eq("ENTER")]
    melchor = blocked[blocked["reason_code"].eq("melchor_block")]
    score = blocked[blocked["reason_code"].eq("score_below_0_20")]
    return {
        "candidate_decisions": int(len(month_all)),
        "enter": int(len(enter)),
        "do_nothing": int(len(blocked)),
        "melchor_blocks": int(len(melchor)),
        "score_blocks": int(len(score)),
        "gaspar_high_deterioration": int(month_all["gaspar_p_deteriorating"].ge(0.70).sum()),
        "avg_gaspar_p_enter": round_float(float(enter["gaspar_p_deteriorating"].mean()) if len(enter) else 0.0),
        "avg_gaspar_p_blocked": round_float(float(blocked["gaspar_p_deteriorating"].mean()) if len(blocked) else 0.0),
        "blocked_hypothetical_total_r": round_float(float(blocked["hypothetical_adjusted_R"].sum()) if len(blocked) else 0.0),
        "melchor_blocked_hypothetical_total_r": round_float(float(melchor["hypothetical_adjusted_R"].sum()) if len(melchor) else 0.0),
        "score_blocked_hypothetical_total_r": round_float(float(score["hypothetical_adjusted_R"].sum()) if len(score) else 0.0),
    }


def build_detail_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "month": row["month"],
                "entry_time": timestamp_str(row["entry_time"]),
                "exit_time": timestamp_str(row["exit_time"]),
                "symbol": row["symbol"],
                "direction": row["direction"],
                "entry_price": row["entry_price"],
                "result": result_label(row["realized_R"]),
                "realized_R": round_float(row["realized_R"]),
                "net_pips": round_float(row["net_pips"]),
                "gross_pips": round_float(row["gross_pips"]),
                "duration_minutes": round_float(row["duration_minutes"]),
                "duration": format_duration(row["duration_minutes"]),
                "aggression_mode": row["aggression_mode"],
                "score": round_float(row["score"]),
                "reason_code": row["reason_code"],
                "gaspar_p_deteriorating": round_float(row["gaspar_p_deteriorating"]),
                "melchor_signal": row["melchor_signal"],
                "decision_id": row["decision_id"],
                "split": row["split"],
            }
        )
    return rows


def markdown_report(audit: pd.DataFrame, diagnostics: dict[str, dict[str, Any]], global_metrics: dict[str, Any]) -> str:
    lines = [
        "# CEO-MAGI v3 Stress Months Audit",
        "",
        "## Scope",
        "",
        "- Months: `2020-03`, `2022-04`, `2026-04`.",
        "- Universe: only CEO-MAGI v3 approved `ENTER` operations for primary metrics.",
        "- Baseline comparison: all candidate decisions in the same month using `hypothetical_adjusted_R` before CEO filtering.",
        "- No models, rules, Bot B, or MT5 were modified.",
        "",
        "## Global Reference",
        "",
        f"- Global CEO ENTER PF: `{fmt(global_metrics['profit_factor'])}`",
        f"- Global CEO ENTER Avg R: `{global_metrics['avg_r']:.4f}`",
        f"- Global CEO ENTER Max DD: `{global_metrics['max_drawdown_r']:.2f}R`",
        f"- Global CEO ENTER win rate: `{global_metrics['win_rate']:.2%}`",
        "",
        "## Stress Month Summary",
        "",
        summary_table(audit),
        "",
        "## Baseline Comparison",
        "",
        baseline_table(audit),
        "",
        "## Direction Breakdown",
        "",
    ]
    for month in STRESS_MONTHS:
        lines.extend([f"### {month} - {STRESS_MONTHS[month]}", "", direction_table(diagnostics[month]["direction"]), ""])

    lines.extend(["## Gate Diagnostics", "", gate_table(diagnostics), "", "## Interpretation", ""])
    lines.extend(interpretation_lines(audit, diagnostics, global_metrics))
    lines.extend(
        [
            "",
            "## Module Readout",
            "",
            module_readout(diagnostics),
            "",
            "## Limitations",
            "",
            "- `exit_price` is not available in the CEO-MAGI v3 artifacts, so exit price geometry is not audited here.",
            f"- Pips are pip-equivalent values using the validated fixed `SL={SL_PIPS:.0f}` pips convention.",
            "- 2026-04 has very few approved entries, so its metrics are directionally useful but statistically weak.",
            "",
            "## Generated Files",
            "",
            f"- `{AUDIT_CSV}`",
            f"- `{DETAIL_CSV}`",
            f"- `{SUMMARY_MD}`",
            "",
        ]
    )
    return "\n".join(lines)


def summary_table(audit: pd.DataFrame) -> str:
    rows = [
        "| Month | Stress | Ops | Wins | Losses | WR | Gross +pips | Gross -pips | Net pips | Avg R | PF | Max DD | Avg dur | Verdict |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for _, row in audit.iterrows():
        rows.append(
            f"| `{row['month']}` | {row['stress_label']} | {int(row['ceo_trades'])} | {int(row['ceo_winning_trades'])} | "
            f"{int(row['ceo_losing_trades'])} | {row['ceo_win_rate']:.2%} | {row['ceo_gross_winning_pips']:.1f} | "
            f"{row['ceo_gross_losing_pips']:.1f} | {row['ceo_net_pips']:.1f} | {row['ceo_avg_r']:.4f} | "
            f"{fmt(row['ceo_profit_factor'])} | {row['ceo_max_drawdown_r']:.2f} | {row['ceo_avg_duration']} | `{row['verdict']}` |"
        )
    return "\n".join(rows)


def baseline_table(audit: pd.DataFrame) -> str:
    rows = [
        "| Month | CEO Total R | Baseline Total R | Delta R | CEO PF | Baseline PF | CEO DD | Baseline DD | Better than baseline? |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in audit.iterrows():
        better = row["ceo_total_r"] > row["baseline_total_r"] and row["ceo_max_drawdown_r"] <= row["baseline_max_drawdown_r"]
        rows.append(
            f"| `{row['month']}` | {row['ceo_total_r']:.2f} | {row['baseline_total_r']:.2f} | "
            f"{row['delta_total_r_vs_baseline']:.2f} | {fmt(row['ceo_profit_factor'])} | {fmt(row['baseline_profit_factor'])} | "
            f"{row['ceo_max_drawdown_r']:.2f} | {row['baseline_max_drawdown_r']:.2f} | `{'yes' if better else 'mixed/no'}` |"
        )
    return "\n".join(rows)


def direction_table(direction: dict[str, dict[str, Any]]) -> str:
    rows = ["| Direction | Ops | WR | Avg R | PF | Total R | Max DD |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for side, m in direction.items():
        rows.append(f"| `{side}` | {m['trades']} | {m['win_rate']:.2%} | {m['avg_r']:.4f} | {fmt(m['profit_factor'])} | {m['total_r']:.2f} | {m['max_drawdown_r']:.2f} |")
    return "\n".join(rows)


def gate_table(diagnostics: dict[str, dict[str, Any]]) -> str:
    rows = [
        "| Month | Candidates | ENTER | DO_NOTHING | Melchor blocks | Score blocks | Blocked hypothetical R | Gaspar high det. | Avg Gaspar ENTER | Avg Gaspar blocked |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for month, d in diagnostics.items():
        g = d["gates"]
        rows.append(
            f"| `{month}` | {g['candidate_decisions']} | {g['enter']} | {g['do_nothing']} | {g['melchor_blocks']} | "
            f"{g['score_blocks']} | {g['blocked_hypothetical_total_r']:.2f} | {g['gaspar_high_deterioration']} | "
            f"{g['avg_gaspar_p_enter']:.4f} | {g['avg_gaspar_p_blocked']:.4f} |"
        )
    return "\n".join(rows)


def interpretation_lines(audit: pd.DataFrame, diagnostics: dict[str, dict[str, Any]], global_metrics: dict[str, Any]) -> list[str]:
    lines = []
    for _, row in audit.iterrows():
        month = row["month"]
        d = diagnostics[month]
        survives = row["ceo_total_r"] > 0 and row["ceo_profit_factor"] > 1
        loses = row["ceo_total_r"] < 0
        better_pf = row["ceo_profit_factor"] > row["baseline_profit_factor"]
        better_dd = row["ceo_max_drawdown_r"] < row["baseline_max_drawdown_r"]
        lines.append(
            f"- `{month}`: {'survives' if survives else 'does not survive cleanly'}; "
            f"{'loses money' if loses else 'does not lose money'}; DD `{row['ceo_max_drawdown_r']:.2f}R`. "
            f"Compared with baseline: PF {'improves' if better_pf else 'does not improve'}, DD {'improves' if better_dd else 'does not improve'}. "
            f"Max loss streak `{d['loss_clustering']['max_loss_streak']}`."
        )
    return lines


def module_readout(diagnostics: dict[str, dict[str, Any]]) -> str:
    melchor_total = sum(d["gates"]["melchor_blocks"] for d in diagnostics.values())
    score_total = sum(d["gates"]["score_blocks"] for d in diagnostics.values())
    gaspar_high = sum(d["gates"]["gaspar_high_deterioration"] for d in diagnostics.values())
    blocked_r = sum(d["gates"]["blocked_hypothetical_total_r"] for d in diagnostics.values())
    return (
        f"Scoring is the most active gate in these stress months (`{score_total}` score blocks), while Melchor blocks `{melchor_total}` "
        f"trades. The blocked trades had combined hypothetical R `{blocked_r:.2f}`, so the gates were not merely cosmetic. "
        f"Gaspar did not trigger the high-deterioration downgrade (`{gaspar_high}` cases >= 0.70), but it still contributes inside the score penalty."
    )


def month_verdict(ceo: dict[str, Any], global_metrics: dict[str, Any]) -> str:
    if ceo["trades"] == 0:
        return "no_sample"
    if ceo["profit_factor"] < 1 or ceo["avg_r"] < 0:
        return "stress_failure"
    if ceo["profit_factor"] < global_metrics["profit_factor"] * 0.75 or ceo["avg_r"] < global_metrics["avg_r"] * 0.75:
        return "degrades_but_survives"
    return "survives"


def prefix(prefix_text: str, values: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix_text}{key}": value for key, value in values.items()}


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


def timestamp_str(value: Any) -> str:
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return ""
    return ts.isoformat().replace("+00:00", "Z")


def format_duration(minutes: Any) -> str:
    if minutes is None or pd.isna(minutes):
        return ""
    total = int(round(float(minutes)))
    hours, mins = divmod(total, 60)
    if hours:
        return f"{hours}h {mins:02d}m"
    return f"{mins}m"


def round_float(value: Any, digits: int = 6) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isinf(number):
        return number
    if math.isnan(number):
        return 0.0
    return round(number, digits)


def fmt(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0.0000"
    if math.isinf(number):
        return "inf"
    return f"{number:.4f}"


if __name__ == "__main__":
    main()
