import fs from "fs";
import path from "path";
import { paths } from "../../config/paths.js";
import { fileExists, readJson } from "../storage.js";

function listSnapshotIds() {
  if (!fs.existsSync(paths.snapshotNormalized)) {
    return [];
  }

  return fs
    .readdirSync(paths.snapshotNormalized)
    .filter((fileName) => fileName.endsWith(".json"))
    .map((fileName) => ({
      snapshot_id: path.basename(fileName, ".json"),
      file_path: path.join(paths.snapshotNormalized, fileName),
      stats: fs.statSync(path.join(paths.snapshotNormalized, fileName)),
    }))
    .sort((left, right) => right.stats.mtimeMs - left.stats.mtimeMs);
}

function buildSnapshotPaths(snapshotId) {
  return {
    legacy: path.join(paths.snapshotLegacy, `${snapshotId}.json`),
    normalized: path.join(paths.snapshotNormalized, `${snapshotId}.json`),
  };
}

function buildSnapshotSummary(legacyEnvelope, normalizedSnapshot, snapshotId) {
  return {
    snapshot_id: snapshotId,
    symbol: normalizedSnapshot?.symbol || legacyEnvelope?.payload?.pair || "UNKNOWN",
    timestamp: normalizedSnapshot?.timestamp || legacyEnvelope?.payload?.timestamp || null,
    received_at: legacyEnvelope?.received_at || null,
    stored_at: normalizedSnapshot?.stored_at || legacyEnvelope?.stored_at || null,
    context: normalizedSnapshot?.market?.context || legacyEnvelope?.payload?.context || "unknown",
    price: normalizedSnapshot?.market?.price || 0,
    allowed_actions: normalizedSnapshot?.market?.allowed_actions || [],
    has_open_position: normalizedSnapshot?.position?.has_open_position || false,
    open_positions_count: normalizedSnapshot?.position?.open_positions_count || 0,
    is_valid: normalizedSnapshot?.validation?.is_valid || false,
    issues: normalizedSnapshot?.validation?.issues || [],
  };
}

export function listRecentSnapshots(limit = 20) {
  return listSnapshotIds()
    .slice(0, limit)
    .map(({ snapshot_id }) => {
      const pathsBySnapshot = buildSnapshotPaths(snapshot_id);
      const legacyEnvelope = readJson(pathsBySnapshot.legacy);
      const normalizedSnapshot = readJson(pathsBySnapshot.normalized);

      return buildSnapshotSummary(legacyEnvelope, normalizedSnapshot, snapshot_id);
    })
    .filter(Boolean);
}

export function getLatestSnapshotSummary() {
  return listRecentSnapshots(1)[0] || null;
}

export function countSnapshotsStored() {
  return listSnapshotIds().length;
}

export function getSnapshotDetail(snapshotId) {
  const pathsBySnapshot = buildSnapshotPaths(snapshotId);

  if (!fileExists(pathsBySnapshot.normalized) && !fileExists(pathsBySnapshot.legacy)) {
    return null;
  }

  const legacyEnvelope = readJson(pathsBySnapshot.legacy);
  const normalizedSnapshot = readJson(pathsBySnapshot.normalized);

  return {
    snapshot_id: snapshotId,
    summary: buildSnapshotSummary(legacyEnvelope, normalizedSnapshot, snapshotId),
    files: {
      legacy_exists: fileExists(pathsBySnapshot.legacy),
      normalized_exists: fileExists(pathsBySnapshot.normalized),
    },
    legacy: legacyEnvelope,
    normalized: normalizedSnapshot,
  };
}
