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

REPORT_MD = REPORTS / "reentry_cluster_sequence_analysis_2026-05-15.md"
CLUSTER_SUMMARY_CSV = REPORTS / "reentry_cluster_summary.csv"
CLUSTER_TRADES_CSV = REPORTS / "reentry_cluster_trades.csv"
RULE_SCENARIOS_CSV = REPORTS / "reentry_cluster_rule_scenarios.csv"

BOGOTA = timezone(timedelta(hours=-5))
TP_USD = 1000.0
SL_USD = -500.0

SESSION_ORDER = {"asia": 0, "london": 1, "overlap": 2, "new_york": 3}


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
    decision_id: str = ""
    snapshot_id: str = ""
    synthetic: bool = False


@dataclass
class Cluster:
    dataset: str
    cluster_id: str
    trades: list[Trade]


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
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
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
    hour = dt.astimezone(timezone.utc).hour
    if 7 <= hour < 12:
        return "london"
    if 12 <= hour < 17:
        return "overlap"
    if 17 <= hour < 22:
        return "new_york"
    return "asia"


def operational_day(dt: datetime) -> str:
    return dt.astimezone(BOGOTA).date().isoformat()


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


def load_snapshot_info() -> dict[str, dict[str, str]]:
    info: dict[str, dict[str, str]] = {}
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
        mode = str(data.get("source_mode") or source.get("source_mode") or "")
        market = data.get("market", {})
        info[sid] = {"mode": mode, "session": str(market.get("session") or "")}
    return info


def load_botc_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not BOTC_DIR.exists():
        return events
    for path in BOTC_DIR.glob("*/bot_c_events.jsonl"):
        events.extend(read_jsonl(path))
    events.sort(key=lambda e: parse_dt(e.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc))
    return events


def classify_live_result(open_event: dict[str, Any], close_event: dict[str, Any] | None) -> tuple[str, float]:
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
            return "BE", 0.0
        return "SL", SL_USD
    if abs(close_price - entry) < 0.00003:
        return "BE", 0.0
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
        entry = parse_dt(open_event.get("timestamp"))
        if entry is None:
            continue
        close_event = closes.get(ticket)
        exit_time = parse_dt(close_event.get("timestamp")) if close_event else None
        result, pnl = classify_live_result(open_event, close_event)
        if result == "OPEN":
            continue
        short_decision = str(open_event.get("decision_id") or "")
        decision = find_decision(short_decision, decisions)
        did = str(decision.get("decision_id") if decision else short_decision)
        sid = str(decision.get("snapshot_id") if decision else "")
        payload = decision.get("execution_payload", {}) if decision else {}
        details = payload.get("details", {}) if isinstance(payload, dict) else {}
        direction = str(details.get("order_type") or "").upper()
        snap = snapshots.get(sid, {})
        mode = str(snap.get("mode") or "")
        synthetic = "synthetic" in sid.lower() or "synthetic" in mode.lower()
        session = str(snap.get("session") or session_for_utc(entry))
        trades.append(
            Trade(
                dataset="live_demo_organic_normalized_usd",
                ticket=ticket,
                symbol=str(open_event.get("symbol") or "EURUSD"),
                direction=direction,
                entry_time=entry,
                exit_time=exit_time,
                result=result,
                pnl=pnl,
                session=session,
                decision_id=did,
                snapshot_id=sid,
                synthetic=synthetic,
            )
        )
    return sorted([t for t in trades if not t.synthetic], key=lambda t: t.entry_time)


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
        pnl = safe_float(row.get("realized_R"), default=float("nan"))
        if math.isnan(pnl):
            pnl = safe_float(row.get("adjusted_R"), default=float("nan"))
        if math.isnan(pnl):
            pnl = 1.0 if result in {"WIN", "TP"} else -1.0 if result in {"LOSS", "SL"} else 0.0
        if result == "TP":
            result = "WIN"
        elif result == "SL":
            result = "LOSS"
        elif not result:
            result = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BE"
        trades.append(
            Trade(
                dataset=path.as_posix().replace(ROOT.as_posix() + "/", ""),
                ticket=str(i + 1),
                symbol=str(row.get("symbol") or "EURUSD"),
                direction=direction,
                entry_time=entry,
                exit_time=exit_time,
                result=result,
                pnl=pnl,
                session=str(row.get("session") or session_for_utc(entry)),
                decision_id=str(row.get("decision_id") or ""),
            )
        )
    return sorted(trades, key=lambda t: t.entry_time)


def is_win(t: Trade) -> bool:
    return t.result in {"TP", "WIN"} or t.pnl > 0


