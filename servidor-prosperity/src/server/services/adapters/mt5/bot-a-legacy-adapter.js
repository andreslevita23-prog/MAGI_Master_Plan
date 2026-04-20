import {
  buildSnapshotLegacyEnvelope,
  snapshotLegacyContract,
} from "../../../domain/contracts/snapshot-legacy.js";
import { createEmptyNormalizedSnapshot } from "../../../domain/contracts/snapshot-normalized.js";

function normalizeSymbol(value) {
  return String(value || "UNKNOWN").trim().toUpperCase();
}

function normalizeTimestamp(value) {
  const candidate = String(value || "").trim();

  if (!candidate) {
    return new Date().toISOString();
  }

  const parsed = new Date(candidate);
  return Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();
}

function normalizeNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeAllowedActions(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }

  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item).trim()).filter(Boolean);
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

function sanitizeFileSafeSegment(value) {
  return String(value || "")
    .trim()
    .replace(/[<>:"/\\|?*\s]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function buildSnapshotId(payload = {}, symbol = "UNKNOWN") {
  const baseOperationId = sanitizeFileSafeSegment(payload.id_operacion);

  if (baseOperationId) {
    return `${symbol}_${baseOperationId}`;
  }

  const timestamp = sanitizeFileSafeSegment(normalizeTimestamp(payload.timestamp));
  return `${symbol}_${timestamp}`;
}

export function adaptBotALegacySnapshot(payload = {}, validation = null) {
  const symbol = normalizeSymbol(payload.pair);
  const normalized = createEmptyNormalizedSnapshot();

  normalized.snapshot_id = buildSnapshotId(payload, symbol);
  normalized.symbol = symbol;
  normalized.timestamp = normalizeTimestamp(payload.timestamp);
  normalized.source = {
    connector: "bot-a",
    transport: "http/webhook",
    contract: snapshotLegacyContract.name,
  };
  normalized.market = {
    price: normalizeNumber(payload.price),
    high: normalizeNumber(payload.high),
    low: normalizeNumber(payload.low),
    context: String(payload.context || "unknown").trim() || "unknown",
    allowed_actions: normalizeAllowedActions(payload.allowed_actions),
    stop_distance_pips: normalizeNumber(payload.stop_distance_pips),
  };
  normalized.position = {
    has_open_position: normalizeNumber(payload.open_positions_count) > 0,
    open_positions_count: normalizeNumber(payload.open_positions_count),
    summary: payload.position_info || null,
  };
  normalized.raw_indicators = Object.fromEntries(
    Object.entries(payload).filter(([key]) =>
      ["candle_pattern_", "market_structure_", "ema20_", "ema50_", "rsi14_"].some(
        (prefix) => key.startsWith(prefix),
      ),
    ),
  );
  normalized.validation = validation || {
    is_valid: true,
    issues: [],
  };

  return {
    legacy: buildSnapshotLegacyEnvelope(payload),
    normalized,
  };
}
