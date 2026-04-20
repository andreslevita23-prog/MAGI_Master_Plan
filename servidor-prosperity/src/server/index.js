import express from "express";
import dotenv from "dotenv";
import fs from "fs";
import path from "path";
import { paths } from "./config/paths.js";
import { buildDashboardSnapshot } from "./services/dashboard.js";
import { mapMvpDecisionToBotBResponse } from "./services/adapters/mt5/bot-b-response-mapper.js";
import {
  getConnectorById,
  listConnectors,
} from "./services/connectors/registry.js";
import { adaptBotALegacySnapshot } from "./services/adapters/mt5/bot-a-legacy-adapter.js";
import { getCaseById, listCases } from "./services/cases/case-query.service.js";
import { listExecutionStates } from "./services/execution/execution-query.service.js";
import { persistExecutionState } from "./services/execution/execution-store.service.js";
import { logger } from "./services/logger.js";
import { buildLogsSnapshot } from "./services/logs/log-query.service.js";
import { evaluateMvpDecision } from "./services/orchestrator/mvp-decision-engine.js";
import {
  getSnapshotDetail,
  listRecentSnapshots,
} from "./services/snapshots/snapshot-query.service.js";
import { persistSnapshotArtifacts } from "./services/snapshots/snapshot-store.service.js";
import {
  ensureProjectDirectories,
  readJson,
  writeJson,
} from "./services/storage.js";
import { buildOverviewSnapshot } from "./services/system/system-status.service.js";
import { validateLegacySnapshot } from "./services/validation/snapshot-validator.js";

dotenv.config();
ensureProjectDirectories();

const app = express();
const port = Number(process.env.PORT || 3000);
const siteUrl = process.env.MAGI_SITE_URL || "https://prosperity.lat";
const hasOpenAIKey = Boolean(process.env.OPENAI_API_KEY);

app.use(express.json({ limit: "1mb" }));
app.use(express.text({ type: ["text/*", "application/octet-stream"] }));
app.use("/assets", express.static(paths.clientAssets));
app.use("/static", express.static(paths.client));

function safeJsonParse(rawInput) {
  if (typeof rawInput === "object" && rawInput !== null) {
    return rawInput;
  }

  const cleanText = String(rawInput || "")
    .replace(/[\u0000-\u001F\u007F-\u009F]/g, "")
    .trim();

  return JSON.parse(cleanText);
}

function persistDecision(decision) {
  const outputPath = path.join(paths.analysis, `${decision.details.symbol}.json`);
  writeJson(outputPath, decision);
  return outputPath;
}

function loadStatusBySymbol() {
  const entries = fs.existsSync(paths.analysis)
    ? fs.readdirSync(paths.analysis).filter((fileName) => fileName.endsWith(".json"))
    : [];

  return entries.reduce((accumulator, fileName) => {
    const symbol = path.basename(fileName, ".json");
    const payload = readJson(path.join(paths.analysis, fileName));

    if (payload) {
      accumulator[symbol] = payload;
    }

    return accumulator;
  }, {});
}

function mapStatusForApi(statusBySymbol) {
  return Object.fromEntries(
    Object.entries(statusBySymbol).map(([symbol, entry]) => [
      symbol,
      {
        symbol,
        comment: entry.details?.comment || "-",
        timestamp: entry.timestamp || new Date().toISOString(),
        decision: entry.action || "-",
        order_type: entry.details?.order_type || "-",
        entry_price: entry.details?.entry_price || 0,
        stop_loss: entry.details?.stop_loss || 0,
        take_profit: entry.details?.take_profit || 0,
        lot_size: entry.details?.lot_size || 0,
      },
    ]),
  );
}

let statusBySymbol = loadStatusBySymbol();

app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    service: "prosperity-magi",
    uptimeSeconds: Math.round(process.uptime()),
    timestamp: new Date().toISOString(),
  });
});

app.get("/", (_req, res) => {
  res.sendFile(path.join(paths.client, "index.html"));
});

app.get("/dashboard", (_req, res) => {
  res.sendFile(path.join(paths.client, "dashboard.html"));
});

app.get("/dashboard.html", (_req, res) => {
  res.redirect("/dashboard");
});

app.get("/api/status", (_req, res) => {
  res.json(mapStatusForApi(statusBySymbol));
});

app.get("/api/overview", (_req, res) => {
  res.json(
    buildOverviewSnapshot({
      uptimeSeconds: Math.round(process.uptime()),
      hasOpenAIKey,
    }),
  );
});

app.get("/api/snapshots", (req, res) => {
  const limit = Math.max(1, Math.min(100, Number(req.query.limit) || 20));

  res.json({
    items: listRecentSnapshots(limit),
    total_returned: Math.min(limit, listRecentSnapshots(limit).length),
  });
});

