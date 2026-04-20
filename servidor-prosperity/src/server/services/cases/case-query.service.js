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

function buildCaseSummary(executionState) {
  if (!executionState) {
    return null;
  }

  return {
    case_id: executionState.snapshot_id,
    symbol: executionState.symbol,
    case_state: executionState.case_state,
    case_type: executionState.case_type,
    final_action: executionState.decision?.final_action || executionState.response?.action || "hold",
    reason: executionState.decision?.reason || executionState.response?.details?.comment || "",
    response_ready: Boolean(executionState.response),
    response_action: executionState.response?.action || "hold",
    stored_at: executionState.stored_at || null,
  };
}

export function listCases() {
  return listExecutionFiles()
    .map((filePath) => readJson(filePath))
    .filter(Boolean)
    .map(buildCaseSummary)
    .filter(Boolean)
    .sort((left, right) => String(right.stored_at || "").localeCompare(String(left.stored_at || "")));
}

export function getCaseById(caseId) {
  const executionState = listExecutionFiles()
    .map((filePath) => readJson(filePath))
    .filter(Boolean)
    .find((item) => item.snapshot_id === caseId);

  if (!executionState) {
    return null;
  }

  return {
    summary: buildCaseSummary(executionState),
    decision: executionState.decision || null,
    response: executionState.response || null,
    stored_at: executionState.stored_at || null,
  };
}
