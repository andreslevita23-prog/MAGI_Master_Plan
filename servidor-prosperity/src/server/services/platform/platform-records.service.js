import fs from "fs";
import path from "path";
import { paths } from "../../config/paths.js";
import { getBotCAuditSnapshot } from "../audit/bot-c-audit.service.js";
import { getCurrentPositionSnapshot } from "../positions/current-position.service.js";
import { getSnapshotDetail, listRecentSnapshots } from "../snapshots/snapshot-query.service.js";
import { listDirectories, readJsonLines } from "../storage.js";

function normalizeLimit(value, fallback = 100) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  return Math.max(1, Math.min(500, Math.floor(parsed)));
}

function timestampOf(item) {
  return item.timestamp_utc || item.timestamp || item.decision_time || item.recorded_at || item.stored_at || null;
}

function sortRecent(items) {
  return items.sort((left, right) => String(timestampOf(right) || "").localeCompare(String(timestampOf(left) || "")));
}

function rangeStart(range = "day") {
  const now = new Date();
  const start = new Date(now);
  if (range === "week") {
    start.setUTCDate(start.getUTCDate() - 7);
  } else if (range === "month") {
    start.setUTCMonth(start.getUTCMonth() - 1);
  } else {
    start.setUTCHours(0, 0, 0, 0);
  }
  return start;
}

function filterByRange(items, range) {
  const start = rangeStart(range);
  return items.filter((item) => {
    const raw = timestampOf(item);
    if (!raw) {
      return false;
    }

    const date = new Date(raw);
    return !Number.isNaN(date.getTime()) && date >= start;
  });
}

function listDateFolders(root) {
  return listDirectories(root)
    .map((dirPath) => ({ dirPath, name: path.basename(dirPath) }))
    .filter((item) => /^\d{4}-\d{2}-\d{2}$/.test(item.name))
    .sort((left, right) => right.name.localeCompare(left.name));
}

function readRecentJsonlFromDateFolders({ root, fileName, limit }) {
  const records = [];
  for (const folder of listDateFolders(root)) {
    const filePath = path.join(folder.dirPath, fileName);
    if (!fs.existsSync(filePath)) {
      continue;
    }

    records.push(
      ...readJsonLines(filePath).map((item) => ({
        ...item,
        source_file: filePath,
        date_folder: folder.name,
      })),
    );

    if (records.length >= limit * 2) {
      break;
    }
  }

  return sortRecent(records).slice(0, limit);
}

function readAllJsonlFromDateFolders({ root, fileName }) {
  return sortRecent(
    listDateFolders(root).flatMap((folder) => {
      const filePath = path.join(folder.dirPath, fileName);
      if (!fs.existsSync(filePath)) {
        return [];
      }

      return readJsonLines(filePath).map((item) => ({
        ...item,
        source_file: filePath,
        date_folder: folder.name,
      }));
    }),
  );
}

function readRecentDecisionAudit(limit) {
  const records = [];
  for (const folder of listDateFolders(paths.auditDecisions)) {
    const filePath = path.join(folder.dirPath, "magi_decisions.jsonl");
    if (!fs.existsSync(filePath)) {
      continue;
    }

    records.push(
      ...readJsonLines(filePath).map((item) => ({
        ...item,
        source_file: filePath,
        date_folder: folder.name,
      })),
    );

    if (records.length >= limit * 2) {
      break;
    }
  }

  return sortRecent(records).slice(0, limit);
}

function readAllDecisionAudit() {
  return sortRecent(
    listDateFolders(paths.auditDecisions).flatMap((folder) => {
      const filePath = path.join(folder.dirPath, "magi_decisions.jsonl");
      if (!fs.existsSync(filePath)) {
        return [];
      }

      return readJsonLines(filePath).map((item) => ({
        ...item,
        source_file: filePath,
        date_folder: folder.name,
      }));
    }),
  );
}

function normalizeBotALog(event = {}) {
  return {
    timestamp: event.timestamp_utc || event.timestamp || null,
    symbol: event.symbol || event.pair || event.details?.symbol || null,
    snapshot_id: event.snapshot_id || event.id_operacion || null,
    status: event.validation?.is_valid === false ? "warning" : "valid",
    source_mode: event.source_mode || event.source?.source_mode || null,
    validation_status: event.validation?.is_valid === false ? "invalid" : "valid",
    issues: event.validation?.issues || [],
    warnings: event.validation?.adapter_warnings || [],
    current_price: event.current_price || event.price || event.anchor_close || null,
    anchor_timeframe: event.anchor_timeframe || null,
    primary_timeframe: event.primary_timeframe || null,
    trigger_type: event.trigger_type || null,
  };
}

