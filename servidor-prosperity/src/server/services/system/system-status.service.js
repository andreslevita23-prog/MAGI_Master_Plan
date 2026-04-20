import { getLatestSnapshotSummary, countSnapshotsStored } from "../snapshots/snapshot-query.service.js";

export function buildOverviewSnapshot({ uptimeSeconds = 0, hasOpenAIKey = false }) {
  const latestSnapshot = getLatestSnapshotSummary();
  const totalSnapshots = countSnapshotsStored();

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
    timestamp: new Date().toISOString(),
  };
}
