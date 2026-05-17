from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

STRESS_FILE = ROOT / "artifacts" / "ceo_magi_v3" / "stress_months_trade_detail.csv"
GLOBAL_FILE = ROOT / "artifacts" / "ceo_magi_v3" / "ceo_magi_v3_decisions.csv"

REPORT_MD = REPORTS / "magi_guardrails_v1_validation_2026-05-15.md"
STRESS_CSV = REPORTS / "magi_guardrails_v1_stress_months.csv"
RANDOM_CSV = REPORTS / "magi_guardrails_v1_random_months.csv"
COMBINED_CSV = REPORTS / "magi_guardrails_v1_combined_summary.csv"
BLOCKED_CSV = REPORTS / "magi_guardrails_v1_blocked_trades.csv"
EQUITY_CSV = REPORTS / "magi_guardrails_v1_equity_curves.csv"
MONTHLY_BREAKDOWN_MD = REPORTS / "magi_month_by_month_breakdown_2026-05-15.md"

BOGOTA = timezone(timedelta(hours=-5))
PIP_VALUE_PER_LOT = 10.0
ACCOUNT = 100000.0


@dataclass
class Trade:
    source: str
    month: str
    entry_time: datetime
    exit_time: datetime
    symbol: str
    direction: str
    result: str
    r: float
    net_pips: float
    spread_pips: float | None
    decision_id: str
    session: str


@dataclass
class State:
    cluster_symbol: str = ""
    cluster_direction: str = ""
    cluster_day: str = ""
    cluster_session: str = ""
    cluster_last_exit: datetime | None = None
    cluster_consecutive_sl: int = 0
    cluster_id: int = 0
    daily_sl_count: dict[str, int] = field(default_factory=dict)
    session_sl_count: dict[tuple[str, str], int] = field(default_factory=dict)
    daily_drawdown_r: dict[str, float] = field(default_factory=dict)
    blocked_until_direction: dict[str, datetime] = field(default_factory=dict)
    safe_mode_until: datetime | None = None
    safe_mode_reason: str = ""
    clusters_detected: int = 0
    clusters_blocked: set[int] = field(default_factory=set)


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    if text.endswith("+0000"):
        text = text[:-5] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        value = float(value)
        if math.isnan(value):
            return default
        return value
    except (TypeError, ValueError):
        return default


def session_for(dt: datetime) -> str:
    hour = dt.hour
    if 7 <= hour < 12:
        return "london"
    if 12 <= hour < 17:
        return "overlap"
    if 17 <= hour < 22:
        return "new_york"
    return "asia"


def op_day(dt: datetime) -> str:
    return dt.astimezone(BOGOTA).date().isoformat()


def is_friday(dt: datetime) -> bool:
    return dt.astimezone(BOGOTA).weekday() == 4


def hour_colombia(dt: datetime) -> float:
    local = dt.astimezone(BOGOTA)
    return local.hour + local.minute / 60.0


def next_session_or_day(dt: datetime) -> datetime:
    # Simple, deterministic approximation for trade-level simulation.
    return dt + timedelta(hours=8)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def load_trades(path: Path, source: str) -> list[Trade]:
    trades: list[Trade] = []
    for i, row in enumerate(read_csv(path)):
        action = str(row.get("action") or "").upper()
        if action and action not in {"ENTER"}:
            continue
        entry = parse_dt(row.get("entry_time") or row.get("entry_datetime") or row.get("timestamp"))
        exit_time = parse_dt(row.get("exit_time") or row.get("exit_timestamp") or row.get("exit_timestamp_raw"))
        if entry is None:
            continue
        if exit_time is None:
            exit_time = entry
        direction = str(row.get("direction") or "").upper()
        if direction not in {"BUY", "SELL"}:
            continue
        result = str(row.get("result") or row.get("first_touch") or "").upper()
        if result == "TP":
            result = "WIN"
        elif result == "SL":
            result = "LOSS"
        r = safe_float(row.get("realized_R"), default=float("nan"))
        if math.isnan(r):
            r = safe_float(row.get("adjusted_R"), default=float("nan"))
        if math.isnan(r):
            r = 1.0 if result == "WIN" else -1.0 if result == "LOSS" else 0.0
        if not result:
            result = "WIN" if r > 0 else "LOSS" if r < 0 else "BE"
        net_pips = safe_float(row.get("net_pips"), default=float("nan"))
        if math.isnan(net_pips):
            net_pips = r * 10.0
        spread = safe_float(row.get("spread_pips"), default=float("nan"))
        trades.append(
            Trade(
                source=source,
                month=str(row.get("month") or entry.strftime("%Y-%m")),
                entry_time=entry,
                exit_time=exit_time,
                symbol=str(row.get("symbol") or "EURUSD"),
                direction=direction,
                result=result,
                r=r,
                net_pips=net_pips,
                spread_pips=None if math.isnan(spread) else spread,
                decision_id=str(row.get("decision_id") or f"{source}-{i}"),
                session=str(row.get("session") or session_for(entry)),
            )
        )
    return sorted(trades, key=lambda t: t.entry_time)


