import { defineConnector } from "../shared.js";

export const botCConnector = defineConnector({
  id: "bot-c",
  name: "Bot C",
  family: "execution-bot",
  role: "Confirmacion complementaria o enriquecimiento",
  description: "Reserva para validaciones adicionales, scoring o confirmaciones externas.",
  inputContract: {
    type: "decision-review-request",
    requiredFields: ["symbol", "context"],
    optionalFields: ["signalStrength", "riskScore", "sourceDecision"],
  },
  outputContract: {
    type: "decision-review-response",
    fields: ["status", "recommendation", "confidence"],
  },
  connection: {
    transport: "http/queue",
    target: "adapter pending",
    requiredEnv: ["MAGI_BOT_C_ENDPOINT"],
    mockEnabled: true,
  },
  mock: {
    notes: "Puede convertirse en motor de confirmacion previa a CEO-MAGI.",
    sample: {
      status: "ready",
      recommendation: "hold",
      confidence: 0.55,
    },
  },
});
