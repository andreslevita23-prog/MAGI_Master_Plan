import path from "path";
import { paths } from "../../config/paths.js";
import { writeJsonWithTimestamp } from "../storage.js";

function buildSnapshotFilePath(baseDir, snapshotId) {
  return path.join(baseDir, `${snapshotId}.json`);
}

export function persistSnapshotArtifacts({ legacy, normalized }) {
  const snapshotId = normalized?.snapshot_id || `snapshot_${Date.now()}`;

  const legacyFilePath = buildSnapshotFilePath(paths.snapshotLegacy, snapshotId);
  const normalizedFilePath = buildSnapshotFilePath(paths.snapshotNormalized, snapshotId);

  writeJsonWithTimestamp(legacyFilePath, legacy);
  writeJsonWithTimestamp(normalizedFilePath, normalized);

  return {
    snapshot_id: snapshotId,
    legacy_file: legacyFilePath,
    normalized_file: normalizedFilePath,
    validation: normalized?.validation || null,
  };
}
