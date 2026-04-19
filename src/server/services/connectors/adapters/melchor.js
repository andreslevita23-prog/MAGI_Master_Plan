import { defineConnector } from "../shared.js";

export const melchorConnector = defineConnector({
  id: "melchor",
  name: "Melchor",
  family: "magi-module",
  role: "Seguridad / Riesgo",
  description: "Valida exposicion, limites diarios y politicas de riesgo antes de habilitar acciones.",
  inputContract: {
    type: "risk-assessment-request",
    requiredFields: ["balance", "dailyDrawdown", "openExposure"],
    optionalFields: ["candidateTrade", "riskPolicyVersion"],
  },
  outputContract: {
    type: "risk-assessment-response",
    fields: ["status", "riskScore", "blockingReasons"],
  },
  connection: {
    transport: "internal-service",
    target: "src/server/services/connectors/adapters/melchor.js",
    requiredEnv: ["MAGI_MELCHOR_MODE"],
    mockEnabled: true,
  },
  mock: {
    notes: "Modulo listo para una futura politica central de riesgo.",
    sample: {
      status: "monitoring",
      riskScore: 0.22,
      blockingReasons: [],
    },
  },
});
