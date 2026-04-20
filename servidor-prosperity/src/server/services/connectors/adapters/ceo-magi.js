import { defineConnector } from "../shared.js";

export const ceoMagiConnector = defineConnector({
  id: "ceo-magi",
  name: "CEO-MAGI",
  family: "magi-module",
  role: "Decision final",
  description: "Orquesta la salida final a partir de los insumos de los modulos MAGI y bots.",
  inputContract: {
    type: "orchestration-request",
    requiredFields: ["riskAssessment", "technicalAssessment", "opportunityAssessment"],
    optionalFields: ["executionFeedback", "humanOverride"],
  },
  outputContract: {
    type: "orchestration-response",
    fields: ["decision", "confidence", "reasoningSummary", "handoff"],
  },
  connection: {
    transport: "internal-orchestrator",
    target: "future orchestration service",
    requiredEnv: ["MAGI_CEO_MODE"],
    mockEnabled: true,
  },
  mock: {
    notes: "Deja definido el punto de arbitraje final sin acoplar trading real.",
    sample: {
      decision: "hold",
      confidence: 0.61,
      reasoningSummary: "Riesgo contenido pero sin confluencia suficiente.",
      handoff: "bot-b",
    },
  },
});
