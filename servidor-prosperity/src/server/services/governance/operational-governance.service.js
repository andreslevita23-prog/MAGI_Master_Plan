import fs from "node:fs";
import path from "node:path";
import { paths } from "../../config/paths.js";
import { listDirectories, readJsonLines, writeJsonWithTimestamp } from "../storage.js";

const BOT_C_EVENTS_FILE = "bot_c_events.jsonl";
const STATE_FILE = path.join(paths.system, "magi_operational_state.json");
const BOGOTA_OFFSET_MS = -5 * 60 * 60 * 1000;
const SESSION_ORDER = ["asia", "london", "overlap", "new_york"];

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeSymbol(value) {
  return String(value || "UNKNOWN").trim().toUpperCase();
}

function normalizeDirection(value) {
  const text = String(value || "").trim().toUpperCase();
  if (text === "BUY" || text === "SELL") {
    return text;
  }
  if (text === "buy" || text === "sell") {
    return text.toUpperCase();
  }
  return "";
}

function compactId(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 12);
}

function parseDate(value) {
  const date = new Date(value || "");
  return Number.isNaN(date.getTime()) ? null : date;
}

function colombiaDateKey(value) {
  const date = value instanceof Date ? value : parseDate(value);
  if (!date) {
    return "";
  }
  return new Date(date.getTime() + BOGOTA_OFFSET_MS).toISOString().slice(0, 10);
}

function colombiaHour(value) {
  const date = value instanceof Date ? value : parseDate(value);
  if (!date) {
    return 0;
  }
  const local = new Date(date.getTime() + BOGOTA_OFFSET_MS);
  return local.getUTCHours() + local.getUTCMinutes() / 60;
}

function isFriday(value) {
  const date = value instanceof Date ? value : parseDate(value);
  if (!date) {
    return false;
  }
  return new Date(date.getTime() + BOGOTA_OFFSET_MS).getUTCDay() === 5;
}

function sessionForHour(hour) {
  if (hour >= 2 && hour < 7) {
    return "london";
  }
  if (hour >= 7 && hour < 12) {
    return "overlap";
  }
  if (hour >= 12 && hour < 17) {
    return "new_york";
  }
  return "asia";
}

function sessionForTimestamp(value) {
  return sessionForHour(colombiaHour(value));
}

function normalizeSession(value, timestamp) {
  const text = String(value || "").trim().toLowerCase();
  if (SESSION_ORDER.includes(text)) {
    return text;
  }
  return sessionForTimestamp(timestamp);
}

function sameOrNextSession(previous, current) {
  if (previous === current) {
    return true;
  }
  const left = SESSION_ORDER.indexOf(previous);
  const right = SESSION_ORDER.indexOf(current);
  return left >= 0 && right >= 0 && right - left >= 0 && right - left <= 1;
}

function nextOperationalSession(timestamp) {
  const date = parseDate(timestamp) || new Date();
  const local = new Date(date.getTime() + BOGOTA_OFFSET_MS);
  const hour = local.getUTCHours() + local.getUTCMinutes() / 60;
  const base = new Date(Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate(), 0, 0, 0));

  let targetHour = 2;
  let addDays = 0;
  if (hour < 2) {
    targetHour = 2;
  } else if (hour < 7) {
    targetHour = 7;
  } else if (hour < 12) {
    targetHour = 12;
  } else {
    targetHour = 2;
    addDays = local.getUTCDay() === 5 ? 3 : 1;
  }

  const targetLocal = new Date(base.getTime() + addDays * 24 * 60 * 60 * 1000 + targetHour * 60 * 60 * 1000);
  return new Date(targetLocal.getTime() - BOGOTA_OFFSET_MS).toISOString();
}

function resolveBotCAuditRoot() {
  const configuredRoot = process.env.MAGI_BOT_C_AUDIT_DIR?.trim();
  return path.resolve(configuredRoot || path.join(paths.audit, "bot_c"));
}

function readBotCEvents(limitDays = 45) {
  const root = resolveBotCAuditRoot();
  if (!fs.existsSync(root)) {
    return [];
  }

  return listDirectories(root)
    .sort()
    .slice(-limitDays)
    .flatMap((folder) => {
      const filePath = path.join(folder, BOT_C_EVENTS_FILE);
      return readJsonLines(filePath).map((event) => ({ ...event, __source_path: filePath }));
    })
    .sort((left, right) => String(left.timestamp || "").localeCompare(String(right.timestamp || "")));
}

function readDecisionRecords(limitDays = 60) {
  if (!fs.existsSync(paths.auditDecisions)) {
    return [];
  }

  return listDirectories(paths.auditDecisions)
    .sort()
    .slice(-limitDays)
    .flatMap((folder) => readJsonLines(path.join(folder, "magi_decisions.jsonl")));
}

function buildDecisionIndex() {
  const byId = new Map();
  const byShort = new Map();

  for (const record of readDecisionRecords()) {
    const decisionId = String(record.decision_id || "");
    if (!decisionId) {
      continue;
    }
    byId.set(decisionId, record);
    byShort.set(compactId(decisionId), record);
  }

  return { byId, byShort };
}

