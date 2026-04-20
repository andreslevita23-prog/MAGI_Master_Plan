export const snapshotLegacyContract = {
  name: "snapshot_legacy_mt5",
  description: "Contrato de entrada legacy enviado por Bot A hacia POST /analisis.",
  requiredFields: [
    "timestamp",
    "pair",
    "price",
    "context",
    "allowed_actions",
    "id_operacion",
  ],
  optionalFields: [
    "high",
    "low",
    "open_positions_count",
    "position_info",
    "stop_distance_pips",
  ],
  dynamicFieldPrefixes: [
    "candle_pattern_",
    "market_structure_",
    "ema20_",
    "ema50_",
    "rsi14_",
  ],
};

export function buildSnapshotLegacyEnvelope(payload = {}) {
  return {
    contract: snapshotLegacyContract.name,
    received_at: new Date().toISOString(),
    payload,
  };
}
