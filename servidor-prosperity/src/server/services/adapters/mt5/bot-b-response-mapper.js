import { createEmptyExecutionResponse } from "../../../domain/contracts/execution-response.js";

export function mapMvpDecisionToBotBResponse(decision, sourcePayload = {}) {
  const symbol = String(decision?.symbol || sourcePayload?.pair || "UNKNOWN").toUpperCase();
  const response = createEmptyExecutionResponse(symbol);

  response.action = decision?.final_action || "hold";
  response.id_operacion =
    sourcePayload?.id_operacion
    || decision?.snapshot_id
    || `${symbol}_${Date.now()}`;
  response.details = {
    symbol,
    order_type: decision?.direction || "",
    entry_price: Number(decision?.entry_price || 0),
    stop_loss: Number(decision?.stop_loss || 0),
    take_profit: Number(decision?.take_profit || 0),
    lot_size: Number(decision?.lot_size || 0),
    comment: decision?.reason || "Decision MVP sin comentario adicional.",
  };
  response.timestamp = new Date().toISOString();

  return response;
}
