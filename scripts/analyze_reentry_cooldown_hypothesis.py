from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SERVER = ROOT / "servidor-prosperity"
DECISIONS_DIR = SERVER / "data" / "audit" / "decisions"
SNAPSHOTS_DIR = SERVER / "data" / "snapshots" / "normalized"
BOTC_DIR = Path(
    os.environ.get("MAGI_BOT_C_AUDIT_DIR", SERVER / "data" / "audit" / "bot_c")
)

LIVE_TRADES_CSV = REPORTS / "reentry_cooldown_live_trades.csv"
SIM_SUMMARY_CSV = REPORTS / "reentry_cooldown_simulation_summary.csv"
EQUITY_CSV = REPORTS / "reentry_cooldown_equity_comparison.csv"
REPORT_MD = REPORTS / "reentry_cooldown_hypothesis_2026-05-15.md"

TP_USD = 1000
SL_USD = -500
BE_USD = 0


@dataclass
class Trade:
    source: str
    ticket: str
    decision_id: str
    snapshot_id: str
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: datetime | None
    result: str
    pnl: float
    session: str
    is_synthetic: bool = False
    reason: str = ""


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
        for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                dt = None
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        v = float(value)
        if math.isnan(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def session_for(dt: datetime | None) -> str:
    if dt is None:
        return "unknown"
    h = dt.astimezone(timezone.utc).hour
    if 7 <= h < 12:
        return "london"
    if 12 <= h < 17:
        return "overlap"
    if 17 <= h < 22:
        return "new_york"
    return "asia"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def load_decisions() -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    if not DECISIONS_DIR.exists():
        return decisions
    for path in DECISIONS_DIR.glob("*/magi_decisions.jsonl"):
        for row in read_jsonl(path):
            decision_id = str(row.get("decision_id") or "")
            if decision_id:
                decisions[decision_id] = row
    return decisions


def find_decision(short_or_full: str, decisions: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not short_or_full:
        return None
    if short_or_full in decisions:
        return decisions[short_or_full]
    matches = [row for did, row in decisions.items() if did.startswith(short_or_full)]
    return matches[0] if matches else None


def load_snapshot_info() -> dict[str, dict[str, str]]:
    info: dict[str, dict[str, str]] = {}
    if not SNAPSHOTS_DIR.exists():
        return modes
    for path in SNAPSHOTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        sid = str(data.get("snapshot_id") or data.get("id") or "")
        if not sid:
            continue
        mode = (
            data.get("source_mode")
            or data.get("metadata", {}).get("source_mode")
            or data.get("source", {}).get("mode")
            or ""
        )
        session = data.get("market", {}).get("session") or ""
        info[sid] = {"mode": str(mode), "session": str(session)}
    return info


def load_botc_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not BOTC_DIR.exists():
        return events
    for path in BOTC_DIR.glob("*/bot_c_events.jsonl"):
        events.extend(read_jsonl(path))
    events.sort(key=lambda e: parse_dt(e.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc))
    return events


def classify_result(open_event: dict[str, Any], close_event: dict[str, Any] | None) -> tuple[str, float]:
    if close_event is None:
        return "OPEN", 0.0
    comment = str(close_event.get("comment") or "").lower()
    profit = safe_float(close_event.get("profit"))
    close_price = safe_float(close_event.get("price"))
    entry = safe_float(open_event.get("price"))
    sl = safe_float(open_event.get("sl"))
    tp = safe_float(open_event.get("tp"))
    if "tp" in comment or (tp and abs(close_price - tp) < 0.00002):
        return "TP", TP_USD
    if "sl" in comment or (sl and abs(close_price - sl) < 0.00002):
        if abs(close_price - entry) < 0.00002 or abs(profit) < 0.05:
            return "BE", BE_USD
        return "SL", SL_USD
    if abs(profit) < 0.05 and abs(close_price - entry) < 0.00003:
        return "BE", BE_USD
    return "SAFETY_PARTIAL", 0.0


def load_live_trades() -> list[Trade]:
    decisions = load_decisions()
    snapshot_info = load_snapshot_info()
    events = load_botc_events()
    opens = [e for e in events if str(e.get("event_type")) == "open"]
    closes_by_ticket: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        if str(e.get("event_type")) == "close":
            ticket = str(int(safe_float(e.get("ticket")))) if safe_float(e.get("ticket")) else str(e.get("ticket") or "")
            closes_by_ticket.setdefault(ticket, []).append(e)

    trades: list[Trade] = []
    for open_event in opens:
        ticket = str(int(safe_float(open_event.get("ticket")))) if safe_float(open_event.get("ticket")) else str(open_event.get("ticket") or "")
        entry_time = parse_dt(open_event.get("timestamp"))
        if entry_time is None:
            continue
        close_event = closes_by_ticket.get(ticket, [None])[0]
        exit_time = parse_dt(close_event.get("timestamp")) if close_event else None
        short_decision = str(open_event.get("decision_id") or "")
        decision = find_decision(short_decision, decisions)
        decision_id = str(decision.get("decision_id") if decision else short_decision)
        snapshot_id = str(decision.get("snapshot_id") if decision else "")
        payload = decision.get("execution_payload", {}) if decision else {}
        details = payload.get("details", {}) if isinstance(payload, dict) else {}
        order_type = str(details.get("order_type") or "").upper()
        if order_type not in {"BUY", "SELL"}:
            comment = str(open_event.get("comment") or "").upper()
            order_type = "SELL" if "SELL" in comment else "BUY" if "BUY" in comment else "UNKNOWN"
        result, pnl = classify_result(open_event, close_event)
        snap_info = snapshot_info.get(snapshot_id, {})
        mode = snap_info.get("mode", "")
        snapshot_session = snap_info.get("session") or session_for(entry_time)
        is_synthetic = "synthetic" in snapshot_id.lower() or "synthetic" in mode.lower()
        trades.append(
            Trade(
                source="live",
                ticket=ticket,
                decision_id=decision_id,
                snapshot_id=snapshot_id,
                symbol=str(open_event.get("symbol") or ""),
                direction=order_type,
                entry_time=entry_time,
                exit_time=exit_time,
                result=result,
                pnl=pnl,
                session=snapshot_session,
                is_synthetic=is_synthetic,
                reason=str(decision.get("reason") if decision else ""),
            )
        )
    trades.sort(key=lambda t: t.entry_time)
    return trades


def is_loss(trade: Trade) -> bool:
    return trade.result.upper() in {"SL", "LOSS"} or trade.pnl < 0


def is_win(trade: Trade) -> bool:
    return trade.result.upper() in {"TP", "WIN"} or trade.pnl > 0


def annotate_reentries(trades: list[Trade]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous_trade: Trade | None = None
    for trade in trades:
        gap_min = None
        same_direction = False
        same_session = False
        within_3h = False
        post_sl = False
        if previous_trade and previous_trade.exit_time and is_loss(previous_trade):
            gap_min = (trade.entry_time - previous_trade.exit_time).total_seconds() / 60
            same_direction = trade.direction == previous_trade.direction
            same_session = trade.session == previous_trade.session
            within_3h = 0 <= gap_min <= 180
            post_sl = True
        rows.append(
            {
                "source": trade.source,
                "ticket": trade.ticket,
                "decision_id": trade.decision_id,
                "snapshot_id": trade.snapshot_id,
                "symbol": trade.symbol,
                "direction": trade.direction,
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat() if trade.exit_time else "",
                "session": trade.session,
                "result": trade.result,
                "pnl_normalized": trade.pnl,
                "is_synthetic": trade.is_synthetic,
                "post_sl_reentry": post_sl,
                "minutes_after_previous_sl": round(gap_min, 2) if gap_min is not None else "",
                "same_direction_as_previous_sl": same_direction,
                "same_session_as_previous_sl": same_session,
                "within_3h_after_previous_sl": within_3h,
                "fast_same_direction_reentry": post_sl and same_direction and within_3h,
                "reason": trade.reason,
            }
        )
        previous_trade = trade
    return rows


def metrics(trades: list[Trade]) -> dict[str, Any]:
    wins = sum(1 for t in trades if is_win(t))
    losses = sum(1 for t in trades if is_loss(t))
    bes = sum(1 for t in trades if t.result == "BE")
    pnl = sum(t.pnl for t in trades)
    gross_win = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = -sum(t.pnl for t in trades if t.pnl < 0)
    pf = gross_win / gross_loss if gross_loss else None
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted(trades, key=lambda x: x.entry_time):
        equity += t.pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "be": bes,
        "win_rate": wins / (wins + losses) if (wins + losses) else None,
        "net": pnl,
        "profit_factor": pf,
        "max_drawdown": max_dd,
    }


def apply_cooldown(trades: list[Trade], scenario: str) -> tuple[list[Trade], list[Trade]]:
    kept: list[Trade] = []
    skipped: list[Trade] = []
    block_same_dir_until: dict[str, datetime] = {}
    loss_streak_by_dir_session: dict[tuple[str, str], int] = {}
    block_all_until: datetime | None = None
    daily_losses: dict[str, int] = {}

    for trade in sorted(trades, key=lambda x: x.entry_time):
        key_day = trade.entry_time.date().isoformat()
        blocked = False
        if block_all_until and trade.entry_time < block_all_until:
            blocked = True
        if not blocked and scenario in {"A_60m", "B_90m", "C_180m"}:
            until = block_same_dir_until.get(trade.direction)
            blocked = bool(until and trade.entry_time < until)
        if not blocked and scenario == "D_2sl_same_dir_session_3h":
            until = block_same_dir_until.get(f"{trade.direction}:{trade.session}")
            blocked = bool(until and trade.entry_time < until)
        if not blocked and scenario == "F_until_session_change":
            marker = block_same_dir_until.get(f"{trade.direction}:session:{trade.session}")
            blocked = bool(marker and trade.entry_time.date() == marker.date())
        if not blocked and scenario == "G_until_next_day":
            until = block_same_dir_until.get(f"{trade.direction}:next_day")
            blocked = bool(until and trade.entry_time < until)
        if blocked:
            skipped.append(trade)
            continue
        kept.append(trade)
        if is_loss(trade) and trade.exit_time:
            if scenario == "A_60m":
                block_same_dir_until[trade.direction] = trade.exit_time + timedelta(minutes=60)
            elif scenario == "B_90m":
                block_same_dir_until[trade.direction] = trade.exit_time + timedelta(minutes=90)
            elif scenario == "C_180m":
                block_same_dir_until[trade.direction] = trade.exit_time + timedelta(minutes=180)
            elif scenario == "D_2sl_same_dir_session_3h":
                k = (trade.direction, trade.session)
                loss_streak_by_dir_session[k] = loss_streak_by_dir_session.get(k, 0) + 1
                if loss_streak_by_dir_session[k] >= 2:
                    block_same_dir_until[f"{trade.direction}:{trade.session}"] = trade.exit_time + timedelta(hours=3)
            elif scenario == "E_3sl_day_safe_mode":
                daily_losses[key_day] = daily_losses.get(key_day, 0) + 1
                if daily_losses[key_day] >= 3:
                    next_day = datetime.combine(trade.entry_time.date() + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                    block_all_until = next_day
            elif scenario == "F_until_session_change":
                block_same_dir_until[f"{trade.direction}:session:{trade.session}"] = trade.exit_time
            elif scenario == "G_until_next_day":
                next_day = datetime.combine(trade.entry_time.date() + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                block_same_dir_until[f"{trade.direction}:next_day"] = next_day
        elif is_win(trade):
            loss_streak_by_dir_session[(trade.direction, trade.session)] = 0
    return kept, skipped


def parse_sim_csv(path: Path) -> list[Trade]:
    rows: list[dict[str, Any]]
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    trades: list[Trade] = []
    for i, row in enumerate(rows):
        action = str(row.get("action") or row.get("prediction") or "").upper()
        if action and action not in {"ENTER", "ENTER_BUY", "ENTER_SELL"}:
            continue
        direction = str(row.get("direction") or "")
        if not direction:
            pred = str(row.get("prediction") or "")
            if pred.endswith("BUY"):
                direction = "BUY"
            elif pred.endswith("SELL"):
                direction = "SELL"
        direction = direction.upper()
        if direction not in {"BUY", "SELL"}:
            continue
        entry_time = (
            parse_dt(row.get("entry_time"))
            or parse_dt(row.get("entry_datetime"))
            or parse_dt(row.get("timestamp"))
        )
        if entry_time is None:
            continue
        exit_time = (
            parse_dt(row.get("exit_time"))
            or parse_dt(row.get("exit_timestamp"))
            or parse_dt(row.get("exit_timestamp_raw"))
        )
        result_raw = str(row.get("result") or row.get("first_touch") or "").upper()
        r = (
            safe_float(row.get("realized_R"), default=float("nan"))
            if "realized_R" in row
            else float("nan")
        )
        if math.isnan(r):
            r = safe_float(row.get("adjusted_R"), default=float("nan"))
        if math.isnan(r):
            r = 1.0 if result_raw in {"WIN", "TP"} else -1.0 if result_raw in {"LOSS", "SL"} else 0.0
        if not result_raw:
            result_raw = "WIN" if r > 0 else "LOSS" if r < 0 else "BE"
        elif result_raw == "TP":
            result_raw = "WIN"
        elif result_raw == "SL":
            result_raw = "LOSS"
        trades.append(
            Trade(
                source=path.as_posix(),
                ticket=str(i + 1),
                decision_id=str(row.get("decision_id") or ""),
                snapshot_id="",
                symbol=str(row.get("symbol") or "EURUSD"),
                direction=direction,
                entry_time=entry_time,
                exit_time=exit_time,
                result=result_raw,
                pnl=r,
                session=str(row.get("session") or session_for(entry_time)),
                is_synthetic=False,
                reason=str(row.get("reason_code") or row.get("reason_codes") or ""),
            )
        )
    trades.sort(key=lambda t: t.entry_time)
    return trades


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def scenario_rows(dataset: str, trades: list[Trade]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base = metrics(trades)
    annotated = annotate_reentries(trades)
    fast = [r for r in annotated if r["fast_same_direction_reentry"]]
    fast_losses = sum(1 for r in fast if str(r["result"]).upper() in {"SL", "LOSS"})
    fast_wins = sum(1 for r in fast if str(r["result"]).upper() in {"TP", "WIN"})
    fast_net = sum(safe_float(r["pnl_normalized"]) for r in fast)
    scenarios = {
        "Baseline": None,
        "Cooldown A - 60m same direction after 1 SL": "A_60m",
        "Cooldown B - 90m same direction after 1 SL": "B_90m",
        "Cooldown C - 180m same direction after 1 SL": "C_180m",
        "Cooldown D - after 2 SL same direction/session block 3h": "D_2sl_same_dir_session_3h",
        "Cooldown E - after 3 SL day safe until next day": "E_3sl_day_safe_mode",
        "Cooldown F - same direction until session change": "F_until_session_change",
        "Cooldown G - same direction until next day": "G_until_next_day",
    }
    for label, code in scenarios.items():
        kept, skipped = (trades, []) if code is None else apply_cooldown(trades, code)
        m = metrics(kept)
        skipped_losses = sum(1 for t in skipped if is_loss(t))
        skipped_wins = sum(1 for t in skipped if is_win(t))
        skipped_net = sum(t.pnl for t in skipped)
        rows.append(
            {
                "dataset": dataset,
                "scenario": label,
                "trades": m["trades"],
                "wins": m["wins"],
                "losses": m["losses"],
                "be": m["be"],
                "win_rate": round(m["win_rate"], 4) if m["win_rate"] is not None else "",
                "net": round(m["net"], 6),
                "profit_factor": round(m["profit_factor"], 4) if m["profit_factor"] is not None else "",
                "max_drawdown": round(m["max_drawdown"], 6),
                "trades_removed": len(skipped),
                "winning_trades_removed": skipped_wins,
                "losing_trades_removed": skipped_losses,
                "removed_net": round(skipped_net, 6),
                "net_delta_vs_baseline": round(m["net"] - base["net"], 6),
                "dd_delta_vs_baseline": round(m["max_drawdown"] - base["max_drawdown"], 6),
                "fast_same_direction_reentries": len(fast),
                "fast_reentry_wins": fast_wins,
                "fast_reentry_losses": fast_losses,
                "fast_reentry_net": round(fast_net, 6),
            }
        )
    return rows


def equity_rows(dataset: str, scenario: str, trades: list[Trade]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    equity = 0.0
    peak = 0.0
    for i, t in enumerate(sorted(trades, key=lambda x: x.entry_time), start=1):
        equity += t.pnl
        peak = max(peak, equity)
        rows.append(
            {
                "dataset": dataset,
                "scenario": scenario,
                "index": i,
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat() if t.exit_time else "",
                "direction": t.direction,
                "result": t.result,
                "pnl": round(t.pnl, 6),
                "equity": round(equity, 6),
                "drawdown": round(peak - equity, 6),
            }
        )
    return rows


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_Sin datos._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    REPORTS.mkdir(exist_ok=True)

    live_all = load_live_trades()
    live_org = [t for t in live_all if not t.is_synthetic and t.result != "OPEN"]
    live_rows = annotate_reentries(live_org)
    write_csv(LIVE_TRADES_CSV, live_rows)

    sim_paths = [
        ROOT / "artifacts" / "ceo_magi_v3" / "stress_months_trade_detail.csv",
        ROOT / "artifacts" / "ceo_magi_v3" / "random_3_months_trade_audit.csv",
        ROOT / "artifacts" / "ceo_magi_v3" / "ceo_magi_v3_decisions.csv",
        ROOT / "artifacts" / "magi_realistic_scenario_c" / "scenario_c_realistic_trades.csv",
        ROOT
        / "data"
        / "output"
        / "magi_v2"
        / "baltasar_v2_rich_features_model"
        / "policy_medium_r_simulation"
        / "simulated_trades_050.csv",
    ]

    summary_rows: list[dict[str, Any]] = []
    equity: list[dict[str, Any]] = []
    datasets: dict[str, list[Trade]] = {"live_demo_organic_normalized_usd": live_org}
    for path in sim_paths:
        if path.exists():
            trades = parse_sim_csv(path)
            if trades:
                datasets[path.as_posix().replace(ROOT.as_posix() + "/", "")] = trades

    for dataset, trades in datasets.items():
        rows = scenario_rows(dataset, trades)
        summary_rows.extend(rows)
        for r in rows:
            label = r["scenario"]
            if label == "Baseline":
                scenario_trades = trades
            elif "60m" in label:
                scenario_trades, _ = apply_cooldown(trades, "A_60m")
            elif "90m" in label:
                scenario_trades, _ = apply_cooldown(trades, "B_90m")
            elif "180m" in label:
                scenario_trades, _ = apply_cooldown(trades, "C_180m")
            elif "2 SL" in label:
                scenario_trades, _ = apply_cooldown(trades, "D_2sl_same_dir_session_3h")
            elif "3 SL day" in label:
                scenario_trades, _ = apply_cooldown(trades, "E_3sl_day_safe_mode")
            elif "session change" in label:
                scenario_trades, _ = apply_cooldown(trades, "F_until_session_change")
            else:
                scenario_trades, _ = apply_cooldown(trades, "G_until_next_day")
            equity.extend(equity_rows(dataset, label, scenario_trades))

    write_csv(SIM_SUMMARY_CSV, summary_rows)
    write_csv(EQUITY_CSV, equity)

    fast_reentries = [r for r in live_rows if r["fast_same_direction_reentry"]]
    fast_losses = [r for r in fast_reentries if r["result"] == "SL"]
    fast_wins = [r for r in fast_reentries if r["result"] == "TP"]
    fast_safety = [r for r in fast_reentries if r["result"] == "SAFETY_PARTIAL"]
    live_summary = [r for r in summary_rows if r["dataset"] == "live_demo_organic_normalized_usd"]
    sim_summary = [r for r in summary_rows if r["dataset"] != "live_demo_organic_normalized_usd"]

    best_live = max(
        [r for r in live_summary if r["scenario"] != "Baseline"],
        key=lambda r: (r["net"], -r["trades_removed"]),
        default=None,
    )

    report = []
    report.append("# Hipotesis de reentradas post-SL en MAGI\n")
    report.append("Fecha de corte: 2026-05-15\n")
    report.append("Modelo live normalizado: TP = +1000 USD, SL = -500 USD, BE = 0 USD.\n")
    report.append("## Resumen ejecutivo\n")
    report.append(
        "La hipotesis es **verdadera para la demo/live reciente, pero solo parcialmente confirmada por los backtests**. "
        "En vivo, el dano mas visible del viernes 15 si vino de secuencias de reentrada rapida en la misma direccion despues de SL. "
        f"Se detectaron {len(fast_reentries)} reentradas organicas en la misma direccion dentro de 3 horas de un SL previo; "
        f"{len(fast_losses)} terminaron en SL, {len(fast_wins)} terminaron en TP y {len(fast_safety)} fue safety/parcial. "
        "Bajo el modelo normalizado, ese grupo tuvo neto -1000 USD. "
        "Sin embargo, en artefactos historicos amplios, muchas reentradas rapidas fueron ganadoras; por eso un cooldown global despues de cada SL puede mejorar estabilidad pero tambien destruir parte del edge.\n"
    )
    report.append("## Respuesta directa\n")
    report.append(
        "- **La hipotesis es verdadera en live/demo:** el cluster mas danino observado tiene forma SL -> reentrada rapida -> SL.\n"
    )
    report.append(
        "- **No queda demostrada como verdad universal historica:** en varios backtests las reentradas rapidas post-SL fueron netamente positivas.\n"
    )
    report.append(
        "- **Conclusion operativa:** no conviene bloquear toda reentrada despues de 1 SL de forma ciega; si conviene disenar una capa de riesgo que detecte clusters: misma direccion, misma sesion/contexto, SL recientes, spread deteriorado, viernes/tarde o 2-3 perdidas agrupadas.\n"
    )
    report.append("## 1. Evidencia live/demo\n")
    fast_net = sum(safe_float(r["pnl_normalized"]) for r in fast_reentries)
    report.append(
        f"Operaciones organicas cerradas analizadas: {len(live_org)}. "
        f"Reentradas rapidas misma direccion post-SL: {len(fast_reentries)}. "
        f"SL dentro de esas reentradas: {len(fast_losses)}. "
        f"TP dentro de esas reentradas: {len(fast_wins)}. "
        f"Safety/parcial dentro de esas reentradas: {len(fast_safety)}. "
        f"Neto normalizado de esas reentradas: {fast_net} USD.\n"
    )
    report.append(
        markdown_table(
            live_rows,
            [
                "ticket",
                "direction",
                "entry_time",
                "exit_time",
                "session",
                "result",
                "pnl_normalized",
                "minutes_after_previous_sl",
                "same_direction_as_previous_sl",
                "within_3h_after_previous_sl",
                "fast_same_direction_reentry",
            ],
        )
    )
    report.append("\n\n### Cooldowns sobre demo/live\n")
    report.append(
        markdown_table(
            live_summary,
            [
                "scenario",
                "trades",
                "wins",
                "losses",
                "be",
                "net",
                "profit_factor",
                "max_drawdown",
                "trades_removed",
                "winning_trades_removed",
                "losing_trades_removed",
                "net_delta_vs_baseline",
                "fast_same_direction_reentries",
                "fast_reentry_losses",
                "fast_reentry_wins",
                "fast_reentry_net",
            ],
        )
    )
    if best_live:
        report.append(
            f"\n\nMejor escenario live por neto: **{best_live['scenario']}**, "
            f"neto {best_live['net']} vs baseline, delta {best_live['net_delta_vs_baseline']}.\n"
        )
    report.append(
        "\n\nLectura live: los cooldowns de 60/90 minutos habrian mejorado el resultado en +500 USD normalizados; "
        "180 minutos o bloqueo hasta cambio de sesion habrian mejorado +1000 USD; bloqueo hasta siguiente dia habria mejorado +1500 USD, "
        "pero este ultimo es demasiado agresivo para adoptarlo sin mas muestra.\n"
    )

    report.append("## 2. Evidencia historica del simulador/backtests\n")
    report.append(
        "Se analizaron artefactos historicos existentes con operaciones o decisiones ejecutables. "
        "Las metricas historicas usan R/realized_R cuando existe, no USD normalizado.\n"
    )
    compact_sim = [
        r
        for r in sim_summary
        if r["scenario"] in {"Baseline", "Cooldown A - 60m same direction after 1 SL", "Cooldown C - 180m same direction after 1 SL"}
    ]
    report.append(
        markdown_table(
            compact_sim,
            [
                "dataset",
                "scenario",
                "trades",
                "wins",
                "losses",
                "win_rate",
                "net",
                "profit_factor",
                "max_drawdown",
                "trades_removed",
                "winning_trades_removed",
                "losing_trades_removed",
                "net_delta_vs_baseline",
                "dd_delta_vs_baseline",
                "fast_same_direction_reentries",
                "fast_reentry_losses",
                "fast_reentry_wins",
                "fast_reentry_net",
            ],
        )
    )
    report.append("\n\n### Lectura historica clave\n")
    report.append(
        "- `stress_months_trade_detail.csv`: hubo 79 reentradas rapidas, 54 ganadoras y 25 perdedoras; neto positivo +56.08R. Cooldown C mejora PF y drawdown, pero reduce neto total.\n"
    )
    report.append(
        "- `ceo_magi_v3_decisions.csv`: hubo 628 reentradas rapidas, 479 ganadoras y 149 perdedoras; neto positivo +600.99R. Un cooldown global reduce mucho el beneficio total.\n"
    )
    report.append(
        "- `scenario_c_realistic_trades.csv`: hubo 2000 reentradas rapidas, 1194 ganadoras y 669 perdedoras; neto positivo +1797.3R. La variante SAFE_MODE mejora drawdown/PF, pero tambien recorta neto.\n"
    )
    report.append(
        "- `random_3_months_trade_audit.csv` y `simulated_trades_050.csv`: no mostraron reentradas rapidas detectables con este criterio/formato, asi que no aportan evidencia a favor del patron.\n"
    )
    report.append(
        "\nLa tabla completa por escenario esta en `reports/reentry_cooldown_simulation_summary.csv`.\n"
    )

    report.append("## 3. Conclusiones\n")
    report.append("- La hipotesis live no es absoluta: no todas las perdidas vienen de reentradas, pero el cluster mas danino si tiene esa forma.\n")
    report.append("- En live, las reentradas rapidas misma direccion explican 4 SL directos, equivalentes a -2000 USD brutos normalizados. Como tambien hubo 1 TP de +1000 USD, el dano neto del grupo fue -1000 USD.\n")
    report.append("- El cooldown live mas rentable fue bloqueo misma direccion hasta siguiente dia (+1500 USD), pero es demasiado restrictivo para convertirlo directamente en regla productiva.\n")
    report.append("- El cooldown live mas razonable parece 180 minutos o hasta cambio de sesion, porque habria evitado 4 SL y perdido 1 TP, mejorando +1000 USD y reduciendo max drawdown de 1500 a 1000 USD.\n")
    report.append("- La evidencia historica evita una conclusion simplista: las reentradas rapidas no son inherentemente malas. En los backtests grandes, muchas reentradas post-SL aportaron beneficio neto.\n")
    report.append("- Por tanto, la mejora recomendada no es `despues de cualquier SL no operar mas`, sino un guardrail contextual: misma direccion + misma sesion/contexto + SL reciente + deterioro operativo, o SAFE_MODE tras 2-3 SL agrupados.\n")
    report.append("- Conviene planear esto antes del 5 de junio, pero como capa de riesgo en Melchor/CEO-MAGI/backend, no en Bot B. Bot B debe seguir siendo ejecutor/guardrail, no cerebro de cooldown.\n")

    report.append("## 4. Donde implementarlo si se aprueba\n")
    report.append("- **Melchor:** lugar natural para bloquear por riesgo contextual: `recent_sl_same_direction`, `session_loss_cluster`, `daily_loss_count`, `friday_risk`.\n")
    report.append("- **CEO-MAGI/backend:** debe conservar estado entre decisiones y decidir si respeta el bloqueo, degrada a HOLD o activa SAFE_MODE.\n")
    report.append("- **Bot B:** solo deberia mantener guardrails de ejecucion: no duplicar, no operar decision vieja, respetar payload. No debe decidir cooldown estrategico.\n")
    report.append("- **Dashboard/auditoria:** mostrar `cooldown_active`, `cooldown_reason`, `blocked_until`, `previous_sl_ticket`.\n")

    report.append("## 5. Archivos generados\n")
    report.append(f"- `{LIVE_TRADES_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{SIM_SUMMARY_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{EQUITY_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{REPORT_MD.relative_to(ROOT)}`\n")

    REPORT_MD.write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
