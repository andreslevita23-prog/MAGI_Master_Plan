export const executionResponseContract = {
  name: "bot_b_legacy_response",
  description: "Contrato de salida compatible con GET /analisis/:symbol para Bot B.",
  requiredFields: ["action", "id_operacion", "details", "timestamp"],
  nestedFields: {
    details: [
      "symbol",
      "order_type",
      "entry_price",
      "stop_loss",
      "take_profit",
      "lot_size",
      "comment",
    ],
  },
};

export function createEmptyExecutionResponse(symbol = "UNKNOWN") {
  return {
    action: "hold",
    id_operacion: `${symbol}_pending`,
    details: {
      symbol,
      order_type: "",
      entry_price: 0,
      stop_loss: 0,
      take_profit: 0,
      lot_size: 0,
      comment: "Respuesta aun no generada por la nueva capa MAGI.",
    },
    timestamp: new Date().toISOString(),
  };
}