function inferCloseResult(event) {
  const comment = String(event.comment || "").toLowerCase();
  const profit = toNumber(event.profit, 0);
  if (comment.includes("[sl")) {
    return "SL";
  }
  if (comment.includes("[tp")) {
    return "TP";
  }
  if (Math.abs(profit) < 0.01) {
    return "BE";
  }
  return profit > 0 ? "TP" : "SL";
}

function isCloseEvent(event) {
  return String(event.event_type || event.type || event.event || "").toLowerCase() === "close";
}

function buildClosedTrades() {
  const decisionIndex = buildDecisionIndex();
  const ticketContext = new Map();
  const trades = [];

  for (const event of readBotCEvents()) {
    const ticket = String(event.ticket || "");
    const decisionId = String(event.decision_id || "");
    const decisionRecord = decisionIndex.byId.get(decisionId) || decisionIndex.byShort.get(compactId(decisionId));
    if (ticket && decisionRecord) {
      ticketContext.set(ticket, {
        symbol: normalizeSymbol(event.symbol || decisionRecord.symbol),
        direction: normalizeDirection(decisionRecord.order_type || decisionRecord.execution_payload?.details?.order_type),
        session: normalizeSession(decisionRecord.execution_payload?.market_session, decisionRecord.decision_time),
        decision_id: decisionRecord.decision_id,
      });
    }

    if (!isCloseEvent(event)) {
      continue;
    }

    const context = ticketContext.get(ticket) || {};
    const closeTime = parseDate(event.timestamp);
    if (!closeTime) {
      continue;
    }

    const direction = context.direction || normalizeDirection(decisionRecord?.order_type || decisionRecord?.execution_payload?.details?.order_type);
    trades.push({
      symbol: normalizeSymbol(event.symbol || context.symbol),
      direction,
      result: inferCloseResult(event),
      close_time: closeTime.toISOString(),
      close_date: colombiaDateKey(closeTime),
      session: normalizeSession(context.session, closeTime),
      ticket,
      decision_id: context.decision_id || decisionId || null,
      profit: toNumber(event.profit, 0),
    });
  }

  return trades.filter((trade) => trade.symbol && trade.direction);
}

function sameCluster(previous, current) {
  if (!previous) {
    return false;
  }
  if (previous.symbol !== current.symbol || previous.direction !== current.direction) {
    return false;
  }
  if (previous.close_date !== current.close_date) {
    return false;
  }
  const gapMinutes = (parseDate(current.close_time).getTime() - parseDate(previous.close_time).getTime()) / 60000;
  return gapMinutes >= 0 && gapMinutes <= 180 && sameOrNextSession(previous.session, current.session);
}

function computeStateFor(snapshot = {}) {
  const symbol = normalizeSymbol(snapshot.symbol);
  const timestamp = snapshot.timestamp || new Date().toISOString();
  const session = normalizeSession(snapshot.market?.session || snapshot.market?.active_session, timestamp);
  const day = colombiaDateKey(timestamp);
  const closedTrades = buildClosedTrades().filter((trade) => trade.symbol === symbol);
  const dailyTrades = closedTrades.filter((trade) => trade.close_date === day);
  const sessionTrades = dailyTrades.filter((trade) => trade.session === session);
  const lastTrade = closedTrades.at(-1) || null;
  let clusterSequence = [];
  let clusterConsecutiveSl = 0;
  let previous = null;

  for (const trade of closedTrades) {
    if (!sameCluster(previous, trade)) {
      clusterSequence = [];
      clusterConsecutiveSl = 0;
    }
    clusterSequence.push(trade.result);
    if (trade.result === "SL") {
      clusterConsecutiveSl += 1;
    } else if (trade.result === "TP") {
      clusterConsecutiveSl = 0;
    }
    previous = trade;
  }

  const lastClose = lastTrade ? parseDate(lastTrade.close_time) : null;
  const blockedUntil = clusterConsecutiveSl >= 3 && lastClose ? nextOperationalSession(lastClose) : null;
  const blockedUntilDate = blockedUntil ? parseDate(blockedUntil) : null;
  const now = parseDate(timestamp) || new Date();
  const safeModeActive = Boolean(
    blockedUntilDate
      && now < blockedUntilDate
      && lastTrade?.symbol === symbol,
  );
  const fridayRisk = isFriday(timestamp);
  const recentReentryDamage = clusterSequence.slice(-3).every((item) => item === "SL") ? "cluster_3sl" : "";

  return {
    symbol,
    session,
    operational_day: day,
    daily_sl_count: dailyTrades.filter((trade) => trade.result === "SL").length,
    daily_tp_count: dailyTrades.filter((trade) => trade.result === "TP").length,
    session_sl_count: sessionTrades.filter((trade) => trade.result === "SL").length,
    cluster_consecutive_sl: clusterConsecutiveSl,
    cluster_sequence: clusterSequence.slice(-8),
    same_direction_recent_sl: lastTrade?.result === "SL" ? {
      direction: lastTrade.direction,
      close_time: lastTrade.close_time,
      session: lastTrade.session,
    } : null,
    safe_mode_active: safeModeActive,
    safe_mode_reason: safeModeActive ? "safe_mode_cluster_3_consecutive_sl" : "",
    blocked_direction: safeModeActive ? lastTrade?.direction : "",
    blocked_until: safeModeActive ? blockedUntil : null,
    friday_risk: fridayRisk,
    recent_reentry_damage: recentReentryDamage,
    last_trade_result: lastTrade?.result || null,
    last_trade_direction: lastTrade?.direction || null,
    last_trade_close_time: lastTrade?.close_time || null,
    last_trade_session: lastTrade?.session || null,
    be_auto_status: "not_enabled_no_mfe_mae_dataset",
    news_guardrail_status: "not_enabled_no_calendar",
    evaluated_at: new Date().toISOString(),
  };
}