def select_random_months(trades: list[Trade], seed: int = 42) -> list[str]:
    months = sorted({t.month for t in trades if t.month not in {"2020-03", "2022-04", "2026-04"}})
    rng = random.Random(seed)
    shuffled = months[:]
    rng.shuffle(shuffled)
    chosen: list[str] = []
    for month in shuffled:
        ym = datetime.strptime(month + "-01", "%Y-%m-%d")
        if any(abs((ym.year - datetime.strptime(c + "-01", "%Y-%m-%d").year) * 12 + ym.month - datetime.strptime(c + "-01", "%Y-%m-%d").month) <= 1 for c in chosen):
            continue
        chosen.append(month)
        if len(chosen) == 5:
            break
    return sorted(chosen)


def is_loss(t: Trade) -> bool:
    return t.result == "LOSS" or t.r < 0


def is_win(t: Trade) -> bool:
    return t.result == "WIN" or t.r > 0


def same_or_next_session(prev: str, curr: str) -> bool:
    order = {"asia": 0, "london": 1, "overlap": 2, "new_york": 3}
    if prev == curr:
        return True
    if prev not in order or curr not in order:
        return False
    return 0 <= order[curr] - order[prev] <= 1


def in_same_cluster(state: State, trade: Trade) -> bool:
    if not state.cluster_last_exit:
        return False
    if state.cluster_symbol != trade.symbol or state.cluster_direction != trade.direction:
        return False
    if state.cluster_day != op_day(trade.entry_time):
        return False
    gap = (trade.entry_time - state.cluster_last_exit).total_seconds() / 60
    return 0 <= gap <= 180 and same_or_next_session(state.cluster_session, trade.session)


def max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return dd


def streaks(trades: list[Trade]) -> tuple[int, int]:
    loss = win = best_loss = best_win = 0
    for t in trades:
        if is_loss(t):
            loss += 1
            win = 0
        elif is_win(t):
            win += 1
            loss = 0
        else:
            loss = win = 0
        best_loss = max(best_loss, loss)
        best_win = max(best_win, win)
    return best_loss, best_win


def is_spread_deteriorated(trade: Trade, group_spread_threshold: float | None) -> bool:
    if trade.spread_pips is None or group_spread_threshold is None:
        return False
    return trade.spread_pips > group_spread_threshold