function normalizeDecisionRecord(record = {}) {
  return {
    timestamp: record.decision_time || record.recorded_at || null,
    decision_id: record.decision_id || null,
    snapshot_id: record.snapshot_id || null,
    symbol: record.symbol || null,
    final_action: record.final_action || null,
    reason: record.reason || null,
    votes: {
      melchor: record.melchor_vote || null,
      baltasar: record.baltasar_vote || null,
      gaspar: record.gaspar_vote || null,
    },
    payload_bot_b: record.execution_payload || null,
    confidence: record.confidence ?? record.score ?? null,
    status: record.status || null,
  };
}

export function listBotAEvents({ limit = 100 } = {}) {
  return listRecentSnapshots(normalizeLimit(limit)).map((summary) => {
    const detail = getSnapshotDetail(summary.snapshot_id);
    const normalized = detail?.normalized || {};
    const raw = normalized.raw || detail?.legacy?.payload || {};
    const validation = normalized.validation || raw.validation || {};

    return {
      timestamp: summary.received_at || summary.timestamp || normalized.timestamp || raw.timestamp || null,
      symbol: summary.symbol,
      snapshot_id: summary.snapshot_id,
      status: summary.is_valid ? "valid" : "warning",
      source_mode: normalized.source?.source_mode || raw.source_mode || null,
      validation_status: validation.is_valid === false ? "invalid" : summary.is_valid ? "valid" : "warning",
      issues: validation.issues || summary.issues || [],
      warnings: validation.adapter_warnings || [],
      current_price: summary.price || normalized.market?.price || raw.current_price || null,
      anchor_timeframe: normalized.timeframes?.anchor || raw.anchor_timeframe || null,
      primary_timeframe: normalized.timeframes?.primary || raw.primary_timeframe || null,
      trigger_type: raw.trigger_type || null,
    };
  });
}

export function listMagiDecisions({ limit = 100 } = {}) {
  return readRecentDecisionAudit(normalizeLimit(limit)).map(normalizeDecisionRecord);
}

export function listBotBEvents({ limit = 100 } = {}) {
  return readRecentJsonlFromDateFolders({
    root: paths.logs,
    fileName: "botB.jsonl",
    limit: normalizeLimit(limit),
  }).map((event) => ({
    timestamp: event.timestamp_utc || event.timestamp || event.decision_time || null,
    symbol: event.details?.symbol || event.symbol || null,
    action: event.action || null,
    decision_id: event.decision_id || event.id_operacion || null,
    snapshot_id: event.snapshot_id || null,
    status: event.error || event.rejected ? "error" : "sent",
    comment: event.details?.comment || null,
    reason: event.details?.reason || null,
    errors: event.error ? [event.error] : [],
    dedupe: event.dedupe || null,
    payload: event,
  }));
}

export function listBotCEvents({ limit = 100 } = {}) {
  return getBotCAuditSnapshot({ limit: normalizeLimit(limit) });
}

function buildEquitySeries(botCEvents) {
  const closedEvents = [...botCEvents]
    .filter((event) => String(event.event_type || "").toLowerCase() === "close" && Number.isFinite(Number(event.profit)))
    .sort((left, right) => String(left.timestamp || "").localeCompare(String(right.timestamp || "")));
  let cumulative = 0;

  return closedEvents.map((event) => {
    cumulative += Number(event.profit);
    return {
      timestamp: event.timestamp,
      value: Number(cumulative.toFixed(2)),
    };
  });
}

function buildDrawdownSeries(equitySeries) {
  let peak = 0;
  return equitySeries.map((point) => {
    peak = Math.max(peak, point.value);
    return {
      timestamp: point.timestamp,
      value: Number(Math.max(0, peak - point.value).toFixed(2)),
    };
  });
}

function countByBucket(items, range) {
  const buckets = new Map();
  for (const item of items) {
    const raw = timestampOf(item);
    const date = new Date(raw);
    if (!raw || Number.isNaN(date.getTime())) {
      continue;
    }

    const key = range === "day"
      ? `${String(date.getUTCHours()).padStart(2, "0")}:00`
      : date.toISOString().slice(0, 10);
    buckets.set(key, (buckets.get(key) || 0) + 1);
  }

  return Array.from(buckets.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([label, count]) => ({ label, value: count }));
}