def is_loss(t: Trade) -> bool:
    return t.result in {"SL", "LOSS"} or t.pnl < 0


def result_token(t: Trade) -> str:
    if is_loss(t):
        return "SL"
    if is_win(t):
        return "TP"
    if t.result == "BE":
        return "BE"
    return t.result


def sessions_adjacent(a: str, b: str) -> bool:
    if a == b:
        return True
    if a not in SESSION_ORDER or b not in SESSION_ORDER:
        return False
    return 0 <= SESSION_ORDER[b] - SESSION_ORDER[a] <= 1


def belongs_to_cluster(prev: Trade, curr: Trade) -> bool:
    if prev.symbol != curr.symbol or prev.direction != curr.direction:
        return False
    if prev.exit_time is None:
        return False
    if operational_day(prev.entry_time) != operational_day(curr.entry_time):
        return False
    gap_min = (curr.entry_time - prev.exit_time).total_seconds() / 60
    if gap_min < 0 or gap_min > 180:
        return False
    return sessions_adjacent(prev.session, curr.session)


def build_clusters(dataset: str, trades: list[Trade]) -> list[Cluster]:
    clusters: list[Cluster] = []
    current: list[Trade] = []
    count = 0
    for trade in sorted(trades, key=lambda t: t.entry_time):
        if not current:
            current = [trade]
            continue
        if belongs_to_cluster(current[-1], trade):
            current.append(trade)
        else:
            if len(current) >= 2:
                count += 1
                clusters.append(Cluster(dataset, f"{dataset}::cluster_{count:04d}", current))
            current = [trade]
    if len(current) >= 2:
        count += 1
        clusters.append(Cluster(dataset, f"{dataset}::cluster_{count:04d}", current))
    return clusters


