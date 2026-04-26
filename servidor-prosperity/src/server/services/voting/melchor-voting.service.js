import path from "path";
import { paths } from "../../config/paths.js";
import { evaluateMelchorRisk } from "../../../../services/melchor-risk-engine.js";
import { writeJson } from "../storage.js";

function safeSegment(value, fallback = "unknown") {
  const cleaned = String(value || fallback)
    .trim()
    .replace(/[<>:"/\\|?*\s.]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

  return cleaned || fallback;
}

function buildVotePath(vote) {
  const timestamp = safeSegment(vote.timestamp || new Date().toISOString(), "vote");
  const symbol = safeSegment(vote.symbol, "UNKNOWN");
  const snapshotId = safeSegment(vote.snapshot_id, "snapshot");

  return path.join(paths.melchorVotes, `${timestamp}_${symbol}_${snapshotId}.json`);
}

export function persistMelchorVote(vote) {
  const filePath = buildVotePath(vote);
  writeJson(filePath, vote);

  return {
    file_path: filePath,
    vote,
  };
}

export function evaluateAndPersistMelchorVote(snapshot, options = {}) {
  const vote = evaluateMelchorRisk(snapshot, options);
  return persistMelchorVote(vote);
}
