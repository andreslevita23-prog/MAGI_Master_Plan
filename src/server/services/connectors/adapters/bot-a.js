import { defineConnector } from "../shared.js";

export const botAConnector = defineConnector({
  id: "bot-a",
  name: "Bot A",
  family: "execution-bot",
  role: "Entrada de contexto y datos de mercado",
  description: "Recibe snapshots de mercado y contexto operativo antes del analisis.",
  inputContract: {
    type: "market-context",
    requiredFields: ["timestamp", "pair", "price", "context"],
    optionalFields: ["high", "low", "allowed_actions", "timeframes"],
  },
  outputContract: {
    type: "normalized-market-context",
    fields: ["pair", "context", "timeframes", "riskWindow"],
  },
  connection: {
    transport: "http/webhook",
    target: "POST /analisis",
    requiredEnv: ["MAGI_BOT_A_ENDPOINT"],
    mockEnabled: true,
  },
  mock: {
    notes: "Usar webhook HTTP o adaptador MT5 que publique JSON normalizado.",
    sample: {
      timestamp: "2026-04-19T07:00:00Z",
      pair: "EURUSD",
      price: 1.1,
      context: "waiting_for_entry",
    },
  },
});
