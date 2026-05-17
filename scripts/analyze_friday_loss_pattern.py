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

REPORT_MD = REPORTS / "friday_loss_pattern_analysis_2026-05-15.md"
WEEKDAY_CSV = REPORTS / "friday_by_weekday_summary.csv"
SESSION_CSV = REPORTS / "friday_session_breakdown.csv"
SCENARIOS_CSV = REPORTS / "friday_filter_scenarios.csv"

BOGOTA = timezone(timedelta(hours=-5))
TP_USD = 1000.0
SL_USD = -500.0
BE_USD = 0.0


@dataclass
class Trade:
    dataset: str
    ticket: str
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: datetime | None
    result: str
    pnl: float
    session: str
    spread_pips: float | None = None
    decision_id: str = ""
    snapshot_id: str = ""
    synthetic: bool = False


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


def session_for_utc(dt: datetime) -> str:
    h = dt.astimezone(timezone.utc).hour
    if 7 <= h < 12:
        return "london"
    if 12 <= h < 17:
        return "overlap"
    if 17 <= h < 22:
        return "new_york"
    return "asia"


def weekday_name(dt: datetime) -> str:
    names = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    return names[dt.astimezone(BOGOTA).weekday()]


def is_friday(dt: datetime) -> bool:
    return dt.astimezone(BOGOTA).weekday() == 4


def friday_hour_co(dt: datetime) -> float:
    local = dt.astimezone(BOGOTA)
    return local.hour + local.minute / 60 + local.second / 3600


def friday_bucket(trade: Trade) -> str:
    if not is_friday(trade.entry_time):
        return "non_friday"
    hour = friday_hour_co(trade.entry_time)
    if hour >= 12:
        return "friday_late_after_12co"
    if hour >= 10:
        return "friday_late_after_10co"
    return trade.session


def load_decisions() -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    if not DECISIONS_DIR.exists():
        return decisions
    for path in DECISIONS_DIR.glob("*/magi_decisions.jsonl"):
        for row in read_jsonl(path):
            did = str(row.get("decision_id") or "")
            if did:
                decisions[did] = row
    return decisions


