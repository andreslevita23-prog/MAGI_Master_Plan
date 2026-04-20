import { defineConnector } from "../shared.js";

export const baltasarConnector = defineConnector({
  id: "baltasar",
  name: "Baltasar",
  family: "magi-module",
  role: "Analisis tecnico / Datos",
  description: "Consolida series, estructura y senales para alimentar decisiones.",
  inputContract: {
    type: "analysis-request",
    requiredFields: ["symbol", "timeframes"],
    optionalFields: ["indicators", "marketStructure", "volatility"],
  },
  outputContract: {
    type: "analysis-response",
    fields: ["bias", "keyLevels", "signalStrength", "notes"],
  },
  connection: {
    transport: "internal-service",
    target: "analysis pipeline",
    requiredEnv: ["MAGI_BALTASAR_SOURCE"],
    mockEnabled: true,
  },
  mock: {
    notes: "Sustituible luego por pipeline tecnico real o proveedor de datos.",
    sample: {
      bias: "neutral",
      keyLevels: ["1.0980", "1.1020"],
      signalStrength: 0.48,
      notes: "Estructura mixta en H1/H4.",
    },
  },
});