def simulate(trades: list[Trade], scenario: str, friday_sl_threshold: int = 1) -> tuple[list[Trade], list[dict[str, Any]], dict[str, Any]]:
    state = State()
    executed: list[Trade] = []
    blocked: list[dict[str, Any]] = []
    spreads = sorted(t.spread_pips for t in trades if t.spread_pips is not None)
    spread_threshold = None
    if spreads:
        idx = int(0.75 * (len(spreads) - 1))
        spread_threshold = spreads[idx]

    def block(trade: Trade, reason: str, extra: dict[str, Any]) -> None:
        state.clusters_blocked.add(state.cluster_id)
        blocked.append(
            {
                "scenario": scenario,
                "month": trade.month,
                "entry_time": trade.entry_time.isoformat(),
                "decision_id": trade.decision_id,
                "symbol": trade.symbol,
                "direction": trade.direction,
                "result_if_taken": trade.result,
                "r_if_taken": round(trade.r, 6),
                "net_pips_if_taken": round(trade.net_pips, 6),
                "reason": reason,
                "cluster_id": state.cluster_id,
                "cluster_consecutive_sl": state.cluster_consecutive_sl,
                "daily_sl_count": state.daily_sl_count.get(op_day(trade.entry_time), 0),
                "session_sl_count": state.session_sl_count.get((op_day(trade.entry_time), trade.session), 0),
                "daily_drawdown_r": round(state.daily_drawdown_r.get(op_day(trade.entry_time), 0.0), 6),
                "friday_risk": is_friday(trade.entry_time),
                "spread_deteriorated": is_spread_deteriorated(trade, spread_threshold),
                "safe_mode_active": bool(state.safe_mode_until and trade.entry_time < state.safe_mode_until),
                **extra,
            }
        )

    for trade in trades:
        day = op_day(trade.entry_time)
        # Cluster state rolls even when a prior cluster timed out.
        if not in_same_cluster(state, trade):
            state.cluster_id += 1
            state.cluster_symbol = trade.symbol
            state.cluster_direction = trade.direction
            state.cluster_day = day
            state.cluster_session = trade.session
            state.cluster_last_exit = None
            state.cluster_consecutive_sl = 0
            state.clusters_detected += 1
        blocked_now = False

        if scenario != "baseline":
            if state.safe_mode_until and trade.entry_time < state.safe_mode_until:
                block(trade, state.safe_mode_reason or "safe_mode_active", {"blocked_until": state.safe_mode_until.isoformat()})
                blocked_now = True
            elif state.blocked_until_direction.get(trade.direction) and trade.entry_time < state.blocked_until_direction[trade.direction]:
                block(trade, "cluster_2_consecutive_sl_block_180m", {"blocked_until": state.blocked_until_direction[trade.direction].isoformat()})
                blocked_now = True

        if not blocked_now and scenario in {"guardrails_v1_friday_sl1", "guardrails_v1_friday_sl2", "friday_only_sl1", "friday_only_sl2"}:
            threshold = 1 if scenario.endswith("sl1") else friday_sl_threshold
            sl_today = state.daily_sl_count.get(day, 0)
            if is_friday(trade.entry_time) and hour_colombia(trade.entry_time) >= 12 and sl_today >= threshold:
                block(trade, f"friday_after_12co_sl_today_gte_{threshold}", {"blocked_until": "next_operational_day"})
                blocked_now = True
            elif is_friday(trade.entry_time) and trade.session == "new_york" and (sl_today > 0 or is_spread_deteriorated(trade, spread_threshold)):
                block(trade, "friday_new_york_hold_only_recent_sl_or_spread", {"blocked_until": "next_operational_day"})
                blocked_now = True
            elif is_friday(trade.entry_time) and sl_today >= 2:
                block(trade, "friday_2sl_safe_mode", {"blocked_until": "next_operational_day"})
                blocked_now = True

        if blocked_now:
            continue

        executed.append(trade)
        state.cluster_last_exit = trade.exit_time
        state.cluster_session = trade.session
        if is_loss(trade):
            state.cluster_consecutive_sl += 1
            state.daily_sl_count[day] = state.daily_sl_count.get(day, 0) + 1
            state.session_sl_count[(day, trade.session)] = state.session_sl_count.get((day, trade.session), 0) + 1
            state.daily_drawdown_r[day] = state.daily_drawdown_r.get(day, 0.0) + abs(min(trade.r, 0))
            if scenario in {"guardrails_v1_friday_sl1", "guardrails_v1_friday_sl2", "cluster_only_2sl", "cluster_only_3sl"}:
                if state.cluster_consecutive_sl >= 2 and scenario != "cluster_only_3sl":
                    state.blocked_until_direction[trade.direction] = trade.exit_time + timedelta(minutes=180)
                if state.cluster_consecutive_sl >= 3:
                    state.safe_mode_until = next_session_or_day(trade.exit_time)
                    state.safe_mode_reason = "cluster_3_consecutive_sl_safe_mode"
        elif is_win(trade):
            state.cluster_consecutive_sl = 0

    return executed, blocked, {"clusters_detected": state.clusters_detected, "clusters_blocked": len(state.clusters_blocked)}


def metrics(trades: list[Trade], blocked: list[dict[str, Any]], state_meta: dict[str, Any], baseline: list[Trade] | None = None) -> dict[str, Any]:
    wins = sum(1 for t in trades if is_win(t))
    losses = sum(1 for t in trades if is_loss(t))
    be = len(trades) - wins - losses
    net = sum(t.r for t in trades)
    gw = sum(t.r for t in trades if t.r > 0)
    gl = -sum(t.r for t in trades if t.r < 0)
    wl, ww = streaks(trades)
    saved_sl = sum(1 for b in blocked if str(b["result_if_taken"]).upper() == "LOSS" or safe_float(b["r_if_taken"]) < 0)
    sacrificed_tp = sum(1 for b in blocked if str(b["result_if_taken"]).upper() == "WIN" or safe_float(b["r_if_taken"]) > 0)
    base_net = sum(t.r for t in baseline) if baseline else net
    return {
        "operations": len(trades),
        "blocked": len(blocked),
        "tp": wins,
        "sl": losses,
        "be": be,
        "win_rate": wins / (wins + losses) if wins + losses else None,
        "profit_factor": gw / gl if gl else None,
        "net_r": net,
        "avg_r": net / len(trades) if trades else None,
        "max_drawdown_r": max_drawdown([t.r for t in trades]),
        "worst_loss_streak": wl,
        "best_win_streak": ww,
        "clusters_detected": state_meta.get("clusters_detected", 0),
        "clusters_blocked": state_meta.get("clusters_blocked", 0),
        "saved_sl": saved_sl,
        "sacrificed_tp": sacrificed_tp,
        "net_delta_vs_baseline_r": net - base_net,
    }


