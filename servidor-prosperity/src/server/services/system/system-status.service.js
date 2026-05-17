import { getLatestSnapshotSummary, countSnapshotsStored } from "../snapshots/snapshot-query.service.js";
import { listExecutionStates } from "../execution/execution-query.service.js";
import { getOperationalState } from "../governance/operational-governance.service.js";

export function buildOverviewSnapshot({ uptimeSeconds = 0, hasOpenAIKey = false }) {
  const latestSnapshot = getLatestSnapshotSummary();
  const totalSnapshots = countSnapshotsStored();
  const executionStates = listExecutionStates();
  const latestExecution = executionStates[0] || null;
  const governance = getOperationalState();

  return {
    status: "operativo",
    service: "prosperity-magi",
    uptime_seconds: uptimeSeconds,
    openai: hasOpenAIKey ? "configurado" : "no_configurado",
    snapshots: {
      total: totalSnapshots,
      latest: latestSnapshot,
    },
    bot_a: latestSnapshot
      ? {
          status: "recibiendo",
          last_snapshot_id: latestSnapshot.snapshot_id,
          last_received_at: latestSnapshot.received_at,
        }
      : {
          status: "sin_datos",
          last_snapshot_id: null,
          last_received_at: null,
        },
    execution: {
      total_symbols: executionStates.length,
      latest: latestExecution,
    },
    governance,
    timestamp: new Date().toISOString(),
  };
}
