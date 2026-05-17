import { createEmptyExecutionResponse } from "../../../domain/contracts/execution-response.js";

export function mapMvpDecisionToBotBResponse(decision, sourcePayload = {}) {
  const symbol = String(decision?.symbol || sourcePayload?.pair || sourcePayload?.symbol || "UNKNOWN").toUpperCase();
  const response = createEmptyExecutionResponse(symbol);
  const decisionId = decision?.decision_id || sourcePayload?.decision_id || null;
  const snapshotId = decision?.snapshot_id || sourcePayload?.snapshot_id || null;
  const shortDecisionId = String(decision?.short_decision_id || decisionId || snapshotId || "")
    .replace(/[^a-zA-Z0-9_-]/g, "")
    .slice(0, 12);
  const auditComment = shortDecisionId
    ? `MAGI|${shortDecisionId}`
    : (decision?.reason || "Decision MVP sin comentario adicional.");

  response.action = decision?.final_action || "hold";
  response.decision_id = decisionId;
  response.snapshot_id = snapshotId;
  response.decision_time = decision?.decision_time || new Date().toISOString();
  response.id_operacion =
    sourcePayload?.id_operacion
    || decisionId
    || decision?.snapshot_id
    || `${symbol}_${Date.now()}`;
  response.details = {
    symbol,
    order_type: decision?.direction || "",
    entry_price: Number(decision?.entry_price || 0),
    stop_loss: Number(decision?.stop_loss || 0),
    take_profit: Number(decision?.take_profit || 0),
    lot_size: Number(decision?.lot_size || 0),
    comment: auditComment,
    reason: decision?.reason || "Decision MVP sin comentario adicional.",
  };
  response.risk_state = decision?.risk_state || null;
  response.cluster_state = decision?.cluster_state || null;
  response.shadow_guardrails = decision?.shadow_guardrails || null;
  response.current_lot_size = decision?.current_lot_size || response.details.lot_size;
  response.demo_mode_until = decision?.demo_mode_until || null;
  response.be_auto_status = decision?.be_auto_status || null;
  response.news_guardrail_status = decision?.news_guardrail_status || null;
  response.timestamp = new Date().toISOString();

  return response;
}