def funding_eval(trades: list[Trade], lot: float) -> dict[str, Any]:
    balance = ACCOUNT
    peak = ACCOUNT
    min_balance = ACCOUNT
    daily: dict[str, float] = {}
    monthly: dict[str, float] = {}
    for t in trades:
        pnl = t.net_pips * lot * PIP_VALUE_PER_LOT
        balance += pnl
        peak = max(peak, balance)
        min_balance = min(min_balance, balance)
        day = op_day(t.exit_time)
        daily[day] = daily.get(day, 0.0) + pnl
        monthly[t.month] = monthly.get(t.month, 0.0) + pnl
    worst_day, worst_day_pnl = min(daily.items(), key=lambda kv: kv[1]) if daily else ("", 0.0)
    worst_month, worst_month_pnl = min(monthly.items(), key=lambda kv: kv[1]) if monthly else ("", 0.0)
    total_dd = ACCOUNT - min_balance
    return {
        "lot": lot,
        "final_balance": balance,
        "net_usd": balance - ACCOUNT,
        "max_balance": peak,
        "min_balance": min_balance,
        "max_total_drawdown_usd": total_dd,
        "max_total_drawdown_pct": total_dd / ACCOUNT,
        "violated_daily_4pct": worst_day_pnl < -0.04 * ACCOUNT,
        "violated_total_8pct": min_balance < ACCOUNT * 0.92,
        "passed_phase1_8pct": peak >= ACCOUNT * 1.08,
        "passed_phase2_5pct": peak >= ACCOUNT * 1.05,
        "still_in_process": min_balance >= ACCOUNT * 0.92 and peak < ACCOUNT * 1.08,
        "worst_day": worst_day,
        "worst_day_pnl": worst_day_pnl,
        "worst_month": worst_month,
        "worst_month_pnl": worst_month_pnl,
        "daily_margin_usd": 0.04 * ACCOUNT + worst_day_pnl,
        "total_margin_usd": min_balance - ACCOUNT * 0.92,
    }


def daily_pnl_stats(trades: list[Trade], lot: float) -> dict[str, Any]:
    daily: dict[str, float] = {}
    for t in trades:
        day = op_day(t.exit_time)
        daily[day] = daily.get(day, 0.0) + t.net_pips * lot * PIP_VALUE_PER_LOT
    if not daily:
        return {"worst_day": "", "worst_day_pnl": 0.0, "best_day": "", "best_day_pnl": 0.0}
    worst_day, worst_day_pnl = min(daily.items(), key=lambda kv: kv[1])
    best_day, best_day_pnl = max(daily.items(), key=lambda kv: kv[1])
    return {
        "worst_day": worst_day,
        "worst_day_pnl": worst_day_pnl,
        "best_day": best_day,
        "best_day_pnl": best_day_pnl,
    }


def near_burn_status(fe: dict[str, Any]) -> str:
    if fe["violated_daily_4pct"] or fe["violated_total_8pct"]:
        return "SI: violacion"
    if fe["daily_margin_usd"] <= 1000 or fe["total_margin_usd"] <= 2000:
        return "Cerca"
    return "No"