def find_decision(short_or_full: str, decisions: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not short_or_full:
        return None
    if short_or_full in decisions:
        return decisions[short_or_full]
    for did, row in decisions.items():
        if did.startswith(short_or_full):
            return row
    return None


def load_snapshot_info() -> dict[str, dict[str, Any]]:
    info: dict[str, dict[str, Any]] = {}
    if not SNAPSHOTS_DIR.exists():
        return info
    for path in SNAPSHOTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        sid = str(data.get("snapshot_id") or "")
        if not sid:
            continue
        source = data.get("source", {})
        mode = data.get("source_mode") or source.get("source_mode") or ""
        market = data.get("market", {})
        info[sid] = {
            "mode": str(mode),
            "session": str(market.get("session") or ""),
            "spread_pips": safe_float(market.get("spread_pips"), default=float("nan")),
        }
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
    close_price = safe_float(close_event.get("price"))
    entry = safe_float(open_event.get("price"))
    sl = safe_float(open_event.get("sl"))
    tp = safe_float(open_event.get("tp"))
    if "tp" in comment or (tp and abs(close_price - tp) < 0.00002):
        return "TP", TP_USD
    if "sl" in comment or (sl and abs(close_price - sl) < 0.00002):
        if abs(close_price - entry) < 0.00003:
            return "BE", BE_USD
        return "SL", SL_USD
    if abs(close_price - entry) < 0.00003:
        return "BE", BE_USD
    return "SAFETY_PARTIAL", 0.0


def load_live_trades() -> list[Trade]:
    decisions = load_decisions()
    snapshots = load_snapshot_info()
    events = load_botc_events()
    opens = [e for e in events if str(e.get("event_type")) == "open"]
    closes: dict[str, dict[str, Any]] = {}
    for e in events:
        if str(e.get("event_type")) != "close":
            continue
        ticket = str(int(safe_float(e.get("ticket")))) if safe_float(e.get("ticket")) else str(e.get("ticket") or "")
        closes.setdefault(ticket, e)

    trades: list[Trade] = []
    for open_event in opens:
        ticket = str(int(safe_float(open_event.get("ticket")))) if safe_float(open_event.get("ticket")) else str(open_event.get("ticket") or "")
        entry_time = parse_dt(open_event.get("timestamp"))
        if entry_time is None:
            continue
        close_event = closes.get(ticket)
        exit_time = parse_dt(close_event.get("timestamp")) if close_event else None
        short_decision = str(open_event.get("decision_id") or "")
        decision = find_decision(short_decision, decisions)
        did = str(decision.get("decision_id") if decision else short_decision)
        sid = str(decision.get("snapshot_id") if decision else "")
        payload = decision.get("execution_payload", {}) if decision else {}
        details = payload.get("details", {}) if isinstance(payload, dict) else {}
        direction = str(details.get("order_type") or "").upper()
        if direction not in {"BUY", "SELL"}:
            direction = "UNKNOWN"
        snap = snapshots.get(sid, {})
        mode = str(snap.get("mode") or "")
        synthetic = "synthetic" in sid.lower() or "synthetic" in mode.lower()
        session = str(snap.get("session") or session_for_utc(entry_time))
        spread_raw = snap.get("spread_pips")
        spread = None if spread_raw is None or math.isnan(safe_float(spread_raw, default=float("nan"))) else safe_float(spread_raw)
        result, pnl = classify_result(open_event, close_event)
        if result == "OPEN":
            continue
        trades.append(
            Trade(
                dataset="live_demo_organic_normalized_usd",
                ticket=ticket,
                symbol=str(open_event.get("symbol") or ""),
                direction=direction,
                entry_time=entry_time,
                exit_time=exit_time,
                result=result,
                pnl=pnl,
                session=session,
                spread_pips=spread,
                decision_id=did,
                snapshot_id=sid,
                synthetic=synthetic,
            )
        )
    trades.sort(key=lambda t: t.entry_time)
    return [t for t in trades if not t.synthetic]


def parse_sim_csv(path: Path) -> list[Trade]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    trades: list[Trade] = []
    for i, row in enumerate(rows):
        action = str(row.get("action") or row.get("prediction") or "").upper()
        if action and action not in {"ENTER", "ENTER_BUY", "ENTER_SELL"}:
            continue
        direction = str(row.get("direction") or "").upper()
        pred = str(row.get("prediction") or "").upper()
        if not direction:
            if pred.endswith("BUY"):
                direction = "BUY"
            elif pred.endswith("SELL"):
                direction = "SELL"
        if direction not in {"BUY", "SELL"}:
            continue
        entry = parse_dt(row.get("entry_time")) or parse_dt(row.get("entry_datetime")) or parse_dt(row.get("timestamp"))
        if entry is None:
            continue
        exit_time = parse_dt(row.get("exit_time")) or parse_dt(row.get("exit_timestamp")) or parse_dt(row.get("exit_timestamp_raw"))
        result = str(row.get("result") or row.get("first_touch") or "").upper()
        r = safe_float(row.get("realized_R"), default=float("nan"))
        if math.isnan(r):
            r = safe_float(row.get("adjusted_R"), default=float("nan"))
        if math.isnan(r):
            r = 1.0 if result in {"WIN", "TP"} else -1.0 if result in {"LOSS", "SL"} else 0.0
        if result == "TP":
            result = "WIN"
        elif result == "SL":
            result = "LOSS"
        elif not result:
            result = "WIN" if r > 0 else "LOSS" if r < 0 else "BE"
        trades.append(
            Trade(
                dataset=path.as_posix().replace(ROOT.as_posix() + "/", ""),
                ticket=str(i + 1),
                symbol=str(row.get("symbol") or "EURUSD"),
                direction=direction,
                entry_time=entry,
                exit_time=exit_time,
                result=result,
                pnl=r,
                session=str(row.get("session") or session_for_utc(entry)),
                spread_pips=safe_float(row.get("spread_pips"), default=float("nan")),
                decision_id=str(row.get("decision_id") or ""),
            )
        )
    trades.sort(key=lambda t: t.entry_time)
    return trades


def is_win(t: Trade) -> bool:
    return t.result in {"TP", "WIN"} or t.pnl > 0


def is_loss(t: Trade) -> bool:
    return t.result in {"SL", "LOSS"} or t.pnl < 0


def max_streak(trades: list[Trade], predicate) -> int:
    current = 0
    best = 0
    for t in sorted(trades, key=lambda x: x.entry_time):
        if predicate(t):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def max_drawdown(trades: list[Trade]) -> float:
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for t in sorted(trades, key=lambda x: x.entry_time):
        equity += t.pnl
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return dd


def metrics(trades: list[Trade]) -> dict[str, Any]:
    wins = sum(1 for t in trades if is_win(t))
    losses = sum(1 for t in trades if is_loss(t))
    be = sum(1 for t in trades if t.result == "BE")
    net = sum(t.pnl for t in trades)
    gross_win = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = -sum(t.pnl for t in trades if t.pnl < 0)
    pf = gross_win / gross_loss if gross_loss else None
    return {
        "trades": len(trades),
        "tp": wins,
        "sl": losses,
        "be": be,
        "win_rate": wins / (wins + losses) if wins + losses else None,
        "profit_factor": pf,
        "net": net,
        "avg_r_or_pnl": net / len(trades) if trades else None,
        "max_drawdown": max_drawdown(trades),
        "worst_loss_streak": max_streak(trades, is_loss),
        "best_win_streak": max_streak(trades, is_win),
    }


def fast_reentries(trades: list[Trade]) -> list[Trade]:
    out: list[Trade] = []
    previous: Trade | None = None
    for trade in sorted(trades, key=lambda t: t.entry_time):
        if previous and previous.exit_time and is_loss(previous):
            minutes = (trade.entry_time - previous.exit_time).total_seconds() / 60
            if 0 <= minutes <= 180 and trade.direction == previous.direction:
                out.append(trade)
        previous = trade
    return out


def group_rows(dataset: str, trades: list[Trade]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    weekdays = ["lunes", "martes", "miercoles", "jueves", "viernes"]
    for day in weekdays:
        subset = [t for t in trades if weekday_name(t.entry_time) == day]
        m = metrics(subset)
        rows.append(
            {
                "dataset": dataset,
                "weekday": day,
                **format_metrics(m),
                "fast_reentries_3h_same_direction": len(fast_reentries(subset)),
                "avg_spread_pips": average_spread(subset),
            }
        )
    return rows


def friday_session_rows(dataset: str, trades: list[Trade]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    friday = [t for t in trades if is_friday(t.entry_time)]
    buckets = ["london", "overlap", "new_york", "friday_late_after_10co", "friday_late_after_12co"]
    for bucket in buckets:
        if bucket.startswith("friday_late"):
            subset = [t for t in friday if friday_bucket(t) == bucket]
        else:
            subset = [t for t in friday if t.session == bucket]
        m = metrics(subset)
        rows.append(
            {
                "dataset": dataset,
                "friday_segment": bucket,
                **format_metrics(m),
                "fast_reentries_3h_same_direction": len(fast_reentries(subset)),
                "avg_spread_pips": average_spread(subset),
            }
        )
    return rows


def average_spread(trades: list[Trade]) -> str:
    vals = [t.spread_pips for t in trades if t.spread_pips is not None and not math.isnan(t.spread_pips)]
    if not vals:
        return ""
    return round(sum(vals) / len(vals), 4)


def format_metrics(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "trades": m["trades"],
        "tp": m["tp"],
        "sl": m["sl"],
        "be": m["be"],
        "win_rate": round(m["win_rate"], 4) if m["win_rate"] is not None else "",
        "profit_factor": round(m["profit_factor"], 4) if m["profit_factor"] is not None else "",
        "net": round(m["net"], 6),
        "avg_r_or_pnl": round(m["avg_r_or_pnl"], 6) if m["avg_r_or_pnl"] is not None else "",
        "max_drawdown": round(m["max_drawdown"], 6),
        "worst_loss_streak": m["worst_loss_streak"],
        "best_win_streak": m["best_win_streak"],
    }


def apply_friday_rule(trades: list[Trade], rule: str) -> tuple[list[Trade], list[Trade]]:
    kept: list[Trade] = []
    removed: list[Trade] = []
    friday_session_counts: dict[tuple[str, str], int] = {}
    friday_loss_count: dict[str, int] = {}
    block_friday_after_loss: dict[str, bool] = {}

    for trade in sorted(trades, key=lambda t: t.entry_time):
        local = trade.entry_time.astimezone(BOGOTA)
        day_key = local.date().isoformat()
        friday = is_friday(trade.entry_time)
        blocked = False
        hour = friday_hour_co(trade.entry_time)
        if friday:
            if rule == "A_after_12co" and hour >= 12:
                blocked = True
            elif rule == "B_after_10co" and hour >= 10:
                blocked = True
            elif rule == "C_max_1_trade_per_session":
                key = (day_key, trade.session)
                if friday_session_counts.get(key, 0) >= 1:
                    blocked = True
            elif rule == "D_after_1_sl_until_monday" and block_friday_after_loss.get(day_key):
                blocked = True
            elif rule == "E_after_2_sl_until_monday" and friday_loss_count.get(day_key, 0) >= 2:
                blocked = True
            elif rule == "F_late_only_manage_after_12co" and hour >= 12:
                blocked = True

        if blocked:
            removed.append(trade)
            continue
        kept.append(trade)
        if friday:
            friday_session_counts[(day_key, trade.session)] = friday_session_counts.get((day_key, trade.session), 0) + 1
            if is_loss(trade):
                friday_loss_count[day_key] = friday_loss_count.get(day_key, 0) + 1
                if rule == "D_after_1_sl_until_monday":
                    block_friday_after_loss[day_key] = True
    return kept, removed


def scenario_rows(dataset: str, trades: list[Trade]) -> list[dict[str, Any]]:
    baseline = metrics(trades)
    rules = {
        "Baseline": None,
        "Friday Rule A - no opens after 12:00 Colombia": "A_after_12co",
        "Friday Rule B - no opens after 10:00 Colombia": "B_after_10co",
        "Friday Rule C - max 1 trade per session": "C_max_1_trade_per_session",
        "Friday Rule D - after 1 SL safe until Monday": "D_after_1_sl_until_monday",
        "Friday Rule E - after 2 SL safe until Monday": "E_after_2_sl_until_monday",
        "Friday Rule F - late only manage, no new opens": "F_late_only_manage_after_12co",
    }
    rows: list[dict[str, Any]] = []
    for label, code in rules.items():
        kept, removed = (trades, []) if code is None else apply_friday_rule(trades, code)
        m = metrics(kept)
        removed_m = metrics(removed)
        rows.append(
            {
                "dataset": dataset,
                "scenario": label,
                **format_metrics(m),
                "trades_removed": len(removed),
                "tp_removed": removed_m["tp"],
                "sl_removed": removed_m["sl"],
                "be_removed": removed_m["be"],
                "removed_net": round(sum(t.pnl for t in removed), 6),
                "net_delta_vs_baseline": round(m["net"] - baseline["net"], 6),
                "dd_delta_vs_baseline": round(m["max_drawdown"] - baseline["max_drawdown"], 6),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_Sin datos._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines)


def load_datasets() -> dict[str, list[Trade]]:
    paths = [
        ROOT / "artifacts" / "ceo_magi_v3" / "stress_months_trade_detail.csv",
        ROOT / "artifacts" / "ceo_magi_v3" / "ceo_magi_v3_decisions.csv",
        ROOT / "artifacts" / "ceo_magi_v3" / "random_3_months_trade_audit.csv",
        ROOT / "artifacts" / "magi_realistic_scenario_c" / "scenario_c_realistic_trades.csv",
        ROOT
        / "data"
        / "output"
        / "magi_v2"
        / "baltasar_v2_rich_features_model"
        / "policy_medium_r_simulation"
        / "simulated_trades_050.csv",
    ]
    datasets = {"live_demo_organic_normalized_usd": load_live_trades()}
    for path in paths:
        if path.exists():
            trades = parse_sim_csv(path)
            if trades:
                datasets[path.as_posix().replace(ROOT.as_posix() + "/", "")] = trades
    return datasets


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    datasets = load_datasets()

    weekday_rows: list[dict[str, Any]] = []
    session_rows: list[dict[str, Any]] = []
    scenario_all: list[dict[str, Any]] = []
    for name, trades in datasets.items():
        weekday_rows.extend(group_rows(name, trades))
        session_rows.extend(friday_session_rows(name, trades))
        scenario_all.extend(scenario_rows(name, trades))

    write_csv(WEEKDAY_CSV, weekday_rows)
    write_csv(SESSION_CSV, session_rows)
    write_csv(SCENARIOS_CSV, scenario_all)

    live_weekday = [r for r in weekday_rows if r["dataset"] == "live_demo_organic_normalized_usd"]
    live_sessions = [r for r in session_rows if r["dataset"] == "live_demo_organic_normalized_usd"]
    live_scenarios = [r for r in scenario_all if r["dataset"] == "live_demo_organic_normalized_usd"]

    historical_baselines = [
        r for r in weekday_rows if r["dataset"] != "live_demo_organic_normalized_usd" and r["weekday"] == "viernes"
    ]
    historical_scenarios = [r for r in scenario_all if r["dataset"] != "live_demo_organic_normalized_usd"]

    report: list[str] = []
    report.append("# Patron de perdidas de viernes en MAGI\n")
    report.append("Fecha de corte: 2026-05-15\n")
    report.append("Zona horaria para reglas viernes: America/Bogota (UTC-5).\n")
    report.append("## Resumen ejecutivo\n")
    report.append(
        "Conclusion categorizada: **2. Patron parcial: viernes tarde/New York es peor, pero no todo el viernes**. "
        "El viernes 15 si fue malo y concentrado en reentradas durante overlap/New York, "
        "pero la evidencia historica no confirma que todo viernes sea estructuralmente perdedor. "
        "Los viernes tarde muestran riesgo operativo en live y algunos filtros mejoran drawdown, "
        "aunque en backtests amplios los filtros viernes pueden recortar bastante rentabilidad.\n"
    )
    report.append("## 1. Demo/live por dia de la semana\n")
    report.append(
        markdown_table(
            live_weekday,
            [
                "weekday",
                "trades",
                "tp",
                "sl",
                "be",
                "win_rate",
                "profit_factor",
                "net",
                "avg_r_or_pnl",
                "max_drawdown",
                "worst_loss_streak",
                "best_win_streak",
                "fast_reentries_3h_same_direction",
                "avg_spread_pips",
            ],
        )
    )
    report.append("\n\n## 2. Viernes live por sesion/franja\n")
    report.append(
        markdown_table(
            live_sessions,
            [
                "friday_segment",
                "trades",
                "tp",
                "sl",
                "be",
                "win_rate",
                "profit_factor",
                "net",
                "max_drawdown",
                "worst_loss_streak",
                "fast_reentries_3h_same_direction",
                "avg_spread_pips",
            ],
        )
    )
    report.append("\n\n## 3. Escenarios de regla viernes en live\n")
    report.append(
        markdown_table(
            live_scenarios,
            [
                "scenario",
                "trades",
                "tp",
                "sl",
                "be",
                "net",
                "profit_factor",
                "max_drawdown",
                "trades_removed",
                "tp_removed",
                "sl_removed",
                "removed_net",
                "net_delta_vs_baseline",
                "dd_delta_vs_baseline",
            ],
        )
    )
    report.append("\n\n## 4. Viernes en backtests/simulaciones\n")
    report.append(
        markdown_table(
            historical_baselines,
            [
                "dataset",
                "trades",
                "tp",
                "sl",
                "win_rate",
                "profit_factor",
                "net",
                "avg_r_or_pnl",
                "max_drawdown",
                "worst_loss_streak",
                "fast_reentries_3h_same_direction",
                "avg_spread_pips",
            ],
        )
    )
    report.append("\n\n## 5. Filtros viernes sobre backtests/simulaciones\n")
    report.append(
        markdown_table(
            historical_scenarios,
            [
                "dataset",
                "scenario",
                "trades",
                "tp",
                "sl",
                "net",
                "profit_factor",
                "max_drawdown",
                "trades_removed",
                "tp_removed",
                "sl_removed",
                "net_delta_vs_baseline",
                "dd_delta_vs_baseline",
            ],
        )
    )
    report.append("\n\n## 6. Respuestas directas\n")
    report.append("- **El viernes 15 fue coherente con un riesgo operativo real**, pero no basta para afirmar que todos los viernes son malos.\n")
    report.append("- **MAGI no pierde historicamente mas todos los viernes de forma clara** en todos los datasets. Hay datasets donde viernes sigue siendo rentable.\n")
    report.append("- **Viernes tarde/New York si es la zona que mas merece guardrail**, especialmente despues de SL o con spread deteriorado.\n")
    report.append("- **El patron aparece muy fuerte en demo/live reciente** y parcialmente en simulaciones via drawdown/filtros, pero no como ley universal.\n")
    report.append("- **La muestra live es insuficiente para apagar todo viernes**, pero suficiente para disenar una regla preventiva de viernes tarde y perdida agrupada.\n")
    report.append("- **Friday Rule F equivale a Rule A en los datos actuales**, porque se modela como no abrir despues de 12:00 Colombia y no habia eventos de gestion separados en los CSV historicos.\n")
    report.append("\n## 7. Recomendacion\n")
    report.append(
        "Antes del 5 de junio conviene implementar una regla viernes prudente, pero no un bloqueo total de viernes. "
        "La mejor direccion es: viernes despues de 12:00 Colombia no abrir nuevas operaciones si ya hubo SL en el dia, "
        "y activar SAFE_MODE tras 2 SL de viernes. Tambien conviene limitar viernes tarde a gestion de posiciones abiertas.\n"
    )
    report.append("- **Melchor:** debe evaluar `friday_risk`, `friday_late`, `friday_loss_count`, `spread_deteriorated`.\n")
    report.append("- **CEO-MAGI/backend:** debe persistir estado diario y convertir el bloqueo en HOLD/SAFE_MODE trazable.\n")
    report.append("- **Bot B:** no debe decidir la regla; solo respetar payload y proteger contra duplicados.\n")
    report.append("- **Dashboard/auditoria:** mostrar `friday_guardrail_active`, motivo y hora de desbloqueo.\n")
    report.append("\n## 8. Archivos generados\n")
    report.append(f"- `{WEEKDAY_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{SESSION_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{SCENARIOS_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{REPORT_MD.relative_to(ROOT)}`\n")

    REPORT_MD.write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
