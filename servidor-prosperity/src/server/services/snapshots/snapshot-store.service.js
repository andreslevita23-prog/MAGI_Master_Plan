import path from "path";
import { paths } from "../../config/paths.js";
import { writeJsonWithTimestamp } from "../storage.js";

function safeSnapshotFileId(snapshotId) {
  return String(snapshotId || `snapshot_${Date.now()}`)
    .trim()
    .replace(/[<>:"/\\|?*\s]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function buildSnapshotFilePath(baseDir, snapshotId) {
  return path.join(baseDir, `${safeSnapshotFileId(snapshotId)}.json`);
}

export function persistSnapshotArtifacts({ legacy, normalized }) {
  const snapshotId = normalized?.snapshot_id || `snapshot_${Date.now()}`;
  const snapshotFileId = safeSnapshotFileId(snapshotId);

  const legacyFilePath = buildSnapshotFilePath(paths.snapshotLegacy, snapshotId);
  const normalizedFilePath = buildSnapshotFilePath(paths.snapshotNormalized, snapshotId);

  writeJsonWithTimestamp(legacyFilePath, legacy);
  writeJsonWithTimestamp(normalizedFilePath, normalized);

  return {
    snapshot_id: snapshotId,
    snapshot_file_id: snapshotFileId,
    legacy_file: legacyFilePath,
    normalized_file: normalizedFilePath,
    validation: normalized?.validation || null,
  };
}