function countDecisionsByAction(decisions) {
  const counts = new Map();
  for (const decision of decisions) {
    const action = String(decision.final_action || "unknown").toUpperCase();
    counts.set(action, (counts.get(action) || 0) + 1);
  }

  return Array.from(counts.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([label, count]) => ({ label, value: count }));
}

function classifyClosedTrades(botCEvents, botCAvailable) {
  if (!botCAvailable) {
    return {
      available: false,
      closed_operations: null,
      winners: null,
      losers: null,
      breakeven: null,
      unknown_profit: null,
      daily_pnl: null,
      profit_factor: null,
      win_rate: null,
    };
  }

  const closedEvents = botCEvents.filter((event) => String(event.event_type || "").toLowerCase() === "close");
  let winners = 0;
  let losers = 0;
  let breakeven = 0;
  let unknownProfit = 0;
  let grossProfit = 0;
  let grossLoss = 0;
  let dailyPnl = 0;

  for (const event of closedEvents) {
    const profit = Number(event.profit);
    if (!Number.isFinite(profit)) {
      unknownProfit += 1;
      continue;
    }

    dailyPnl += profit;
    if (profit > 0) {
      winners += 1;
      grossProfit += profit;
    } else if (profit < 0) {
      losers += 1;
      grossLoss += Math.abs(profit);
    } else {
      breakeven += 1;
    }
  }

  const knownTrades = winners + losers + breakeven;

  return {
    available: true,
    closed_operations: closedEvents.length,
    winners,
    losers,
    breakeven,
    unknown_profit: unknownProfit,
    daily_pnl: knownTrades ? Number(dailyPnl.toFixed(2)) : null,
    profit_factor: grossLoss > 0 ? Number((grossProfit / grossLoss).toFixed(2)) : null,
    win_rate: knownTrades > 0 ? Number(((winners / knownTrades) * 100).toFixed(2)) : null,
  };
}

function metricCount(totalCount, returnedCount, limit, source, available = true) {
  return {
    value: available ? totalCount : null,
    total_count: available ? totalCount : null,
    returned_count: returnedCount,
    limit,
    source,
    available,
  };
}

function secondsSince(rawTimestamp) {
  if (!rawTimestamp) {
    return null;
  }

  const timestamp = new Date(rawTimestamp);
  if (Number.isNaN(timestamp.getTime())) {
    return null;
  }

  return Math.max(0, Math.floor((Date.now() - timestamp.getTime()) / 1000));
}

function readBotCEventsForRange(range, limit) {
  const probe = listBotCEvents({ limit: 1 });
  if (probe.status === "no_disponible") {
    return {
      available: false,
      status: probe.status,
      reason: probe.reason,
      events: [],
    };
  }

  const start = rangeStart(range);
  const startDay = new Date(start);
  startDay.setUTCHours(0, 0, 0, 0);
  const root = probe.audit_root;
  const folders = listDateFolders(root).filter((folder) => {
    const date = new Date(`${folder.name}T00:00:00.000Z`);
    return !Number.isNaN(date.getTime()) && date >= startDay;
  });
  const snapshots = folders.map((folder) => getBotCAuditSnapshot({ date: folder.name, limit }));
  const events = filterByRange(
    snapshots.flatMap((snapshot) => snapshot.events || []),
    range,
  );
  const available = snapshots.some((snapshot) => snapshot.status === "disponible");

  return {
    available,
    status: available ? "disponible" : probe.status,
    reason: available ? null : "Bot C no tiene archivos de auditoria disponibles para el rango solicitado.",
    events: sortRecent(events),
  };
}

