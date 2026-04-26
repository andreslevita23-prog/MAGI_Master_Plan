import { defineConnector } from "../shared.js";

export const melchorConnector = defineConnector({
  id: "melchor",
  name: "Melchor",
  family: "magi-module",
  role: "Seguridad / Riesgo",
  description: "Valida exposicion, limites diarios y politicas de riesgo antes de habilitar acciones.",
  inputContract: {
    type: "risk-assessment-request",
    requiredFields: ["snapshot", "candidateTrade"],
    optionalFields: ["accountContext", "riskPolicyVersion"],
  },
  outputContract: {
    type: "magi-vote",
    fields: [
      "module",
      "version",
      "vote",
      "risk_block_recommendation",
      "confidence",
      "risk_level",
      "reason",
      "rules_triggered",
      "recommended_action",
    ],
  },
  connection: {
    transport: "internal-service",
    target: "services/melchor-risk-engine.js",
    requiredEnv: ["MAGI_MELCHOR_MODE"],
    mockEnabled: true,
  },
  mock: {
    notes: "Melchor v1 es deterministico, auditable y conservador.",
    sample: {
      module: "MELCHOR",
      version: "v1.0",
      vote: "ALLOW",
      risk_block_recommendation: false,
      confidence: 1.0,
      risk_level: "LOW",
      reason: "Reglas Melchor v1 superadas.",
      rules_triggered: [],
      recommended_action: {
        action: "hold",
        details: {},
      },
    },
  },
});
