import { defineConnector } from "../shared.js";

export const gasparConnector = defineConnector({
  id: "gaspar",
  name: "Gaspar",
  family: "magi-module",
  role: "Exploracion / Oportunidad",
  description: "Busca oportunidades y prioriza simbolos o escenarios de interes.",
  inputContract: {
    type: "opportunity-scan-request",
    requiredFields: ["watchlist", "session"],
    optionalFields: ["volatilityMap", "newsContext"],
  },
  outputContract: {
    type: "opportunity-scan-response",
    fields: ["candidates", "priority", "rationale"],
  },
  connection: {
    transport: "internal-service",
    target: "scanner pipeline",
    requiredEnv: ["MAGI_GASPAR_SOURCE"],
    mockEnabled: true,
  },
  mock: {
    notes: "Base pensada para watchlists dinamicas y filtros por sesion.",
    sample: {
      candidates: ["EURUSD", "XAUUSD"],
      priority: "medium",
      rationale: "Volatilidad y liquidez alineadas con la sesion.",
    },
  },
});
