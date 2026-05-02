from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


DETAIL_CSV = Path("artifacts/ceo_magi_v3/random_3_months_trade_audit.csv")
SUMMARY_CSV = Path("artifacts/ceo_magi_v3/random_3_months_monthly_summary.csv")
SOURCE_DECISIONS = Path("artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv")
OUTPUT_DIR = Path("artifacts/ceo_magi_v3")
REPORT_MD = OUTPUT_DIR / "audit_of_audit_report.md"
DIFFERENCES_CSV = OUTPUT_DIR / "audit_of_audit_differences.csv"

SL_PIPS = 10.0
TOLERANCE = 1e-4


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    detail = load_detail()
    summary = load_summary()
    source = load_source()

    selected_months = sorted(detail["month"].astype(str).unique())
    recalculated = recalc_monthly(detail)
    differences = compare_summary(summary, recalculated)
    duplicate_rows = detect_duplicates(detail)
    missing_rows, extra_rows = compare_against_source(detail, source, selected_months)
    pips_checks = validate_pips(detail)
    duration_checks = validate_duration(detail, source)
    bias = bias_analysis(source, selected_months)

    all_differences = pd.concat(
        [differences, duplicate_rows, missing_rows, extra_rows, pips_checks, duration_checks],
        ignore_index=True,
    )
    if all_differences.empty:
        all_differences = pd.DataFrame(columns=["severity", "month", "field", "check", "actual", "expected", "note"])
    all_differences.to_csv(DIFFERENCES_CSV, index=False)
    REPORT_MD.write_text(
        markdown_report(selected_months, all_differences, recalculated, summary, bias),
        encoding="utf-8",
    )

    print(f"selected_months={','.join(selected_months)}")
    print(f"difference_rows={len(all_differences)}")
    print(f"critical_issues={int(all_differences['severity'].eq('ERROR').sum()) if len(all_differences) else 0}")
    print(f"warnings={int(all_differences['severity'].eq('WARNING').sum()) if len(all_differences) else 0}")
    print(f"output_report={REPORT_MD}")
    print(f"output_differences={DIFFERENCES_CSV}")