function buildShadowGuardrails(riskState = {}, snapshot = {}) {
  const spread = toNumber(snapshot.market?.spread_pips, 0);
  const isFridayLate = riskState.friday_risk && colombiaHour(snapshot.timestamp) >= 12;
  const fridayWouldBlock = Boolean(
    isFridayLate
      && (
        riskState.daily_sl_count >= 1
        || riskState.same_direction_recent_sl
        || spread > 1.5
        || riskState.recent_reentry_damage
      ),
  );
  const cluster2slWouldBlock = riskState.cluster_consecutive_sl >= 2;

  return {
    friday_guardrail_would_block: fridayWouldBlock,
    friday_reason: fridayWouldBlock ? "friday_after_12co_sl_recent_or_deteriorated_context" : "",
    cluster_2sl_would_block: cluster2slWouldBlock,
    cluster_2sl_reason: cluster2slWouldBlock ? "two_consecutive_sl_same_direction_context" : "",
  };
}

export function getDemoGovernanceConfig({ demoMode = false } = {}) {
  return {
    demo_mode: Boolean(demoMode),
    demo_mode_until: process.env.MAGI_DEMO_MODE_UNTIL || "2026-06-05",
    demo_lot_size: Number(process.env.MAGI_DEMO_LOT_SIZE || 1.0),
  };
}

export function applyDemoLotSizing(decision = {}, { demoMode = false } = {}) {
  const config = getDemoGovernanceConfig({ demoMode });
  if (!config.demo_mode || decision.final_action !== "open") {
    return {
      ...decision,
      demo_mode_until: config.demo_mode_until,
      current_lot_size: decision.lot_size || 0,
    };
  }

  return {
    ...decision,
    lot_size: config.demo_lot_size,
    current_lot_size: config.demo_lot_size,
    lot_size_source: "demo_guardrails_v1_fixed_lot",
    demo_mode_until: config.demo_mode_until,
  };
}

export function applyOperationalGovernance(snapshot = {}, decision = {}) {
  const riskState = computeStateFor(snapshot);
  const shadowGuardrails = buildShadowGuardrails(riskState, snapshot);
  const direction = normalizeDirection(decision.direction);
  const baseDecision = {
    ...decision,
    risk_state: riskState,
    cluster_state: {
      sequence: riskState.cluster_sequence,
      consecutive_sl: riskState.cluster_consecutive_sl,
      session: riskState.session,
      operational_day: riskState.operational_day,
    },
    shadow_guardrails: shadowGuardrails,
    be_auto_status: riskState.be_auto_status,
    news_guardrail_status: riskState.news_guardrail_status,
  };

  if (
    decision.final_action === "open"
    && riskState.safe_mode_active
    && direction
    && direction === riskState.blocked_direction
  ) {
    return {
      ...baseDecision,
      final_action: "hold",
      direction: null,
      entry_price: null,
      stop_loss: null,
      take_profit: null,
      lot_size: 0,
      reason: "safe_mode_cluster_3_consecutive_sl",
      ceo_magi_decision: {
        action: "hold_by_operational_governance",
        reason: "safe_mode_cluster_3_consecutive_sl",
      },
    };
  }

  return baseDecision;
}

export function persistOperationalState(snapshot = {}, decision = {}) {
  const state = {
    symbol: normalizeSymbol(snapshot.symbol || decision.symbol),
    risk_state: decision.risk_state || computeStateFor(snapshot),
    cluster_state: decision.cluster_state || null,
    shadow_guardrails: decision.shadow_guardrails || null,
    current_lot_size: decision.current_lot_size || decision.lot_size || 0,
    demo_mode_until: decision.demo_mode_until || process.env.MAGI_DEMO_MODE_UNTIL || "2026-06-05",
    last_decision_id: decision.decision_id || null,
    last_snapshot_id: decision.snapshot_id || snapshot.snapshot_id || null,
    last_action: decision.final_action || null,
  };
  writeJsonWithTimestamp(STATE_FILE, state);
  return state;
}

export function getOperationalState() {
  const snapshot = {};
  if (fs.existsSync(STATE_FILE)) {
    return JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
  }
  return {
    symbol: "UNKNOWN",
    risk_state: computeStateFor(snapshot),
    cluster_state: null,
    shadow_guardrails: null,
    current_lot_size: 0,
    demo_mode_until: process.env.MAGI_DEMO_MODE_UNTIL || "2026-06-05",
  };
}
