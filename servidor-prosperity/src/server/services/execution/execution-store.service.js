import path from "path";
import { paths } from "../../config/paths.js";
import { writeJsonWithTimestamp } from "../storage.js";

export function persistExecutionState({ decision, response }) {
  const symbol = String(response?.details?.symbol || decision?.symbol || "UNKNOWN").toUpperCase();
  const filePath = path.join(paths.execution, `${symbol}.json`);

  const executionState = {
    symbol,
    snapshot_id: decision?.snapshot_id || null,
    case_state: decision?.case_state || "sin_caso",
    case_type: decision?.case_type || null,
    decision,
    response,
  };

  writeJsonWithTimestamp(filePath, executionState);

  return {
    file_path: filePath,
    state: executionState,
  };
}