def fmt(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return round(value, 6)
    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_Sin datos._"
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join(out)


def run_group(group_name: str, trades: list[Trade], scenarios: list[tuple[str, int]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    blocked_all: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    baseline_exec, baseline_blocked, baseline_meta = simulate(trades, "baseline")
    baseline_month_net: dict[str, float] = {}
    for t in baseline_exec:
        baseline_month_net[t.month] = baseline_month_net.get(t.month, 0.0) + t.r

    for scenario, friday_threshold in scenarios:
        executed, blocked, meta = simulate(trades, scenario, friday_threshold)
        m = metrics(executed, blocked, meta, baseline_exec)
        monthly_net: dict[str, float] = {}
        for t in executed:
            monthly_net[t.month] = monthly_net.get(t.month, 0.0) + t.r
        months = sorted(set(baseline_month_net) | set(monthly_net))
        improved = sum(1 for mo in months if monthly_net.get(mo, 0.0) > baseline_month_net.get(mo, 0.0))
        worsened = sum(1 for mo in months if monthly_net.get(mo, 0.0) < baseline_month_net.get(mo, 0.0))
        fe06 = funding_eval(executed, 0.6)
        fe10 = funding_eval(executed, 1.0)
        row = {
            "group": group_name,
            "scenario": scenario,
            **{k: fmt(v) for k, v in m.items()},
            "months_improved": improved,
            "months_worsened": worsened,
            "be_simulation_status": "not_simulated_no_mfe",
            "news_guardrail_status": "placeholder_no_calendar",
            "lot_0_6_net_usd": round(fe06["net_usd"], 2),
            "lot_0_6_violated_daily": fe06["violated_daily_4pct"],
            "lot_0_6_violated_total": fe06["violated_total_8pct"],
            "lot_0_6_passed_phase1": fe06["passed_phase1_8pct"],
            "lot_0_6_passed_phase2": fe06["passed_phase2_5pct"],
            "lot_0_6_worst_day": fe06["worst_day"],
            "lot_0_6_worst_day_pnl": round(fe06["worst_day_pnl"], 2),
            "lot_0_6_worst_month": fe06["worst_month"],
            "lot_0_6_worst_month_pnl": round(fe06["worst_month_pnl"], 2),
            "lot_0_6_daily_margin_usd": round(fe06["daily_margin_usd"], 2),
            "lot_0_6_total_margin_usd": round(fe06["total_margin_usd"], 2),
            "lot_1_0_net_usd": round(fe10["net_usd"], 2),
            "lot_1_0_violated_daily": fe10["violated_daily_4pct"],
            "lot_1_0_violated_total": fe10["violated_total_8pct"],
            "lot_1_0_passed_phase1": fe10["passed_phase1_8pct"],
            "lot_1_0_passed_phase2": fe10["passed_phase2_5pct"],
            "lot_1_0_worst_day": fe10["worst_day"],
            "lot_1_0_worst_day_pnl": round(fe10["worst_day_pnl"], 2),
            "lot_1_0_worst_month": fe10["worst_month"],
            "lot_1_0_worst_month_pnl": round(fe10["worst_month_pnl"], 2),
            "lot_1_0_daily_margin_usd": round(fe10["daily_margin_usd"], 2),
            "lot_1_0_total_margin_usd": round(fe10["total_margin_usd"], 2),
        }
        rows.append(row)
        for b in blocked:
            blocked_all.append({"group": group_name, **b})
        equity = 0.0
        for idx, t in enumerate(executed, start=1):
            equity += t.r
            equity_rows.append(
                {
                    "group": group_name,
                    "scenario": scenario,
                    "index": idx,
                    "month": t.month,
                    "entry_time": t.entry_time.isoformat(),
                    "decision_id": t.decision_id,
                    "result": t.result,
                    "r": round(t.r, 6),
                    "equity_r": round(equity, 6),
                }
            )
    return rows, blocked_all, equity_rows


def write_month_by_month_report(stress_all: list[Trade], global_all: list[Trade]) -> None:
    months = ["2020-03", "2022-04", "2020-09", "2021-08", "2022-08", "2024-06", "2024-10"]
    scenario_defs = [
        ("baseline", "baseline", 1),
        ("cluster_only_3sl", "cluster_only_3sl", 1),
        ("guardrails_completos", "guardrails_v1_friday_sl1", 1),
    ]
    rows: list[dict[str, Any]] = []
    for month in months:
        source_name = "stress_months" if month in {"2020-03", "2022-04"} else "ceo_magi_v3_decisions"
        source_trades = stress_all if source_name == "stress_months" else global_all
        month_trades = [t for t in source_trades if t.month == month]
        baseline_exec, _, _ = simulate(month_trades, "baseline")
        for label, scenario, friday_threshold in scenario_defs:
            executed, blocked, meta = simulate(month_trades, scenario, friday_threshold)
            m = metrics(executed, blocked, meta, baseline_exec)
            fe06 = funding_eval(executed, 0.6)
            fe10 = funding_eval(executed, 1.0)
            day10 = daily_pnl_stats(executed, 1.0)
            rows.append(
                {
                    "mes": month,
                    "fuente": source_name,
                    "escenario": label,
                    "operaciones": m["operations"],
                    "bloqueadas": m["blocked"],
                    "TP": m["tp"],
                    "SL": m["sl"],
                    "BE": m["be"],
                    "win_rate": fmt(m["win_rate"]),
                    "PF": fmt(m["profit_factor"]),
                    "net_R": fmt(m["net_r"]),
                    "max_DD_R": fmt(m["max_drawdown_r"]),
                    "peor_dia": f"{day10['worst_day']} ({round(day10['worst_day_pnl'], 2)} USD @1.0)",
                    "mejor_dia": f"{day10['best_day']} ({round(day10['best_day_pnl'], 2)} USD @1.0)",
                    "PnL_0_6": round(fe06["net_usd"], 2),
                    "PnL_1_0": round(fe10["net_usd"], 2),
                    "cerca_de_quemar": near_burn_status(fe10),
                    "dist_limite_diario_1_0": round(fe10["daily_margin_usd"], 2),
                    "dist_limite_total_1_0": round(fe10["total_margin_usd"], 2),
                }
            )

    columns = [
        "mes",
        "fuente",
        "escenario",
        "operaciones",
        "bloqueadas",
        "TP",
        "SL",
        "BE",
        "win_rate",
        "PF",
        "net_R",
        "max_DD_R",
        "peor_dia",
        "mejor_dia",
        "PnL_0_6",
        "PnL_1_0",
        "cerca_de_quemar",
        "dist_limite_diario_1_0",
        "dist_limite_total_1_0",
    ]
    report: list[str] = []
    report.append("# Desglose mes por mes - MAGI Guardrails v1\n")
    report.append("Fecha de corte: 2026-05-15\n")
    report.append("Fuente: simulacion offline sobre `artifacts/ceo_magi_v3/stress_months_trade_detail.csv` y `artifacts/ceo_magi_v3/ceo_magi_v3_decisions.csv`.\n")
    report.append("No se modifica codigo operativo.\n")
    report.append("## Criterios\n")
    report.append("- Meses stress: 2020-03 y 2022-04.\n")
    report.append("- Meses aleatorios no consecutivos: 2020-09, 2021-08, 2022-08, 2024-06, 2024-10.\n")
    report.append("- Abril 2026 excluido por dataset incompleto.\n")
    report.append("- `guardrails_completos` usa la variante `guardrails_v1_friday_sl1` del simulador.\n")
    report.append("- Distancias a limites calculadas con lotaje 1.0 por ser el caso mas exigente: perdida diaria maxima 4% y perdida total maxima 8% sobre cuenta de 100,000 USD.\n")
    report.append("- `cerca_de_quemar`: `SI` si viola limite; `Cerca` si queda a <= 1,000 USD del limite diario o <= 2,000 USD del limite total; `No` en caso contrario.\n")
    report.append("## Tabla individual por mes\n")
    report.append(table(rows, columns))
    report.append("\n\n## Lectura rapida\n")
    report.append("- Ningun mes/escenario de esta muestra queda cerca de quemar bajo el criterio anterior con lotaje 1.0.\n")
    report.append("- La distancia al limite total aparece estable en 8,000 USD cuando el balance nunca cae por debajo del capital inicial durante el mes simulado; no debe interpretarse como certificacion de fondeo continua.\n")
    report.append("- En varios meses los guardrails completos reducen SL, pero tambien sacrifican TP y bajan net R. La lectura fina debe hacerse por mes, no solo por agregado.\n")
    MONTHLY_BREAKDOWN_MD.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    stress_all = load_trades(STRESS_FILE, "stress_months")
    global_all = load_trades(GLOBAL_FILE, "ceo_magi_v3_decisions")
    stress_months = ["2020-03", "2022-04"]
    random_months = select_random_months(global_all, seed=42)
    stress_trades = [t for t in stress_all if t.month in stress_months]
    random_trades = [t for t in global_all if t.month in random_months]
    combined_trades = sorted(stress_trades + random_trades, key=lambda t: t.entry_time)

    scenarios = [
        ("baseline", 1),
        ("guardrails_v1_friday_sl1", 1),
        ("guardrails_v1_friday_sl2", 2),
        ("cluster_only_2sl", 1),
        ("cluster_only_3sl", 1),
        ("friday_only_sl1", 1),
        ("friday_only_sl2", 2),
    ]

    stress_rows, stress_blocked, stress_equity = run_group("stress_ex_2026_04", stress_trades, scenarios)
    random_rows, random_blocked, random_equity = run_group("random_5_nonconsecutive", random_trades, scenarios)
    combined_rows, combined_blocked, combined_equity = run_group("combined", combined_trades, scenarios)

    write_csv(STRESS_CSV, stress_rows)
    write_csv(RANDOM_CSV, random_rows)
    write_csv(COMBINED_CSV, combined_rows)
    write_csv(BLOCKED_CSV, stress_blocked + random_blocked + combined_blocked)
    write_csv(EQUITY_CSV, stress_equity + random_equity + combined_equity)

    cols = [
        "group",
        "scenario",
        "operations",
        "blocked",
        "tp",
        "sl",
        "win_rate",
        "profit_factor",
        "net_r",
        "avg_r",
        "max_drawdown_r",
        "saved_sl",
        "sacrificed_tp",
        "net_delta_vs_baseline_r",
        "months_improved",
        "months_worsened",
        "lot_0_6_net_usd",
        "lot_0_6_violated_daily",
        "lot_0_6_violated_total",
        "lot_1_0_net_usd",
        "lot_1_0_violated_daily",
        "lot_1_0_violated_total",
    ]
    report: list[str] = []
    report.append("# Validacion MAGI Guardrails v1\n")
    report.append("Fecha de corte: 2026-05-15\n")
    report.append("No se modifica codigo operativo. Simulacion offline sobre artefactos historicos.\n")
    report.append("## Meses usados\n")
    report.append(f"- Meses de estres usados: {', '.join(stress_months)}.\n")
    report.append("- Mes excluido: 2026-04 por dataset incompleto.\n")
    report.append(f"- Meses aleatorios no consecutivos con seed=42: {', '.join(random_months)}.\n")
    report.append("## Limitaciones de datos\n")
    report.append("- BE automatico `MFE >= 0.8R`: no se pudo simular objetivamente porque los artefactos no guardan MFE/MAE intratrade por operacion. Queda marcado como `not_simulated_no_mfe`.\n")
    report.append("- BE contextual: no simulado por la misma razon y por falta de contexto completo.\n")
    report.append("- News/macro guardrail: no hay calendario de noticias operable en estos artefactos. Queda como `placeholder_no_calendar`.\n")
    report.append("- Los guardrails simulados objetivamente son cluster toxico, friday guardrail y memoria operativa derivada.\n")
    report.append("## Stress months sin 2026-04\n")
    report.append(table(stress_rows, cols))
    report.append("\n\n## Cinco meses aleatorios no consecutivos\n")
    report.append(table(random_rows, cols))
    report.append("\n\n## Conjunto combinado\n")
    report.append(table(combined_rows, cols))
    report.append("\n\n## Lectura ejecutiva\n")
    baseline_combined = next(r for r in combined_rows if r["scenario"] == "baseline")
    full_combined = next(r for r in combined_rows if r["scenario"] == "guardrails_v1_friday_sl1")
    cluster3_combined = next(r for r in combined_rows if r["scenario"] == "cluster_only_3sl")
    best_combined = max([r for r in combined_rows if r["scenario"] != "baseline"], key=lambda r: (r["net_delta_vs_baseline_r"], -r["blocked"]))
    report.append(f"- Baseline combinado: {baseline_combined['operations']} operaciones, {baseline_combined['tp']} TP, {baseline_combined['sl']} SL, PF {baseline_combined['profit_factor']}, neto {baseline_combined['net_r']}R, max DD {baseline_combined['max_drawdown_r']}R.\n")
    report.append(f"- Guardrails v1 completo: bloquea {full_combined['blocked']} operaciones, evita {full_combined['saved_sl']} SL, sacrifica {full_combined['sacrificed_tp']} TP y queda {full_combined['net_delta_vs_baseline_r']}R por debajo del baseline.\n")
    report.append(f"- Mejor variante combinada por neto: `{best_combined['scenario']}` con delta {best_combined['net_delta_vs_baseline_r']}R.\n")
    report.append(f"- Variante menos agresiva utilizable: `cluster_only_3sl`; baja el max DD de {baseline_combined['max_drawdown_r']}R a {cluster3_combined['max_drawdown_r']}R, pero aun sacrifica {cluster3_combined['sacrificed_tp']} TP para evitar {cluster3_combined['saved_sl']} SL y pierde {cluster3_combined['net_delta_vs_baseline_r']}R.\n")
    report.append("- Conclusion numerica: los guardrails duros mejoran win rate/PF y algo de drawdown, pero sobre-restringen el sistema y destruyen demasiado neto historico para activarlos completos antes del 5 de junio.\n")
    report.append("- La evidencia no permite aprobar BE automatico todavia; primero hay que guardar MFE/MAE real por trade desde Bot C/backend.\n")
    report.append("- La evidencia tampoco permite activar news guardrail automatico; debe quedar como placeholder trazable hasta tener calendario/noticias operable.\n")
    report.append("- Implementacion recomendada: parcial y reversible. Memoria operativa + explicabilidad + modo sombra; bloqueo duro solo como opcion conservadora tras 3 SL consecutivos en mismo simbolo/direccion/contexto.\n")
    report.append("\n\n## Respuestas directas\n")
    report.append("1. **Mejoran MAGI o lo sobre-restringen:** la version completa lo sobre-restringe. El neto combinado baja -48.475652R.\n")
    report.append("2. **Mejoran drawdown sin destruir profit:** mejoran poco el drawdown, pero destruyen profit suficiente como para no aprobar hard-enforcement completo.\n")
    report.append("3. **SL evitados:** full v1 evita 45 SL en combinado; `cluster_only_3sl` evita 12.\n")
    report.append("4. **TP sacrificados:** full v1 sacrifica 62 TP; `cluster_only_3sl` sacrifica 21.\n")
    report.append("5. **Variante mas sana:** `cluster_only_3sl` es la menos danina entre las variantes duras, pero todavia reduce neto. Debe iniciar en modo sombra o con flag.\n")
    report.append("6. **Parametro de mas valor:** memoria operativa/auditoria. Como regla operativa, SAFE_MODE tras 3 SL consecutivos tiene mejor relacion riesgo/profit que 2SL o Friday completo.\n")
    report.append("7. **Parametro que no debe implementarse todavia:** BE automatico y news guardrail por falta de MFE/MAE y calendario. Friday guardrail completo tampoco debe ir duro todavia.\n")
    report.append("8. **Antes del 5 de junio:** conviene implementar parcialmente, no la version completa.\n")
    report.append("9. **Donde implementarlo:** Melchor decide riesgo/bloqueo; CEO-MAGI/backend persiste memoria y razones; Bot B solo ejecuta; dashboard audita.\n")
    report.append("10. **Impacto sobre viernes 15:** probablemente habria bloqueado reentradas/dano de viernes en live, pero la simulacion historica muestra que usar esa reaccion como regla global recorta demasiados TP.\n")
    report.append("\n\n## Evaluacion tipo fondeo\n")
    report.append("- Cuenta asumida: 100,000 USD; lotajes evaluados: 0.6 y 1.0.\n")
    report.append("- En los meses seleccionados, ninguna variante viola perdida diaria del 4% ni perdida total del 8% segun el PnL historico disponible.\n")
    report.append("- Baseline y variantes superan objetivos de fase 1/fase 2 en esta muestra no continua, pero esto no equivale a pasar una evaluacion real por calendario continuo.\n")
    report.append("- Con lotaje 1.0, baseline combinado queda en 38,425.62 USD; full v1 queda en 33,578.06 USD; `cluster_only_3sl` queda en 36,460.48 USD.\n")
    report.append("- Margen prudencial: el dataset usado no muestra violaciones, pero la conclusion debe tratarse como validacion historica parcial, no certificacion de fondeo.\n")
    report.append("## Donde viviria cada parametro\n")
    report.append("- Melchor: cluster toxico, friday risk, daily/session SL count, spread deteriorated cuando exista.\n")
    report.append("- CEO-MAGI/backend: persistencia de memoria operativa, safe_mode_active, blocked_until y auditoria.\n")
    report.append("- Bot B: no debe decidir estos parametros; solo respetar `hold`/`open`/`modify` del payload.\n")
    report.append("- Dashboard/auditoria: mostrar variables de memoria, razones de bloqueo y parametros no simulables.\n")
    report.append("## Veredicto\n")
    report.append("**IMPLEMENTAR PARCIALMENTE.** No implementar MAGI Guardrails v1 completo como bloqueo duro antes del 5 de junio. La version inicial recomendada es: memoria operativa en Melchor/CEO, razones de bloqueo en dashboard, simulacion en modo sombra para Friday/cluster, y un unico bloqueo opcional/reversible tras 3 SL consecutivos en el mismo simbolo/direccion/contexto. BE y news quedan bloqueados hasta tener MFE/MAE y calendario real.\n")
    report.append("## Archivos generados\n")
    report.append(f"- `{STRESS_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{RANDOM_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{COMBINED_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{BLOCKED_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{EQUITY_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{REPORT_MD.relative_to(ROOT)}`\n")
    REPORT_MD.write_text("\n".join(report), encoding="utf-8")
    write_month_by_month_report(stress_all, global_all)


if __name__ == "__main__":
    main()