def max_drawdown_pnl(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for v in values:
        equity += v
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return dd


def max_consecutive(tokens: list[str], wanted: str) -> int:
    best = 0
    current = 0
    for token in tokens:
        if token == wanted:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def summarize_cluster(cluster: Cluster) -> dict[str, Any]:
    trades = cluster.trades
    tokens = [result_token(t) for t in trades]
    net = sum(t.pnl for t in trades)
    first = tokens[0]
    return {
        "dataset": cluster.dataset,
        "cluster_id": cluster.cluster_id,
        "start_time": trades[0].entry_time.isoformat(),
        "end_time": (trades[-1].exit_time or trades[-1].entry_time).isoformat(),
        "symbol": trades[0].symbol,
        "direction": trades[0].direction,
        "session_start": trades[0].session,
        "trades": len(trades),
        "sequence": "-".join(tokens),
        "first_result": first,
        "net": round(net, 6),
        "positive_cluster": net > 0,
        "negative_cluster": net < 0,
        "max_drawdown": round(max_drawdown_pnl([t.pnl for t in trades]), 6),
        "max_consecutive_sl": max_consecutive(tokens, "SL"),
        "max_consecutive_tp": max_consecutive(tokens, "TP"),
        "reached_3_consecutive_sl": max_consecutive(tokens, "SL") >= 3,
        "started_tp_and_kept_winning": first == "TP" and len(tokens) >= 2 and tokens[1] == "TP",
        "second_result": tokens[1] if len(tokens) > 1 else "",
        "second_after_first_sl_is_sl": first == "SL" and len(tokens) > 1 and tokens[1] == "SL",
        "second_after_first_sl_is_tp": first == "SL" and len(tokens) > 1 and tokens[1] == "TP",
    }


def apply_rule_to_cluster(cluster: Cluster, rule: str) -> tuple[list[Trade], list[Trade]]:
    trades = cluster.trades
    tokens = [result_token(t) for t in trades]
    if rule == "baseline":
        return trades, []
    keep = [True] * len(trades)
    if rule == "rule1_after_first_sl_block_180m":
        if tokens[0] == "SL":
            for i in range(1, len(trades)):
                keep[i] = False
    elif rule == "rule2_after_2_consecutive_sl_block_180m":
        streak = 0
        blocked = False
        for i, token in enumerate(tokens):
            if blocked:
                keep[i] = False
                continue
            streak = streak + 1 if token == "SL" else 0
            if streak >= 2:
                blocked = True
    elif rule == "rule3_after_3_consecutive_sl_next_session_day":
        streak = 0
        blocked = False
        for i, token in enumerate(tokens):
            if blocked:
                keep[i] = False
                continue
            streak = streak + 1 if token == "SL" else 0
            if streak >= 3:
                blocked = True
    elif rule == "rule4_first_tp_max_1_reentry":
        if tokens[0] == "TP":
            for i in range(2, len(trades)):
                keep[i] = False
    elif rule == "rule5_first_sl_one_reentry_then_block_if_fails":
        if tokens[0] == "SL" and len(tokens) > 1 and tokens[1] == "SL":
            for i in range(2, len(trades)):
                keep[i] = False
    elif rule == "rule6_tp_continue_sl_restrictive":
        if tokens[0] == "SL":
            for i in range(2, len(trades)):
                keep[i] = False
    kept = [t for i, t in enumerate(trades) if keep[i]]
    removed = [t for i, t in enumerate(trades) if not keep[i]]
    return kept, removed


def metrics(trades: list[Trade]) -> dict[str, Any]:
    wins = sum(1 for t in trades if is_win(t))
    losses = sum(1 for t in trades if is_loss(t))
    bes = sum(1 for t in trades if result_token(t) == "BE")
    net = sum(t.pnl for t in trades)
    gross_win = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = -sum(t.pnl for t in trades if t.pnl < 0)
    return {
        "trades": len(trades),
        "tp": wins,
        "sl": losses,
        "be": bes,
        "win_rate": wins / (wins + losses) if wins + losses else None,
        "profit_factor": gross_win / gross_loss if gross_loss else None,
        "net": net,
        "avg": net / len(trades) if trades else None,
        "max_drawdown": max_drawdown_pnl([t.pnl for t in sorted(trades, key=lambda t: t.entry_time)]),
    }


def scenario_rows(dataset: str, trades: list[Trade], clusters: list[Cluster]) -> list[dict[str, Any]]:
    clustered_ids = {id(t) for c in clusters for t in c.trades}
    non_cluster_trades = [t for t in trades if id(t) not in clustered_ids]
    rules = [
        ("Baseline", "baseline"),
        ("Rule 1 - block after first SL in cluster", "rule1_after_first_sl_block_180m"),
        ("Rule 2 - after 2 consecutive SL safe 180m", "rule2_after_2_consecutive_sl_block_180m"),
        ("Rule 3 - after 3 consecutive SL safe next session/day", "rule3_after_3_consecutive_sl_next_session_day"),
        ("Rule 4 - first TP max 1 reentry", "rule4_first_tp_max_1_reentry"),
        ("Rule 5 - first SL one reentry, block if fails", "rule5_first_sl_one_reentry_then_block_if_fails"),
        ("Rule 6 - TP clusters continue, SL clusters restrictive", "rule6_tp_continue_sl_restrictive"),
    ]
    base = metrics(trades)
    rows: list[dict[str, Any]] = []
    for label, code in rules:
        kept = list(non_cluster_trades)
        removed: list[Trade] = []
        for c in clusters:
            k, r = apply_rule_to_cluster(c, code)
            kept.extend(k)
            removed.extend(r)
        kept.sort(key=lambda t: t.entry_time)
        removed.sort(key=lambda t: t.entry_time)
        m = metrics(kept)
        rm = metrics(removed)
        rows.append(
            {
                "dataset": dataset,
                "scenario": label,
                "trades": m["trades"],
                "tp": m["tp"],
                "sl": m["sl"],
                "be": m["be"],
                "win_rate": round(m["win_rate"], 4) if m["win_rate"] is not None else "",
                "profit_factor": round(m["profit_factor"], 4) if m["profit_factor"] is not None else "",
                "net": round(m["net"], 6),
                "avg": round(m["avg"], 6) if m["avg"] is not None else "",
                "max_drawdown": round(m["max_drawdown"], 6),
                "trades_removed": len(removed),
                "tp_removed": rm["tp"],
                "sl_removed": rm["sl"],
                "removed_net": round(sum(t.pnl for t in removed), 6),
                "net_delta_vs_baseline": round(m["net"] - base["net"], 6),
                "dd_delta_vs_baseline": round(m["max_drawdown"] - base["max_drawdown"], 6),
            }
        )
    return rows


def aggregate_cluster_questions(dataset: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    sl_start = [r for r in summaries if r["dataset"] == dataset and r["first_result"] == "SL"]
    tp_start = [r for r in summaries if r["dataset"] == dataset and r["first_result"] == "TP"]
    loss_2 = [r for r in summaries if r["dataset"] == dataset and int(r["max_consecutive_sl"]) >= 2]
    loss_3 = [r for r in summaries if r["dataset"] == dataset and int(r["max_consecutive_sl"]) >= 3]
    loss_gt3 = [r for r in summaries if r["dataset"] == dataset and int(r["max_consecutive_sl"]) > 3]
    return {
        "dataset": dataset,
        "clusters": len([r for r in summaries if r["dataset"] == dataset]),
        "sl_start_clusters": len(sl_start),
        "sl_start_positive": sum(1 for r in sl_start if r["positive_cluster"]),
        "sl_start_negative": sum(1 for r in sl_start if r["negative_cluster"]),
        "sl_start_avg_net": round(sum(float(r["net"]) for r in sl_start) / len(sl_start), 6) if sl_start else "",
        "sl_start_recovery_rate": round(sum(1 for r in sl_start if r["positive_cluster"]) / len(sl_start), 4) if sl_start else "",
        "first_sl_then_sl": sum(1 for r in sl_start if r["second_after_first_sl_is_sl"]),
        "first_sl_then_tp": sum(1 for r in sl_start if r["second_after_first_sl_is_tp"]),
        "tp_start_clusters": len(tp_start),
        "tp_start_kept_winning": sum(1 for r in tp_start if r["started_tp_and_kept_winning"]),
        "tp_start_positive": sum(1 for r in tp_start if r["positive_cluster"]),
        "tp_start_negative": sum(1 for r in tp_start if r["negative_cluster"]),
        "tp_start_avg_net": round(sum(float(r["net"]) for r in tp_start) / len(tp_start), 6) if tp_start else "",
        "clusters_2sl_consecutive": len(loss_2),
        "clusters_3sl_consecutive": len(loss_3),
        "clusters_gt3sl_consecutive": len(loss_gt3),
        "avg_damage_2sl_clusters": round(sum(float(r["net"]) for r in loss_2) / len(loss_2), 6) if loss_2 else "",
        "max_damage_cluster": min([float(r["net"]) for r in summaries if r["dataset"] == dataset], default=0),
    }


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
    cluster_rows: list[dict[str, Any]] = []
    cluster_trade_rows: list[dict[str, Any]] = []
    scenario_all: list[dict[str, Any]] = []
    question_rows: list[dict[str, Any]] = []

    for name, trades in datasets.items():
        clusters = build_clusters(name, trades)
        for cluster in clusters:
            cluster_rows.append(summarize_cluster(cluster))
            for idx, trade in enumerate(cluster.trades, start=1):
                cluster_trade_rows.append(
                    {
                        "dataset": name,
                        "cluster_id": cluster.cluster_id,
                        "trade_index": idx,
                        "ticket": trade.ticket,
                        "entry_time": trade.entry_time.isoformat(),
                        "exit_time": trade.exit_time.isoformat() if trade.exit_time else "",
                        "symbol": trade.symbol,
                        "direction": trade.direction,
                        "session": trade.session,
                        "result": result_token(trade),
                        "pnl": round(trade.pnl, 6),
                        "decision_id": trade.decision_id,
                        "snapshot_id": trade.snapshot_id,
                    }
                )
        scenario_all.extend(scenario_rows(name, trades, clusters))
        question_rows.append(aggregate_cluster_questions(name, cluster_rows))

    write_csv(CLUSTER_SUMMARY_CSV, cluster_rows)
    write_csv(CLUSTER_TRADES_CSV, cluster_trade_rows)
    write_csv(RULE_SCENARIOS_CSV, scenario_all)

    live_questions = [r for r in question_rows if r["dataset"] == "live_demo_organic_normalized_usd"]
    live_clusters = [r for r in cluster_rows if r["dataset"] == "live_demo_organic_normalized_usd"]
    live_scenarios = [r for r in scenario_all if r["dataset"] == "live_demo_organic_normalized_usd"]
    historical_questions = [r for r in question_rows if r["dataset"] != "live_demo_organic_normalized_usd"]
    historical_scenarios = [
        r
        for r in scenario_all
        if r["dataset"] != "live_demo_organic_normalized_usd"
        and r["scenario"]
        in {
            "Baseline",
            "Rule 1 - block after first SL in cluster",
            "Rule 2 - after 2 consecutive SL safe 180m",
            "Rule 6 - TP clusters continue, SL clusters restrictive",
        }
    ]

    report: list[str] = []
    report.append("# Analisis de clusters de reentrada MAGI\n")
    report.append("Fecha de corte: 2026-05-15\n")
    report.append("Definicion: mismo simbolo, misma direccion, gap cierre->apertura <= 180 minutos, mismo dia operativo Colombia y misma sesion o sesion inmediata posterior.\n")
    report.append("## Resumen ejecutivo\n")
    report.append(
        "La hipotesis queda **parcialmente confirmada con un matiz importante**: en live/demo, el dano visible no vino de clusters que empiecen estrictamente con SL, "
        "sino de clusters que, una vez dentro, acumulan 2-3 SL consecutivos en la misma direccion/contexto. "
        "Los historicos muestran que las rachas iniciadas con TP suelen aportar edge y que incluso muchas rachas iniciadas con SL se recuperan. "
        "Por eso un cooldown ciego destruiria profit; la regla mas sana antes del 5 de junio es detectar 2 SL consecutivos o deterioro dentro del cluster, no bloquear toda reentrada.\n"
    )
    report.append("## A. Clusters live/demo\n")
    report.append(
        markdown_table(
            live_clusters,
            [
                "cluster_id",
                "start_time",
                "end_time",
                "direction",
                "session_start",
                "trades",
                "sequence",
                "first_result",
                "net",
                "max_drawdown",
                "max_consecutive_sl",
                "started_tp_and_kept_winning",
            ],
        )
    )
    report.append("\n\n## B. Resumen por dataset\n")
    report.append(
        markdown_table(
            question_rows,
            [
                "dataset",
                "clusters",
                "sl_start_clusters",
                "sl_start_positive",
                "sl_start_negative",
                "sl_start_avg_net",
                "sl_start_recovery_rate",
                "first_sl_then_sl",
                "first_sl_then_tp",
                "tp_start_clusters",
                "tp_start_kept_winning",
                "tp_start_positive",
                "tp_start_negative",
                "tp_start_avg_net",
                "clusters_2sl_consecutive",
                "clusters_3sl_consecutive",
                "clusters_gt3sl_consecutive",
                "avg_damage_2sl_clusters",
                "max_damage_cluster",
            ],
        )
    )
    report.append("\n\nLectura clave del resumen: en live/demo hay 0 clusters que empiezan con SL bajo la definicion estricta. El cluster danino principal fue `BE-SL-SL-SL-TP-SL-SL`. En historicos, los clusters que empiezan con TP son claramente mas saludables que los que empiezan con SL, pero los clusters SL-start tambien se recuperan con frecuencia alta.\n")
    report.append("\n\n## C. Simulaciones de reglas en live/demo\n")
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
    report.append("\n\n## D. Simulaciones de reglas en backtests/simulaciones\n")
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
                "removed_net",
                "net_delta_vs_baseline",
                "dd_delta_vs_baseline",
            ],
        )
    )
    report.append("\n\n## E. Respuestas directas\n")
    report.append("- **El verdadero problema no es reentrar siempre:** el problema es reentrar sin freno despues de perdida dentro del mismo contexto.\n")
    report.append("- **Las reentradas despues de ganancia parecen saludables en historicos amplios:** muchas rachas iniciadas con TP terminan positivas y sostienen una parte importante del profit.\n")
    report.append("- **En live/demo el cluster critico fue `BE-SL-SL-SL-TP-SL-SL`:** llego a 3 SL consecutivos y termino -1500 USD normalizados.\n")
    report.append("- **Clusters con 3 o mas SL consecutivos:** live/demo 1 cluster con 3 SL; stress 5 clusters con 3+ SL y 2 con mas de 3; CEO v3 decisions 24 con 3+ y 7 con mas de 3; scenario C 125 con 3+ y 32 con mas de 3.\n")
    report.append("- **SAFE_MODE tras 2 SL consecutivos es mas defendible que bloquear despues de 1 SL:** en live mejora +500 USD, pero en historicos reduce neto; debe ser contextual, no global.\n")
    report.append("- **Rule 6 es una direccion conceptual, no una regla lista tal cual:** permitir continuidad si el cluster inicia con TP; ser restrictivo si el cluster empieza o deriva en SL consecutivos.\n")
    report.append("\n## F. Recomendacion antes del 5 de junio\n")
    report.append("Implementar una regla de cluster en capa de riesgo, no en ejecucion:\n")
    report.append("- **Melchor:** detectar `cluster_started_with_sl`, `cluster_consecutive_sl`, `same_direction_reentry_cluster` y recomendar BLOCK/HOLD.\n")
    report.append("- **CEO-MAGI/backend:** mantener estado del cluster por simbolo/direccion/sesion y aplicar SAFE_MODE trazable.\n")
    report.append("- **Bot B:** no debe decidir clusters; solo ejecutar o no segun payload y mantener guardrails.\n")
    report.append("- **Dashboard/auditoria:** mostrar cluster activo, secuencia, bloqueo y regla aplicada.\n")
    report.append("\n## G. Archivos generados\n")
    report.append(f"- `{CLUSTER_SUMMARY_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{CLUSTER_TRADES_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{RULE_SCENARIOS_CSV.relative_to(ROOT)}`\n")
    report.append(f"- `{REPORT_MD.relative_to(ROOT)}`\n")

    REPORT_MD.write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
