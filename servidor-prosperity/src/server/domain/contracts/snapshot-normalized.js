export const snapshotNormalizedContract = {
  name: "snapshot_v1",
  description: "Contrato canonico interno para snapshots normalizados del backend MAGI.",
  requiredFields: [
    "snapshot_id",
    "symbol",
    "timestamp",
    "source",
    "market",
    "position",
    "validation",
  ],
  nestedFields: {
    source: ["connector", "transport"],
    market: ["price", "context", "allowed_actions"],
    position: ["has_open_position", "open_positions_count", "summary"],
    validation: ["is_valid", "issues"],
  },
};

export function createEmptyNormalizedSnapshot() {
  return {
    snapshot_id: "",
    symbol: "UNKNOWN",
    timestamp: "",
    source: {
      connector: "bot-a",
      transport: "http/webhook",
    },
    market: {
      price: 0,
      context: "unknown",
      allowed_actions: [],
    },
    position: {
      has_open_position: false,
      open_positions_count: 0,
      summary: null,
    },
    validation: {
      is_valid: false,
      issues: [],
    },
  };
}
