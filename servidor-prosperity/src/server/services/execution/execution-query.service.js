import path from "path";
import { paths } from "../../config/paths.js";
import { listFiles, readJson } from "../storage.js";

function listExecutionFiles() {
  return listFiles(paths.execution, ".json").sort((left, right) => {
    const leftName = path.basename(left).toLowerCase();
    const rightName = path.basename(right).toLowerCase();
    return leftName.localeCompare(rightName);
  });
}

function buildExecutionSummary(executionState) {
  return {
    symbol: executionState.symbol,
    snapshot_id: executionState.snapshot_id,
    decision_id: executionState.decision?.decision_id || executionState.response?.decision_id || null,
    decision_time: executionState.decision?.decision_time || executionState.response?.decision_time || null,
    case_state: executionState.case_state,
    case_type: executionState.case_type,
    final_action: executionState.decision?.final_action || executionState.response?.action || "hold",
    reason: executionState.decision?.reason || executionState.response?.details?.comment || "",
    risk_state: executionState.risk_state || executionState.decision?.risk_state || executionState.response?.risk_state || null,
    cluster_state: executionState.cluster_state || executionState.decision?.cluster_state || executionState.response?.cluster_state || null,
    shadow_guardrails:
      executionState.shadow_guardrails
      || executionState.decision?.shadow_guardrails
      || executionState.response?.shadow_guardrails
      || null,
    current_lot_size:
      executionState.current_lot_size
      || executionState.decision?.current_lot_size
      || executionState.response?.current_lot_size
      || executionState.response?.details?.lot_size
      || 0,
    demo_mode_until: executionState.demo_mode_until || executionState.decision?.demo_mode_until || executionState.response?.demo_mode_until || null,
    melchor_vote: executionState.decision?.melchor_vote || null,
    baltasar_vote: executionState.decision?.baltasar_vote || null,
    gaspar_vote: executionState.decision?.gaspar_vote || null,
    ceo_decision: executionState.decision?.ceo_magi_decision || {
      source: executionState.decision?.source || null,
      final_action: executionState.decision?.final_action || null,
      direction: executionState.decision?.direction || null,
      override_melchor: executionState.decision?.override_melchor || false,
      override_reason: executionState.decision?.override_reason || null,
    },
    bot_b_response: executionState.response || null,
    stored_at: executionState.stored_at || null,
  };
}

export function listExecutionStates() {
  return listExecutionFiles()
    .map((filePath) => readJson(filePath))
    .filter(Boolean)
    .map(buildExecutionSummary)
    .sort((left, right) => String(right.stored_at || "").localeCompare(String(left.stored_at || "")));
}
