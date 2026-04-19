import path from "path";
import { paths } from "../config/paths.js";
import {
  listDirectories,
  listFiles,
  readJson,
  readJsonLines,
} from "./storage.js";

const moduleCatalog = [
  {
    id: "melchor",
    name: "Melchor",
    role: "Seguridad / Riesgo",
    description: "Valida limites operativos, exposicion y consistencia del riesgo.",
  },
  {
    id: "baltasar",
    name: "Baltasar",
    role: "Analisis tecnico / Datos",
    description: "Consolida estructura, momentum y calidad de entrada.",
  },
  {
    id: "gaspar",
    name: "Gaspar",
    role: "Exploracion / Oportunidad",
    description: "Prioriza escenarios, simbolos y ventanas activas.",
  },
  {
    id: "ceo-magi",
    name: "CEO-MAGI",
    role: "Decision final",
    description: "Orquesta la salida final y alinea ejecucion con el sistema.",
  },
];

function formatAction(action = "hold") {
  const labels = {
    open: "Open",
    hold: "Hold",
    close: "Close",
    modify: "Modify",
    move_sl: "Move SL",
  };

  return labels[action] || action;
}

function getLatestLogFolder() {
  const folders = listDirectories(paths.logs)
    .map((folderPath) => path.basename(folderPath))
    .sort();

  return folders.at(-1) || null;
}

function loadLatestSignals(limit = 8) {
  const latestFolder = getLatestLogFolder();
  if (!latestFolder) {
    return [];
  }

  const filePath = path.join(paths.logs, latestFolder, "botB.jsonl");

  return readJsonLines(filePath)
    .slice(-limit)
    .reverse()
    .map((entry, index) => ({
      id: `${entry.id_operacion || latestFolder}-${index}`,
      timestamp: entry.timestamp_utc,
      symbol: entry.details?.symbol || "UNKNOWN",
      action: formatAction(entry.action),
      confidence: entry.action === "open" ? "High" : "Monitoring",
      comment: entry.details?.comment || "Sin comentario disponible.",
      orderType: entry.details?.order_type || "-",
      lotSize: entry.details?.lot_size ?? 0,
    }));
}

function loadRecentLogs(limit = 10) {
  const latestFolder = getLatestLogFolder();
  if (!latestFolder) {
    return [];
  }

  const files = ["api.jsonl", "botA.jsonl", "botB.jsonl"];

  return files
    .flatMap((fileName) => {
      const filePath = path.join(paths.logs, latestFolder, fileName);
      return readJsonLines(filePath).map((entry) => ({
        source: fileName.replace(".jsonl", ""),
        timestamp: entry.timestamp_utc,
        summary:
          entry.details?.comment ||
          entry.respuesta_raw ||
          entry.pair ||
          entry.symbol ||
          "Evento registrado.",
      }));
    })
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, limit);
}

function loadAnalysisStatus() {
  return listFiles(paths.analysis, ".json")
    .map((filePath) => readJson(filePath))
    .filter(Boolean)
    .map((item) => ({
      symbol: item.details?.symbol || "UNKNOWN",
      action: item.action || "hold",
      comment: item.details?.comment || "Sin comentario.",
      updatedAt: item.timestamp || item.id_operacion || null,
    }));
}

function computeOverview(signals, analysisStatus, uptimeSeconds) {
  const openSignals = signals.filter((signal) => signal.action === "Open").length;
  const latestSignal = signals[0];

  return {
    systemStatus: "Operational",
    trackedSymbols: analysisStatus.length,
    activeSignals: openSignals,
    lastDecisionAt: latestSignal?.timestamp || null,
    uptimeSeconds,
    activitySummary:
      analysisStatus.length > 0
        ? `${analysisStatus.length} simbolos con estado persistido.`
        : "Sin simbolos persistidos aun.",
    latestFolder: getLatestLogFolder(),
  };
}

function computeModules(signals, analysisStatus) {
  const openSignals = signals.filter((signal) => signal.action === "Open").length;
  const recentAnalyses = analysisStatus.length;

  return moduleCatalog.map((module) => {
    if (module.id === "melchor") {
      return {
        ...module,
        status: openSignals > 0 ? "Guarding risk" : "Watching exposure",
        metric: `${openSignals} decisiones abiertas`,
      };
    }

    if (module.id === "baltasar") {
      return {
        ...module,
        status: recentAnalyses > 0 ? "Analyzing flow" : "Awaiting market data",
        metric: `${recentAnalyses} simbolos evaluados`,
      };
    }

    if (module.id === "gaspar") {
      return {
        ...module,
        status: "Ready for discovery",
        metric: "Mock opportunities enabled",
      };
    }

    return {
      ...module,
      status: "Coordinating output",
      metric: signals[0]?.action || "No recent decision",
    };
  });
}

function buildSettingsSnapshot(port, hasOpenAIKey) {
  return {
    environment: process.env.NODE_ENV || "development",
    siteUrl: process.env.MAGI_SITE_URL || "https://prosperity.lat",
    port,
    openAIConfigured: hasOpenAIKey,
    mocksEnabled: process.env.MAGI_ENABLE_MOCKS !== "false",
    storage: {
      analysis: path.relative(paths.root, paths.analysis),
      logs: path.relative(paths.root, paths.logs),
      errors: path.relative(paths.root, paths.errors),
    },
    futureConnections: [
      "Bot A",
      "Bot B",
      "Bot C",
      "Melchor",
      "Baltasar",
      "Gaspar",
      "CEO-MAGI",
    ],
  };
}

export function buildDashboardSnapshot({ uptimeSeconds, port, hasOpenAIKey }) {
  const signals = loadLatestSignals();
  const analysisStatus = loadAnalysisStatus();
  const logs = loadRecentLogs();

  return {
    overview: computeOverview(signals, analysisStatus, uptimeSeconds),
    modules: computeModules(signals, analysisStatus),
    signals,
    logs,
    settings: buildSettingsSnapshot(port, hasOpenAIKey),
    analysisStatus,
  };
}
