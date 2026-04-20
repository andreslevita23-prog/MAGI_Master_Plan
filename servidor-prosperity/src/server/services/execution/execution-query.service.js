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
    case_state: executionState.case_state,
    case_type: executionState.case_type,
    final_action: executionState.decision?.final_action || executionState.response?.action || "hold",
    reason: executionState.decision?.reason || executionState.response?.details?.comment || "",
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
