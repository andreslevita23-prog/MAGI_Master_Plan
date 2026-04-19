import { defineConnector } from "../shared.js";

export const botBConnector = defineConnector({
  id: "bot-b",
  name: "Bot B",
  family: "execution-bot",
  role: "Salida de decisiones operativas",
  description: "Consume la decision final normalizada y la prepara para ejecucion futura.",
  inputContract: {
    type: "trade-decision",
    requiredFields: ["action", "id_operacion", "details.symbol"],
    optionalFields: ["details.order_type", "details.stop_loss", "details.take_profit"],
  },
  outputContract: {
    type: "execution-command",
    fields: ["symbol", "action", "risk", "comment"],
  },
  connection: {
    transport: "file/http",
    target: "data/analysis + adapter de salida",
    requiredEnv: ["MAGI_BOT_B_ENDPOINT"],
    mockEnabled: true,
  },
  mock: {
    notes: "No ejecuta trading real; deja preparado el contrato de despacho.",
    sample: {
      action: "hold",
      id_operacion: "mock_001",
      details: {
        symbol: "EURUSD",
        comment: "Decision mock para despacho controlado.",
      },
    },
  },
});
