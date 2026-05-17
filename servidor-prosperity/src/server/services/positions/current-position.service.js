import { getBotCAuditSnapshot } from "../audit/bot-c-audit.service.js";
import { listExecutionStates } from "../execution/execution-query.service.js";
import { getSnapshotDetail, listRecentSnapshots } from "../snapshots/snapshot-query.service.js";

const EMPTY_POSITION = {
  status: "not_available",
  source: null,
  confidence: "low",
  symbol: null,
  ticket: null,
  side: null,
  entry_price: null,
  sl: null,
  tp: null,
  lot_size: null,
  floating_profit: null,
  open_time: null,
  duration_seconds: null,
  decision_id: null,
  snapshot_id: null,
  comment: null,
  protection_state: null,
  warnings: [],
};

function isPresent(value) {
  return value !== null && value !== undefined && value !== "";
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function secondsSince(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
}

function inferProtectionState({ entryPrice, sl, side }) {
  if (!isPresent(entryPrice) || !isPresent(sl) || !side) {
    return null;
  }

  const normalizedSide = String(side).toLowerCase();
  const entry = numberOrNull(entryPrice);
  const stop = numberOrNull(sl);
  if (!Number.isFinite(entry) || !Number.isFinite(stop)) {
    return null;
  }

  const tolerance = Math.max(Math.abs(entry) * 0.00001, 0.0000001);
  if (Math.abs(entry - stop) <= tolerance) {
    return "breakeven";
  }

  if ((normalizedSide.includes("buy") && stop > entry) || (normalizedSide.includes("sell") && stop < entry)) {
    return "trailing";
  }

  return "normal";
}

function findLatestSnapshotDetail() {
  const summaries = listRecentSnapshots(10);
  for (const summary of summaries) {
    const detail = getSnapshotDetail(summary.snapshot_id);
    if (detail?.normalized?.position) {
      return { summary, detail };
    }
  }

  return summaries[0] ? { summary: summaries[0], detail: getSnapshotDetail(summaries[0].snapshot_id) } : null;
}

function buildFromBotC(botC) {
  const warnings = [];
  if (botC.status !== "disponible" || !botC.events.length) {
    return null;
  }

  const latestEvent = botC.events[0];
  const eventType = String(latestEvent.event_type || "").toLowerCase();
  const isOpenEvent = ["open", "floating_snapshot"].includes(eventType);
  const isClosedEvent = ["close"].includes(eventType);

  if (!isOpenEvent && !isClosedEvent) {
    return null;
  }

  if (latestEvent.missing_decision_id) {
    warnings.push("Bot C reporto el evento mas reciente sin decision_id.");
  }
  if (latestEvent.anomaly) {
    warnings.push(`Bot C reporto anomalia: ${latestEvent.anomaly}`);
  }

  const matchingOpen = botC.events.find((event) => {
    if (String(event.event_type || "").toLowerCase() !== "open") {
      return false;
    }

    if (latestEvent.ticket && event.ticket) {
      return String(event.ticket) === String(latestEvent.ticket);
    }

    if (latestEvent.decision_id && event.decision_id) {
      return latestEvent.decision_id === event.decision_id;
    }

    return event.symbol && event.symbol === latestEvent.symbol;
  });
  const openTime = isOpenEvent ? matchingOpen?.timestamp || (eventType === "open" ? latestEvent.timestamp : null) : null;

  return {
    ...EMPTY_POSITION,
    status: isClosedEvent ? "closed" : "open",
    source: `bot_c:${eventType}`,
    confidence: "high",
    symbol: latestEvent.symbol || null,
    ticket: latestEvent.ticket || null,
    entry_price: eventType === "open" ? numberOrNull(latestEvent.price) : numberOrNull(matchingOpen?.price),
    sl: numberOrNull(latestEvent.sl),
    tp: numberOrNull(latestEvent.tp),
    lot_size: numberOrNull(latestEvent.volume),
    floating_profit: isOpenEvent ? numberOrNull(latestEvent.floating_profit) : null,
    open_time: openTime,
    duration_seconds: secondsSince(openTime),
    decision_id: latestEvent.decision_id || null,
    snapshot_id: latestEvent.snapshot_id || null,
    comment: latestEvent.comment || null,
    protection_state: inferProtectionState({
      entryPrice: eventType === "open" ? latestEvent.price : matchingOpen?.price,
      sl: latestEvent.sl,
      side: null,
    }),
    warnings,
  };
}

function buildFromSnapshot(snapshotInfo) {
  const position = snapshotInfo?.detail?.normalized?.position || null;
  const summary = snapshotInfo?.summary || null;
  if (!position && !summary) {
    return null;
  }

  const hasOpenPosition = Boolean(position?.has_open_position || summary?.has_open_position);
  const warnings = [];
  if (!position) {
    warnings.push("El snapshot mas reciente no contiene bloque position normalizado.");
  }

  const positionSummary = position?.summary || {};
  const side = position?.position_type || positionSummary.position_type || null;
  const entryPrice = position?.entry_price || positionSummary.entry_price || null;
  const sl = position?.sl || positionSummary.sl || null;
  const tp = position?.tp || positionSummary.tp || null;

  return {
    ...EMPTY_POSITION,
    status: hasOpenPosition ? "open" : "closed",
    source: "snapshot:normalized_position",
    confidence: hasOpenPosition ? "medium" : "medium",
    symbol: summary?.symbol || snapshotInfo?.detail?.normalized?.symbol || null,
    side,
    entry_price: numberOrNull(entryPrice),
    sl: numberOrNull(sl),
    tp: numberOrNull(tp),
    floating_profit: numberOrNull(position?.floating_pnl ?? positionSummary.floating_pnl),
    snapshot_id: summary?.snapshot_id || snapshotInfo?.detail?.snapshot_id || null,
    protection_state: inferProtectionState({ entryPrice, sl, side }),
    warnings,
  };
}

function buildFromExecution(execution) {
  if (!execution) {
    return null;
  }

  const response = execution.bot_b_response || {};
  const details = response.details || {};
  const action = String(response.action || execution.final_action || "").toLowerCase();
  const warnings = [
    "Fuente de baja confianza: el payload de Bot B expresa intencion o ultima respuesta, no confirmacion de mercado.",
  ];

  return {
    ...EMPTY_POSITION,
    status: action === "open" ? "unknown" : "unknown",
    source: "execution:bot_b_payload",
    confidence: "low",
    symbol: execution.symbol || details.symbol || null,
    side: details.order_type || null,
    entry_price: numberOrNull(details.entry_price),
    sl: numberOrNull(details.stop_loss),
    tp: numberOrNull(details.take_profit),
    lot_size: numberOrNull(details.lot_size),
    decision_id: response.decision_id || execution.decision_id || null,
    snapshot_id: response.snapshot_id || execution.snapshot_id || null,
    comment: details.comment || null,
    protection_state: null,
    warnings,
  };
}

export function getCurrentPositionSnapshot() {
  const warnings = [];
  const botC = getBotCAuditSnapshot({ limit: 200 });
  const botCPosition = buildFromBotC(botC);
  if (botCPosition) {
    return {
      ...botCPosition,
      warnings: [
        ...botCPosition.warnings,
        ...(botC.status === "disponible" ? [] : ["Bot C no esta disponible para validar posicion actual."]),
      ],
    };
  }

  if (botC.status !== "disponible") {
    warnings.push(`Bot C no disponible: ${botC.reason || botC.status}`);
  } else if (!botC.events.length) {
    warnings.push("Bot C disponible sin eventos para inferir posicion actual.");
  } else {
    warnings.push("Bot C disponible, pero el evento mas reciente no confirma apertura ni cierre.");
  }

  const snapshotInfo = findLatestSnapshotDetail();
  const snapshotPosition = buildFromSnapshot(snapshotInfo);
  if (snapshotPosition) {
    return {
      ...snapshotPosition,
      warnings: [...warnings, ...snapshotPosition.warnings],
    };
  }

  const latestExecution = listExecutionStates()[0] || null;
  const executionPosition = buildFromExecution(latestExecution);
  if (executionPosition) {
    return {
      ...executionPosition,
      warnings: [...warnings, ...executionPosition.warnings],
    };
  }

  return {
    ...EMPTY_POSITION,
    status: "not_available",
    source: "none",
    confidence: "low",
    warnings: [...warnings, "No hay execution state, snapshots ni eventos Bot C suficientes."],
  };
}
