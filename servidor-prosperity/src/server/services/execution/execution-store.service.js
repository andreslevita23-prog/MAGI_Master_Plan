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
    risk_state: decision?.risk_state || response?.risk_state || null,
    cluster_state: decision?.cluster_state || response?.cluster_state || null,
    shadow_guardrails: decision?.shadow_guardrails || response?.shadow_guardrails || null,
    current_lot_size: decision?.current_lot_size || response?.current_lot_size || response?.details?.lot_size || 0,
    demo_mode_until: decision?.demo_mode_until || response?.demo_mode_until || null,
  };

  writeJsonWithTimestamp(filePath, executionState);

  return {
    file_path: filePath,
    state: executionState,
  };
}
