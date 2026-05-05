import crypto from "node:crypto";
import path from "node:path";
import { paths } from "../../config/paths.js";
import { appendText, ensureDirectory } from "../storage.js";

function dayFolder(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

function compactId(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 12);
}

function buildDecisionId(decision = {}) {
  if (decision.decision_id) {
    return String(decision.decision_id);
  }

  const seed = [
    decision.snapshot_id,
    decision.symbol,
    decision.final_action,
    decision.direction,
    decision.reason,
    Date.now(),
  ].join("|");

  return `magi_${crypto.createHash("sha256").update(seed).digest("hex").slice(0, 16)}`;
}

export function ensureDecisionAuditIdentity(decision = {}) {
  const decisionId = buildDecisionId(decision);
  const decisionTime = decision.decision_time || new Date().toISOString();

  return {
    ...decision,
    decision_id: decisionId,
    decision_time: decisionTime,
    short_decision_id: compactId(decisionId),
  };
}

export function buildDecisionAuditRecord({
  snapshot,
  decision,
  executionPayload,
  snapshotArtifacts,
  executionState,
  status = "sent",
}) {
  const details = executionPayload?.details || {};

  return {
    schema_version: "magi.audit.decision.v1",
    status,
    decision_id: decision?.decision_id || null,
    snapshot_id: decision?.snapshot_id || snapshot?.snapshot_id || null,
    symbol: decision?.symbol || details.symbol || snapshot?.symbol || "UNKNOWN",
    decision_time: decision?.decision_time || executionPayload?.decision_time || new Date().toISOString(),
    final_action: decision?.final_action || executionPayload?.action || "hold",
    order_type: details.order_type || decision?.direction || "",
    lot_size: Number(details.lot_size || decision?.lot_size || 0),
    sl: Number(details.stop_loss || decision?.stop_loss || 0),
    tp: Number(details.take_profit || decision?.take_profit || 0),
    reason: decision?.reason || details.comment || "",
    melchor_vote: decision?.melchor_vote || null,
    baltasar_vote: decision?.baltasar_vote || null,
    gaspar_vote: decision?.gaspar_vote || null,
    ceo_decision: decision?.ceo_magi_decision || {
      source: decision?.source || null,
      final_action: decision?.final_action || null,
      direction: decision?.direction || null,
      override_melchor: decision?.override_melchor || false,
      override_reason: decision?.override_reason || null,
    },
    override_melchor: Boolean(decision?.override_melchor),
    execution_payload: executionPayload || null,
    files: {
      snapshot_legacy: snapshotArtifacts?.legacy_file || null,
      snapshot_normalized: snapshotArtifacts?.normalized_file || null,
      execution_state: executionState?.file_path || null,
      melchor_vote: decision?.melchor_vote_file || null,
    },
    recorded_at: new Date().toISOString(),
  };
}

export function persistDecisionAuditRecord(record) {
  const folder = path.join(paths.auditDecisions, dayFolder());
  ensureDirectory(folder);
  const filePath = path.join(folder, "magi_decisions.jsonl");
  appendText(filePath, `${JSON.stringify(record)}\n`);

  return {
    file_path: filePath,
    record,
  };
}