app.get("/api/snapshots/:id", (req, res) => {
  const snapshot = getSnapshotDetail(req.params.id);

  if (!snapshot) {
    res.status(404).json({ error: "Snapshot no encontrado." });
    return;
  }

  res.json(snapshot);
});

app.get("/api/cases", (_req, res) => {
  res.json({
    items: listCases(),
  });
});

app.get("/api/cases/:id", (req, res) => {
  const item = getCaseById(req.params.id);

  if (!item) {
    res.status(404).json({ error: "Caso no encontrado." });
    return;
  }

  res.json(item);
});

app.get("/api/execution", (_req, res) => {
  res.json({
    items: listExecutionStates(),
  });
});

app.get("/api/dashboard", (_req, res) => {
  res.json(
    buildDashboardSnapshot({
      uptimeSeconds: Math.round(process.uptime()),
      port,
      hasOpenAIKey,
    }),
  );
});

app.get("/api/signals", (_req, res) => {
  res.json(
    buildDashboardSnapshot({
      uptimeSeconds: Math.round(process.uptime()),
      port,
      hasOpenAIKey,
    }).signals,
  );
});

app.get("/api/modules", (_req, res) => {
  res.json(
    buildDashboardSnapshot({
      uptimeSeconds: Math.round(process.uptime()),
      port,
      hasOpenAIKey,
    }).modules,
  );
});

app.get("/api/logs", (_req, res) => {
  res.json(buildLogsSnapshot());
});

app.get("/api/settings", (_req, res) => {
  res.json(
    buildDashboardSnapshot({
      uptimeSeconds: Math.round(process.uptime()),
      port,
      hasOpenAIKey,
    }).settings,
  );
});

app.get("/api/connectors", (_req, res) => {
  res.json(listConnectors());
});

app.get("/api/connectors/:id", (req, res) => {
  const connector = getConnectorById(req.params.id);

  if (!connector) {
    res.status(404).json({ error: "Connector no encontrado." });
    return;
  }

  res.json(connector);
});

app.get("/analisis/:symbol", (req, res) => {
  const symbol = req.params.symbol.toUpperCase();
  const payload = readJson(path.join(paths.analysis, `${symbol}.json`), {
    action: "hold",
    id_operacion: `${symbol}_missing`,
    details: {
      symbol,
      order_type: "",
      entry_price: 0,
      stop_loss: 0,
      take_profit: 0,
      lot_size: 0,
      comment: "No existe analisis persistido para este simbolo.",
    },
  });

  res.json(payload);
});

app.post("/analisis", async (req, res) => {
  try {
    const payload = safeJsonParse(req.body && Object.keys(req.body).length ? req.body : req.body || req.text || req.rawBody || "");
    logger.logBotA(payload);

    const validation = validateLegacySnapshot(payload);
    const snapshotData = adaptBotALegacySnapshot(payload, validation);
    const snapshotArtifacts = persistSnapshotArtifacts(snapshotData);

    logger.logSystem({
      event: "snapshot_received",
      snapshot_id: snapshotArtifacts.snapshot_id,
      symbol: payload?.pair || "unknown",
      is_valid: validation.is_valid,
      issues: validation.issues,
    });

    const mvpDecision = evaluateMvpDecision(snapshotData.normalized);
    const botBResponse = mapMvpDecisionToBotBResponse(mvpDecision, payload);
    const executionState = persistExecutionState({
      decision: mvpDecision,
      response: botBResponse,
    });

    logger.logSystem({
      event: "mvp_decision_ready",
      snapshot_id: mvpDecision.snapshot_id,
      symbol: mvpDecision.symbol,
      case_state: mvpDecision.case_state,
      case_type: mvpDecision.case_type,
      final_action: mvpDecision.final_action,
      execution_file: executionState.file_path,
    });

    logger.logBotB(botBResponse);
    persistDecision(botBResponse);
    statusBySymbol[botBResponse.details.symbol] = botBResponse;

    res.json(botBResponse);
  } catch (error) {
    res.status(500).json({
      error: "No fue posible procesar el analisis.",
      message: error.message,
    });
  }
});

app.post("/", (req, res) => {
  res.status(307).json({
    message: "Use POST /analisis para enviar entradas al motor.",
    siteUrl,
  });
});

app.listen(port, () => {
  console.log(`Prosperity / MAGI escuchando en http://localhost:${port}`);
  console.log(`Dashboard listo en http://localhost:${port}/dashboard`);
  console.log(`Destino de despliegue previsto: ${siteUrl}`);
});