export function buildPlatformSummary({ range = "day", startedAt = null, uptimeSeconds = null } = {}) {
  const limit = 100;
  const botAAll = filterByRange(readAllJsonlFromDateFolders({ root: paths.logs, fileName: "botA.jsonl" }).map(normalizeBotALog), range);
  const magiAll = filterByRange(readAllDecisionAudit().map(normalizeDecisionRecord), range);
  const botBAll = filterByRange(listBotBEvents({ limit: 500 }), range);
  const botA = botAAll.slice(0, limit);
  const magi = magiAll.slice(0, limit);
  const botB = botBAll.slice(0, limit);
  const botC = readBotCEventsForRange(range, 500);
  const botCEvents = botC.events;
  const currentPosition = getCurrentPositionSnapshot();
  const botCAvailable = botC.available;
  const tradeStats = classifyClosedTrades(botCEvents, botCAvailable);
  const equitySeries = buildEquitySeries(botCEvents);
  const drawdownSeries = buildDrawdownSeries(equitySeries);
  const openOperations = currentPosition.status === "open" ? 1 : currentPosition.status === "closed" ? 0 : null;
  const latestSnapshot = listRecentSnapshots(1)[0] || null;
  const latestSnapshotTimestamp = latestSnapshot?.received_at || latestSnapshot?.stored_at || latestSnapshot?.timestamp || null;
  const generatedAt = new Date().toISOString();

  return {
    generated_at: generatedAt,
    range,
    backend: {
      started_at: startedAt instanceof Date ? startedAt.toISOString() : startedAt,
      uptime_seconds: Number.isFinite(Number(uptimeSeconds)) ? Number(uptimeSeconds) : null,
    },
    current_position: currentPosition,
    data_quality: {
      bot_a: botAAll.length ? "disponible" : "no_disponible",
      magi_decisions: magiAll.length ? "disponible" : "no_disponible",
      bot_b: botBAll.length ? "disponible" : "no_disponible",
      bot_c: botCAvailable ? "disponible" : "no_disponible",
      last_update: generatedAt,
      latest_snapshot_id: latestSnapshot?.snapshot_id || null,
      latest_snapshot_timestamp: latestSnapshotTimestamp,
      latest_snapshot_age_seconds: secondsSince(latestSnapshotTimestamp),
      incomplete_metrics: !tradeStats.available,
      incomplete_metrics_reason: tradeStats.available ? null : "Falta Bot C o una fuente con profit real para confirmar cierres, win/loss, PnL, profit factor y win rate.",
    },
    counts: {
      bot_a: metricCount(botAAll.length, botA.length, limit, "data/logs/*/botA.jsonl"),
      magi: metricCount(magiAll.length, magi.length, limit, "data/audit/decisions/*/magi_decisions.jsonl"),
      bot_b: metricCount(botBAll.length, botB.length, limit, "data/logs/*/botB.jsonl"),
      bot_c: metricCount(botCEvents.length, Math.min(botCEvents.length, limit), limit, "MAGI_BOT_C_AUDIT_DIR", botCAvailable),
    },
    metrics: {
      signals_received: botAAll.length,
      decisions_generated: magiAll.length,
      open_operations: openOperations,
      closed_operations: tradeStats.closed_operations,
      winners: tradeStats.winners,
      losers: tradeStats.losers,
      breakeven: tradeStats.breakeven,
      unknown_profit: tradeStats.unknown_profit,
      daily_pnl: tradeStats.daily_pnl,
      daily_drawdown: drawdownSeries.length ? drawdownSeries.at(-1).value : null,
      profit_factor: tradeStats.profit_factor,
      win_rate: tradeStats.win_rate,
    },
    connections: {
      bot_a: botA.length ? "recibiendo" : "sin_datos",
      magi: magi.length ? "operativo" : "sin_datos",
      bot_b: botB.length ? "connected" : "sin_datos",
      bot_c: botC.status === "disponible" ? "connected" : "sin_datos",
    },
    charts: {
      pnl_curve: equitySeries,
      drawdown_curve: drawdownSeries,
      signals_by_bucket: countByBucket(botAAll, range),
      decisions_by_action: countDecisionsByAction(magiAll),
      win_loss: {
        available: tradeStats.available,
        winners: tradeStats.winners,
        losers: tradeStats.losers,
        breakeven: tradeStats.breakeven,
        unknown_profit: tradeStats.unknown_profit,
      },
    },
    recent: {
      bot_a: botA.slice(0, 5),
      magi: magi.slice(0, 5),
      bot_b: botB.slice(0, 5),
      bot_c: botCEvents.slice(0, 5),
    },
    warnings: [
      ...(botC.status === "disponible" ? [] : [`Bot C: ${botC.reason || botC.status}`]),
      ...(tradeStats.available ? [] : ["Metricas de operaciones cerradas, win/loss, PnL, profit factor y win rate no disponibles sin Bot C o fuente con profit real."]),
      ...(currentPosition.warnings || []),
    ],
  };
}