def load_detail() -> pd.DataFrame:
    if not DETAIL_CSV.exists():
        raise FileNotFoundError(f"Missing detail audit CSV: {DETAIL_CSV}")
    df = pd.read_csv(DETAIL_CSV)
    df["entry_time"] = pd.to_datetime(df["entry_datetime"], utc=True, errors="coerce")
    for col in ["net_pips", "gross_pips", "duration_minutes", "realized_R", "gross_r"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_summary() -> pd.DataFrame:
    if not SUMMARY_CSV.exists():
        raise FileNotFoundError(f"Missing monthly summary CSV: {SUMMARY_CSV}")
    return pd.read_csv(SUMMARY_CSV)


def load_source() -> pd.DataFrame:
    if not SOURCE_DECISIONS.exists():
        raise FileNotFoundError(f"Missing CEO-MAGI v3 source decisions: {SOURCE_DECISIONS}")
    df = pd.read_csv(SOURCE_DECISIONS)
    df = df[df["action"].eq("ENTER")].copy()
    df["entry_time"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["exit_time"] = pd.to_datetime(df["exit_timestamp"], utc=True, errors="coerce")
    df["month"] = df["entry_time"].dt.tz_convert(None).dt.to_period("M").astype(str)
    df["realized_R"] = pd.to_numeric(df["realized_R"], errors="coerce")
    df["gross_r"] = pd.to_numeric(df["gross_r"], errors="coerce")
    df["net_pips"] = df["realized_R"] * SL_PIPS
    df["gross_pips"] = df["gross_r"] * SL_PIPS
    df["duration_minutes_recalc"] = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / 60.0
    df["result_recalc"] = df["realized_R"].apply(result_label)
    return df


def recalc_monthly(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for month, part in detail.groupby("month", sort=True):
        trades = int(len(part))
        wins = int(part["realized_R"].gt(0).sum())
        losses = int(part["realized_R"].lt(0).sum())
        be = int(part["realized_R"].eq(0).sum())
        gross = part["gross_pips"].fillna(0.0)
        net = part["net_pips"].fillna(0.0)
        duration = part["duration_minutes"].dropna()
        rows.append(
            {
                "month": month,
                "trades_executed": trades,
                "winning_trades": wins,
                "losing_trades": losses,
                "breakeven_trades": be,
                "win_rate": round_float(wins / trades if trades else 0.0),
                "gross_winning_pips": round_float(float(gross[gross > 0].sum())),
                "gross_losing_pips": round_float(float(gross[gross < 0].sum())),
                "net_pips_month": round_float(float(net.sum())),
                "avg_duration_minutes": round_float(float(duration.mean()) if len(duration) else 0.0),
                "min_duration_minutes": round_float(float(duration.min()) if len(duration) else 0.0),
                "max_duration_minutes": round_float(float(duration.max()) if len(duration) else 0.0),
            }
        )
    return pd.DataFrame(rows)


def compare_summary(summary: pd.DataFrame, recalculated: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    cols = [
        "trades_executed",
        "winning_trades",
        "losing_trades",
        "breakeven_trades",
        "win_rate",
        "gross_winning_pips",
        "gross_losing_pips",
        "net_pips_month",
        "avg_duration_minutes",
        "min_duration_minutes",
        "max_duration_minutes",
    ]
    merged = summary.merge(recalculated, on="month", how="outer", suffixes=("_summary", "_recalc"), indicator=True)
    for _, row in merged.iterrows():
        month = row["month"]
        if row["_merge"] != "both":
            rows.append(issue("ERROR", month, "summary_presence", "month_missing_in_one_side", row["_merge"], "both", "Month missing in summary or recalculation."))
            continue
        for col in cols:
            actual = row[f"{col}_summary"]
            expected = row[f"{col}_recalc"]
            diff = numeric_diff(actual, expected)
            if abs(diff) > TOLERANCE:
                rows.append(issue("ERROR", month, col, "summary_recalculation_mismatch", actual, expected, f"Difference={diff:.8f}"))
    return pd.DataFrame(rows)


def detect_duplicates(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for col in ["decision_id"]:
        dup = detail[detail.duplicated(col, keep=False)]
        if not dup.empty:
            rows.append(issue("ERROR", "ALL", col, "duplicate_trades", int(len(dup)), 0, f"Duplicate rows by {col}."))
    multi_key = ["entry_datetime", "symbol", "direction", "entry_price"]
    dup = detail[detail.duplicated(multi_key, keep=False)]
    if not dup.empty:
        rows.append(issue("WARNING", "ALL", "trade_key", "potential_duplicate_trade_key", int(len(dup)), 0, "Repeated entry-time/symbol/direction/entry key."))
    return pd.DataFrame(rows)


def compare_against_source(detail: pd.DataFrame, source: pd.DataFrame, selected_months: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    src = source[source["month"].isin(selected_months)].copy()
    detail_ids = set(detail["decision_id"].astype(str))
    source_ids = set(src["decision_id"].astype(str))
    missing = sorted(source_ids - detail_ids)
    extra = sorted(detail_ids - source_ids)
    missing_rows = [
        issue("ERROR", "ALL", "decision_id", "trade_missing_from_audit", len(missing), 0, f"Missing approved ENTER trades from selected months. Examples: {missing[:5]}")
    ] if missing else []
    extra_rows = [
        issue("ERROR", "ALL", "decision_id", "trade_not_found_in_source", len(extra), 0, f"Audit contains trades not found in source. Examples: {extra[:5]}")
    ] if extra else []
    return pd.DataFrame(missing_rows), pd.DataFrame(extra_rows)


def validate_pips(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    net_expected = detail["realized_R"] * SL_PIPS
    gross_expected = detail["gross_r"] * SL_PIPS
    net_diff = (detail["net_pips"] - net_expected).abs()
    gross_diff = (detail["gross_pips"] - gross_expected).abs()
    if (net_diff > TOLERANCE).any():
        rows.append(issue("ERROR", "ALL", "net_pips", "net_pips_formula_mismatch", int((net_diff > TOLERANCE).sum()), 0, "Expected net_pips = realized_R * 10."))
    if (gross_diff > TOLERANCE).any():
        rows.append(issue("ERROR", "ALL", "gross_pips", "gross_pips_formula_mismatch", int((gross_diff > TOLERANCE).sum()), 0, "Expected gross_pips = gross_r * 10."))
    outliers = detail[detail["net_pips"].abs() > 50]
    if not outliers.empty:
        rows.append(issue("WARNING", "ALL", "net_pips", "net_pips_outlier_gt_50", int(len(outliers)), 0, "Trades with absolute net pips > 50."))
    return pd.DataFrame(rows)


def validate_duration(detail: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    src = source[["decision_id", "duration_minutes_recalc"]].copy()
    merged = detail.merge(src, on="decision_id", how="left")
    diff = (merged["duration_minutes"] - merged["duration_minutes_recalc"]).abs()
    if merged["duration_minutes_recalc"].isna().any():
        rows.append(issue("ERROR", "ALL", "duration", "missing_source_duration", int(merged["duration_minutes_recalc"].isna().sum()), 0, "Source duration missing."))
    if (diff > TOLERANCE).any():
        rows.append(issue("ERROR", "ALL", "duration", "duration_recalculation_mismatch", int((diff > TOLERANCE).sum()), 0, "Duration differs from timestamp/exit_timestamp recalculation."))
    if (merged["duration_minutes"] < 0).any():
        rows.append(issue("ERROR", "ALL", "duration", "negative_duration", int((merged["duration_minutes"] < 0).sum()), 0, "Negative trade duration."))
    if (merged["duration_minutes"] == 0).any():
        rows.append(issue("WARNING", "ALL", "duration", "zero_duration", int((merged["duration_minutes"] == 0).sum()), 0, "Zero-minute trade duration."))
    return pd.DataFrame(rows)


def bias_analysis(source: pd.DataFrame, selected_months: list[str]) -> dict[str, Any]:
    monthly = monthly_metrics_from_source(source)
    selected = monthly[monthly["month"].isin(selected_months)].copy()
    rest = monthly[~monthly["month"].isin(selected_months)].copy()
    selected_agg = aggregate_months(source[source["month"].isin(selected_months)])
    rest_agg = aggregate_months(source[~source["month"].isin(selected_months)])
    all_agg = aggregate_months(source)
    percentiles = {}
    for metric in ["net_pips_month", "win_rate", "trades_executed", "avg_duration_minutes"]:
        selected_mean = float(selected[metric].mean()) if len(selected) else 0.0
        percentiles[metric] = percentile_rank(monthly[metric], selected_mean)
    return {
        "monthly_all": monthly,
        "selected_months": selected,
        "selected_aggregate": selected_agg,
        "rest_aggregate": rest_agg,
        "all_aggregate": all_agg,
        "percentile_ranks_of_selected_mean": percentiles,
    }


def monthly_metrics_from_source(source: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month, part in source.groupby("month", sort=True):
        rows.append(month_summary_row(month, part))
    return pd.DataFrame(rows)


def aggregate_months(frame: pd.DataFrame) -> dict[str, Any]:
    return month_summary_row("AGG", frame)


def month_summary_row(month: str, frame: pd.DataFrame) -> dict[str, Any]:
    trades = int(len(frame))
    wins = int(frame["realized_R"].gt(0).sum())
    losses = int(frame["realized_R"].lt(0).sum())
    gross = frame["gross_pips"].fillna(0.0)
    net = frame["net_pips"].fillna(0.0)
    duration = frame["duration_minutes_recalc"].dropna()
    return {
        "month": month,
        "trades_executed": trades,
        "winning_trades": wins,
        "losing_trades": losses,
        "win_rate": round_float(wins / trades if trades else 0.0),
        "gross_winning_pips": round_float(float(gross[gross > 0].sum())),
        "gross_losing_pips": round_float(float(gross[gross < 0].sum())),
        "net_pips_month": round_float(float(net.sum())),
        "avg_duration_minutes": round_float(float(duration.mean()) if len(duration) else 0.0),
    }


def markdown_report(
    selected_months: list[str],
    issues: pd.DataFrame,
    recalculated: pd.DataFrame,
    summary: pd.DataFrame,
    bias: dict[str, Any],
) -> str:
    error_count = int(issues["severity"].eq("ERROR").sum()) if len(issues) else 0
    warning_count = int(issues["severity"].eq("WARNING").sum()) if len(issues) else 0
    numbers_correct = error_count == 0
    bias_text = bias_verdict(bias)
    reliability = reliability_verdict(error_count, warning_count, bias_text)
    lines = [
        "# Audit of 3-Month CEO-MAGI v3 Audit",
        "",
        "## Executive Answer",
        "",
        f"- Numbers correct: `{'yes' if numbers_correct else 'no'}`",
        f"- Critical mismatches found: `{error_count}`",
        f"- Warnings found: `{warning_count}`",
        f"- Inflation detected: `{'no' if numbers_correct else 'possible'}`",
        f"- Bias verdict: {bias_text}",
        f"- Reliability: {reliability}",
        "",
        "## Selected Months",
        "",
        "- " + ", ".join(f"`{month}`" for month in selected_months),
        f"- Non-continuous: `{'yes' if not has_continuous_months(selected_months) else 'no'}`",
        "",
        "## Consistency Validation",
        "",
        issue_summary_table(issues),
        "",
        "## Recalculated Monthly Metrics",
        "",
        monthly_table(recalculated),
        "",
        "## Summary Comparison",
        "",
        comparison_table(summary, recalculated),
        "",
        "## Bias Validation",
        "",
        bias_table(bias),
        "",
        "## Interpretation",
        "",
        interpretation(numbers_correct, bias),
        "",
        "## Potential Errors",
        "",
        "- `exit_price` is unavailable in the source files, so this audit cannot validate exit price geometry.",
        "- Pips are pip-equivalent values derived from R with fixed `SL=10 pips`; they are not broker-reported pip PnL.",
        "- The selected months are random and non-continuous, but they are not a statistically complete walk-forward sample.",
        "",
        "## Generated Files",
        "",
        f"- `{REPORT_MD}`",
        f"- `{DIFFERENCES_CSV}`",
        "",
    ]
    return "\n".join(lines)


def issue_summary_table(issues: pd.DataFrame) -> str:
    if issues.empty:
        return "No consistency, formula, duplicate, missing-trade, pips, or duration errors were found."
    rows = ["| Severity | Month | Field | Check | Actual | Expected | Note |", "| --- | --- | --- | --- | ---: | ---: | --- |"]
    for _, row in issues.iterrows():
        rows.append(f"| `{row['severity']}` | `{row['month']}` | `{row['field']}` | `{row['check']}` | {row['actual']} | {row['expected']} | {row['note']} |")
    return "\n".join(rows)


def monthly_table(frame: pd.DataFrame) -> str:
    rows = ["| Month | Ops | Wins | Losses | Win rate | Gross win pips | Gross loss pips | Net pips | Avg duration min |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for _, row in frame.iterrows():
        rows.append(f"| `{row['month']}` | {int(row['trades_executed'])} | {int(row['winning_trades'])} | {int(row['losing_trades'])} | {row['win_rate']:.2%} | {row['gross_winning_pips']:.1f} | {row['gross_losing_pips']:.1f} | {row['net_pips_month']:.1f} | {row['avg_duration_minutes']:.1f} |")
    return "\n".join(rows)


def comparison_table(summary: pd.DataFrame, recalculated: pd.DataFrame) -> str:
    merged = summary.merge(recalculated, on="month", suffixes=("_summary", "_recalc"))
    rows = ["| Month | Ops diff | Win rate diff | Net pips diff | Avg duration diff |", "| --- | ---: | ---: | ---: | ---: |"]
    for _, row in merged.iterrows():
        rows.append(
            f"| `{row['month']}` | "
            f"{numeric_diff(row['trades_executed_summary'], row['trades_executed_recalc']):.4f} | "
            f"{numeric_diff(row['win_rate_summary'], row['win_rate_recalc']):.6f} | "
            f"{numeric_diff(row['net_pips_month_summary'], row['net_pips_month_recalc']):.6f} | "
            f"{numeric_diff(row['avg_duration_minutes_summary'], row['avg_duration_minutes_recalc']):.6f} |"
        )
    return "\n".join(rows)


def bias_table(bias: dict[str, Any]) -> str:
    selected = bias["selected_aggregate"]
    rest = bias["rest_aggregate"]
    all_ = bias["all_aggregate"]
    p = bias["percentile_ranks_of_selected_mean"]
    rows = [
        "| Group | Ops | Win rate | Net pips | Avg duration min |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Selected 3 months | {selected['trades_executed']} | {selected['win_rate']:.2%} | {selected['net_pips_month']:.1f} | {selected['avg_duration_minutes']:.1f} |",
        f"| Rest of dataset | {rest['trades_executed']} | {rest['win_rate']:.2%} | {rest['net_pips_month']:.1f} | {rest['avg_duration_minutes']:.1f} |",
        f"| Full dataset | {all_['trades_executed']} | {all_['win_rate']:.2%} | {all_['net_pips_month']:.1f} | {all_['avg_duration_minutes']:.1f} |",
        "",
        "| Selected mean percentile vs all monthly distribution | Percentile |",
        "| --- | ---: |",
    ]
    for key, value in p.items():
        rows.append(f"| `{key}` | {value:.2%} |")
    return "\n".join(rows)


def interpretation(numbers_correct: bool, bias: dict[str, Any]) -> str:
    selected = bias["selected_aggregate"]
    rest = bias["rest_aggregate"]
    selected_wr = selected["win_rate"]
    rest_wr = rest["win_rate"]
    selected_avg_net = selected["net_pips_month"] / max(1, len(bias["selected_months"]))
    monthly = bias["monthly_all"]
    net_pct = percentile_rank(monthly["net_pips_month"], selected_avg_net)
    parts = []
    if numbers_correct:
        parts.append("The monthly arithmetic is internally consistent: counts, win rate, pips, and duration recompute back to the published summary.")
    else:
        parts.append("The monthly arithmetic has mismatches and should not be used until reviewed.")
    if selected_wr > rest_wr:
        parts.append(f"The selected months have a higher aggregate win rate than the rest of the dataset ({selected_wr:.2%} vs {rest_wr:.2%}).")
    else:
        parts.append(f"The selected months do not outperform the rest by win rate ({selected_wr:.2%} vs {rest_wr:.2%}).")
    parts.append(f"The selected average monthly net pips sits around the {net_pct:.0%} percentile of all CEO-MAGI v3 ENTER months.")
    return " ".join(parts)


def bias_verdict(bias: dict[str, Any]) -> str:
    p = bias["percentile_ranks_of_selected_mean"]
    net = p["net_pips_month"]
    wr = p["win_rate"]
    if net >= 0.80 and wr >= 0.70:
        return "`selected months are materially above average; sample is optimistic`"
    if net <= 0.20 and wr <= 0.30:
        return "`selected months are materially below average; sample is pessimistic`"
    return "`selected months are not extreme, but still only a small sample`"


def reliability_verdict(error_count: int, warning_count: int, bias_text: str) -> str:
    if error_count:
        return "`low until mismatches are resolved`"
    if "optimistic" in bias_text or "pessimistic" in bias_text:
        return "`arithmetically reliable, but not representative enough for conclusions`"
    if warning_count:
        return "`mostly reliable with noted limitations`"
    return "`arithmetically reliable for describing these 3 months only`"


def percentile_rank(series: pd.Series, value: float) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    return float((clean <= value).mean())


def has_continuous_months(months: list[str]) -> bool:
    periods = sorted(pd.Period(month, freq="M") for month in months)
    return any((b.ordinal - a.ordinal) == 1 for a, b in zip(periods, periods[1:]))


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


def issue(severity: str, month: str, field: str, check: str, actual: Any, expected: Any, note: str) -> dict[str, Any]:
    return {
        "severity": severity,
        "month": month,
        "field": field,
        "check": check,
        "actual": actual,
        "expected": expected,
        "note": note,
    }


def numeric_diff(actual: Any, expected: Any) -> float:
    try:
        return float(actual) - float(expected)
    except (TypeError, ValueError):
        return 0.0 if str(actual) == str(expected) else float("inf")


def round_float(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


if __name__ == "__main__":
    main()
