import fs from "fs";
import path from "path";
import { paths } from "../../config/paths.js";
import { readJson, readJsonLines } from "../storage.js";

const BOT_C_EVENTS_FILE = "bot_c_events.jsonl";
const BOT_C_SUMMARY_FILE = "bot_c_daily_summary.json";
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function todayUtcSegment() {
  return new Date().toISOString().slice(0, 10);
}

function normalizeLimit(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 100;
  }

  return Math.max(1, Math.min(500, Math.floor(parsed)));
}

function resolveAuditRoot() {
  const configuredRoot = process.env.MAGI_BOT_C_AUDIT_DIR?.trim();
  const defaultRoot = path.join(paths.audit, "bot_c");
  const root = configuredRoot || defaultRoot;

  return {
    root: path.resolve(root),
    source: configuredRoot ? "env" : "default_workspace",
    configured: Boolean(configuredRoot),
  };
}

function normalizeBotCEvent(event = {}, sourcePath) {
  const decisionId = event.decision_id || "";
  const anomaly = event.anomaly || event.anomaly_type || event.error || "";

  return {
    source: "bot_c",
    source_path: sourcePath,
    schema_version: event.schema_version || null,
    event_type: event.event_type || event.type || event.event || null,
    timestamp: event.timestamp || event.timestamp_utc || event.time || null,
    ticket: event.ticket ?? event.position_ticket ?? event.position_id ?? null,
    deal: event.deal ?? null,
    order: event.order ?? null,
    symbol: event.symbol || null,
    magic_number: event.magic_number ?? event.magic ?? null,
    comment: event.comment || "",
    decision_id: decisionId || null,
    snapshot_id: event.snapshot_id || null,
    price: event.price ?? null,
    volume: event.volume ?? null,
    sl: event.sl ?? null,
    tp: event.tp ?? null,
    profit: event.profit_final ?? event.profit ?? null,
    floating_profit: event.floating_profit ?? null,
    retcode: event.retcode ?? null,
    anomaly,
    missing_decision_id: !decisionId,
    severity: !decisionId || anomaly ? "warning" : "normal",
    raw: event,
  };
}

function buildUnavailableResponse({ date, reason, rootInfo }) {
  return {
    status: "no_disponible",
    reason,
    date,
    configured: rootInfo.configured,
    source: rootInfo.source,
    audit_root: rootInfo.root,
    expected_files: {
      events: path.join(rootInfo.root, date, BOT_C_EVENTS_FILE),
      daily_summary: path.join(rootInfo.root, date, BOT_C_SUMMARY_FILE),
    },
    files: {
      root_exists: fs.existsSync(rootInfo.root),
      date_dir_exists: false,
      events_exists: false,
      daily_summary_exists: false,
    },
    events: [],
    daily_summary: null,
    total_events: 0,
    missing_decision_id: 0,
    events_without_decision_id: [],
  };
}

export function getBotCAuditSnapshot({ date = todayUtcSegment(), limit = 100 } = {}) {
  if (!DATE_PATTERN.test(date)) {
    const error = new Error("Fecha invalida. Use YYYY-MM-DD.");
    error.statusCode = 400;
    throw error;
  }

  const rootInfo = resolveAuditRoot();
  const normalizedLimit = normalizeLimit(limit);

  if (!fs.existsSync(rootInfo.root)) {
    return buildUnavailableResponse({
      date,
      reason: rootInfo.configured
        ? "La ruta configurada en MAGI_BOT_C_AUDIT_DIR no existe o no es accesible."
        : "MAGI_BOT_C_AUDIT_DIR no esta configurada y la ruta local por defecto no existe.",
      rootInfo,
    });
  }

  const dateDir = path.join(rootInfo.root, date);
  const eventsPath = path.join(dateDir, BOT_C_EVENTS_FILE);
  const summaryPath = path.join(dateDir, BOT_C_SUMMARY_FILE);
  const dateDirExists = fs.existsSync(dateDir);
  const eventsExists = fs.existsSync(eventsPath);
  const summaryExists = fs.existsSync(summaryPath);
  const events = eventsExists
    ? readJsonLines(eventsPath)
        .slice(-normalizedLimit)
        .map((event) => normalizeBotCEvent(event, eventsPath))
        .sort((left, right) => String(right.timestamp || "").localeCompare(String(left.timestamp || "")))
    : [];
  const dailySummary = summaryExists ? readJson(summaryPath) : null;
  const eventsWithoutDecisionId = events.filter((event) => event.missing_decision_id);

  return {
    status: eventsExists || summaryExists ? "disponible" : "sin_archivos",
    reason: eventsExists || summaryExists ? null : "La ruta existe, pero no hay archivos Bot C para la fecha solicitada.",
    date,
    configured: rootInfo.configured,
    source: rootInfo.source,
    audit_root: rootInfo.root,
    expected_files: {
      events: eventsPath,
      daily_summary: summaryPath,
    },
    files: {
      root_exists: true,
      date_dir_exists: dateDirExists,
      events_exists: eventsExists,
      daily_summary_exists: summaryExists,
    },
    events,
    daily_summary: dailySummary,
    total_events: events.length,
    missing_decision_id: eventsWithoutDecisionId.length,
    events_without_decision_id: eventsWithoutDecisionId,
  };
}
