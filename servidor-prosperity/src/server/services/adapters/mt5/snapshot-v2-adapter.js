import { createEmptyNormalizedSnapshot } from "../../../domain/contracts/snapshot-normalized.js";

export const snapshotV2Contract = {
  name: "magi.snapshot.v2",
  description: "Contrato tecnico emitido por Bot A actual, alineado con Bot_A_sub3.",
  criticalFields: ["symbol", "current_price", "timestamp"],
};

const V2_SCHEMA_PREFIX = "magi.snapshot.v2";

function normalizeSymbol(value) {
  return String(value || "").trim().toUpperCase();
}

function normalizeTimestamp(value) {
  const candidate = String(value || "").trim();

  if (!candidate) {
    return null;
  }

  const normalizedCandidate = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(candidate)
    ? candidate
    : `${candidate}Z`;
  const parsed = new Date(normalizedCandidate);

  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function normalizeNumber(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeArray(value) {
  return Array.isArray(value) ? value : [];
}

function normalizeAllowedActions(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }

  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return normalizeAllowedActions(parsed);
      }
    } catch {
      return value
        .split(",")
        .map((item) => item.replace(/[[\]"]/g, "").trim())
        .filter(Boolean);
    }
  }

  return [];
}

function objectOrEmpty(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function buildSnapshotId(payload, symbol, timestamp) {
  return String(payload.snapshot_id || "").trim() || `${symbol}_${timestamp}`;
}

function deriveMarketContext(allowedActions, position) {
  if (position.has_open_position || position.open_positions_count > 0) {
    return "position_management";
  }

  if (allowedActions.includes("open")) {
    return "waiting_for_entry";
  }

  return "market_snapshot";
}

function normalizeStructureForLegacyFeature(feature = {}) {
  const structure = String(feature.market_structure || "").trim().toLowerCase();
  const direction = String(feature.structure_direction || "").trim().toLowerCase();

  if (structure === "trend" && direction === "bullish") {
    return "uptrend";
  }

  if (structure === "trend" && direction === "bearish") {
    return "downtrend";
  }

  if (direction === "bullish") {
    return "uptrend";
  }

  if (direction === "bearish") {
    return "downtrend";
  }

  return structure || "range";
}

function buildRawIndicators(payload) {
  const indicators = {};

  for (const feature of normalizeArray(payload.features)) {
    const timeframe = String(feature?.timeframe || "").trim().toUpperCase();
    if (!timeframe) {
      continue;
    }

    indicators[`candle_pattern_${timeframe}`] = feature.candle_pattern || "none";
    indicators[`market_structure_${timeframe}`] = normalizeStructureForLegacyFeature(feature);
    indicators[`structure_direction_${timeframe}`] = feature.structure_direction || "neutral";
    indicators[`ema20_${timeframe}`] = normalizeNumber(feature.ema_20);
    indicators[`ema50_${timeframe}`] = normalizeNumber(feature.ema_50);
    indicators[`ema200_${timeframe}`] = normalizeNumber(feature.ema_200);
    indicators[`rsi14_${timeframe}`] = normalizeNumber(feature.rsi_14);
    indicators[`recent_range_${timeframe}`] = normalizeNumber(feature.recent_range);
  }

  return indicators;
}

function collectWarnings(payload, normalized) {
  const issues = [];

  const nonCriticalFields = [
    "anchor_bar_timestamp",
    "bar_timestamp",
    "anchor_timeframe",
    "primary_timeframe",
    "anchor_open",
    "anchor_high",
    "anchor_low",
    "anchor_close",
    "market_structure",
    "structure_direction",
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "momentum",
    "recent_range",
    "spread_pips",
    "active_session",
    "allowed_actions",
    "account",
    "position",
    "gaspar_context",
    "features",
    "validation",
  ];

  for (const field of nonCriticalFields) {
    const value = payload[field];
    if (value === undefined || value === null || value === "") {
      issues.push(`Advertencia v2: falta campo no critico "${field}".`);
    }
  }

  if (normalized.account.daily_drawdown_percent === 0) {
    issues.push(
      "Advertencia operativa: daily_drawdown_percent llega en 0.0; se conserva como placeholder pendiente.",
    );
  }

  if (normalized.account.risk_percent_per_trade === 0) {
    issues.push(
      "Advertencia operativa: risk_percent_per_trade llega en 0.0; se conserva como placeholder pendiente.",
    );
  }

  if (normalized.news.length === 0) {
    issues.push("Advertencia operativa: news_context no disponible; campo news llega vacio.");
  }

  const position = normalized.position;
  if (position.open_positions_count > 1) {
    issues.push(
      "Advertencia operativa: multiples posiciones abiertas; SL/TP pueden no representar cada posicion individual.",
    );
  }

  return issues;
}

export function isSnapshotV2Payload(payload = {}) {
  return String(payload?.schema_version || "").startsWith(V2_SCHEMA_PREFIX);
}

export function validateSnapshotV2Payload(payload = {}) {
  const issues = [];
  const symbol = normalizeSymbol(payload.symbol);
  const currentPrice = normalizeNumber(payload.current_price);
  const timestamp = normalizeTimestamp(payload.timestamp);

  if (!symbol) {
    issues.push('Falta el campo critico "symbol".');
  }

  if (currentPrice === null || currentPrice <= 0) {
    issues.push('Falta el campo critico "current_price" valido.');
  }

  if (!timestamp) {
    issues.push('Falta el campo critico "timestamp" usable.');
  }

  return {
    contract: snapshotV2Contract.name,
    is_valid: issues.length === 0,
    issues,
    missing_fields: issues.length ? snapshotV2Contract.criticalFields.filter((field) => !payload[field]) : [],
    checked_at: new Date().toISOString(),
  };
}

export function adaptBotASnapshotV2(payload = {}, validation = null) {
  const criticalValidation = validation || validateSnapshotV2Payload(payload);

  if (!criticalValidation.is_valid) {
    const error = new Error(`Payload magi.snapshot.v2 invalido: ${criticalValidation.issues.join(" ")}`);
    error.statusCode = 400;
    error.validation = criticalValidation;
    throw error;
  }

  const symbol = normalizeSymbol(payload.symbol);
  const timestamp = normalizeTimestamp(payload.timestamp);
  const anchorTimestamp = normalizeTimestamp(payload.anchor_bar_timestamp);
  const barTimestamp = normalizeTimestamp(payload.bar_timestamp);
  const account = objectOrEmpty(payload.account);
  const position = objectOrEmpty(payload.position);
  const allowedActions = normalizeAllowedActions(payload.allowed_actions);
  const sourceValidation = objectOrEmpty(payload.validation);
  const normalized = createEmptyNormalizedSnapshot();

  normalized.schema_version = "snapshot_v2_normalized";
  normalized.snapshot_id = buildSnapshotId(payload, symbol, timestamp);
  normalized.symbol = symbol;
  normalized.timestamp = timestamp;
  normalized.source = {
    connector: "bot-a",
    transport: "http/webhook",
    contract: snapshotV2Contract.name,
    source_schema_version: payload.schema_version,
    source_mode: payload.source_mode || null,
  };
  normalized.timeframes = {
    anchor: payload.anchor_timeframe || null,
    primary: payload.primary_timeframe || null,
  };
  normalized.bars = {
    anchor_bar_timestamp: anchorTimestamp,
    bar_timestamp: barTimestamp,
    anchor_open: normalizeNumber(payload.anchor_open),
    anchor_high: normalizeNumber(payload.anchor_high),
    anchor_low: normalizeNumber(payload.anchor_low),
    anchor_close: normalizeNumber(payload.anchor_close),
  };
  normalized.market = {
    price: normalizeNumber(payload.current_price),
    open: normalizeNumber(payload.anchor_open),
    high: normalizeNumber(payload.anchor_high),
    low: normalizeNumber(payload.anchor_low),
    close: normalizeNumber(payload.anchor_close),
    context: deriveMarketContext(allowedActions, position),
    allowed_actions: allowedActions,
    spread_pips: normalizeNumber(payload.spread_pips),
    session: payload.active_session || null,
    support_levels: normalizeArray(payload.support_levels),
    resistance_levels: normalizeArray(payload.resistance_levels),
    mtf_alignment_status: payload.mtf_alignment_status || null,
    mtf_alignment_warnings: payload.mtf_alignment_warnings || "",
    mtf_data_source_status: payload.mtf_data_source_status || null,
  };
  normalized.position = {
    has_open_position: Boolean(position.has_open_position),
    open_positions_count: normalizeNumber(position.open_positions_count, 0),
    position_type: position.position_type ?? null,
    entry_price: normalizeNumber(position.entry_price),
    sl: normalizeNumber(position.sl),
    tp: normalizeNumber(position.tp),
    floating_pnl: normalizeNumber(position.floating_pnl),
    summary: position,
  };
  normalized.account = {
    balance: normalizeNumber(account.balance),
    equity: normalizeNumber(account.equity),
    daily_drawdown_percent: normalizeNumber(account.daily_drawdown_percent, 0),
    risk_percent_per_trade: normalizeNumber(account.risk_percent_per_trade, 0),
  };
  normalized.risk = {
    daily_drawdown_percent: normalized.account.daily_drawdown_percent,
    risk_percent_per_trade: normalized.account.risk_percent_per_trade,
  };
  normalized.news = normalizeArray(payload.news);
  normalized.operational_notes = payload.operational_notes || "";
  normalized.gaspar_context = objectOrEmpty(payload.gaspar_context);
  normalized.features = {
    timeframes: normalizeArray(payload.features),
    primary: {
      market_structure: payload.market_structure || null,
      structure_direction: payload.structure_direction || null,
      ema_20: normalizeNumber(payload.ema_20),
      ema_50: normalizeNumber(payload.ema_50),
      ema_200: normalizeNumber(payload.ema_200),
      rsi_14: normalizeNumber(payload.rsi_14),
      momentum: payload.momentum || null,
      recent_range: normalizeNumber(payload.recent_range),
    },
  };
  normalized.raw_indicators = {
    ...buildRawIndicators(payload),
    market_structure: payload.market_structure || null,
    structure_direction: payload.structure_direction || null,
    ema_20: normalizeNumber(payload.ema_20),
    ema_50: normalizeNumber(payload.ema_50),
    ema_200: normalizeNumber(payload.ema_200),
    rsi_14: normalizeNumber(payload.rsi_14),
    momentum: payload.momentum || null,
    recent_range: normalizeNumber(payload.recent_range),
  };
  normalized.validation = {
    is_valid: sourceValidation.is_valid !== false,
    issues: normalizeArray(sourceValidation.issues),
    source_validation: sourceValidation,
    adapter_validation: criticalValidation,
  };
  normalized.raw = payload;

  const adapterWarnings = collectWarnings(payload, normalized);
  normalized.validation.issues = [...normalized.validation.issues, ...adapterWarnings];
  normalized.validation.adapter_warnings = adapterWarnings;

  return {
    legacy: {
      contract: snapshotV2Contract.name,
      received_at: new Date().toISOString(),
      payload,
    },
    normalized,
  };
}
