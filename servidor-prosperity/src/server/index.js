import express from "express";
import dotenv from "dotenv";
import crypto from "crypto";
import fs from "fs";
import path from "path";
import { paths } from "./config/paths.js";
import { buildDashboardSnapshot } from "./services/dashboard.js";
import { mapMvpDecisionToBotBResponse } from "./services/adapters/mt5/bot-b-response-mapper.js";
import {
  buildDecisionAuditRecord,
  ensureDecisionAuditIdentity,
  persistDecisionAuditRecord,
} from "./services/audit/decision-audit.service.js";
import { getBotCAuditSnapshot } from "./services/audit/bot-c-audit.service.js";
import {
  getConnectorById,
  listConnectors,
} from "./services/connectors/registry.js";
import { adaptBotALegacySnapshot } from "./services/adapters/mt5/bot-a-legacy-adapter.js";
import {
  adaptBotASnapshotV2,
  isSnapshotV2Payload,
  validateSnapshotV2Payload,
} from "./services/adapters/mt5/snapshot-v2-adapter.js";
import { getCaseById, listCases } from "./services/cases/case-query.service.js";
import { listExecutionStates } from "./services/execution/execution-query.service.js";
import { persistExecutionState } from "./services/execution/execution-store.service.js";
import { logger } from "./services/logger.js";
import {
  applyDemoLotSizing,
  getDemoGovernanceConfig,
  getOperationalState,
  persistOperationalState,
} from "./services/governance/operational-governance.service.js";
import { buildLogsSnapshot } from "./services/logs/log-query.service.js";
import { evaluateMvpDecision } from "./services/orchestrator/mvp-decision-engine.js";
import {
  buildPlatformSummary,
  listBotAEvents,
  listBotBEvents,
  listBotCEvents,
  listMagiDecisions,
} from "./services/platform/platform-records.service.js";
import { getCurrentPositionSnapshot } from "./services/positions/current-position.service.js";
import {
  getSnapshotDetail,
  listRecentSnapshots,
} from "./services/snapshots/snapshot-query.service.js";
import { persistSnapshotArtifacts } from "./services/snapshots/snapshot-store.service.js";
import {
  buildStorageHealth,
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
const demoMode = String(process.env.DEMO_MODE || "").toLowerCase() === "true";
const readOnlyDashboard = String(process.env.READ_ONLY_DASHBOARD || "").toLowerCase() === "true";
const dashboardAuthToken = process.env.DASHBOARD_AUTH_TOKEN || "";
const dashboardUsersJson = process.env.DASHBOARD_USERS_JSON || "";
const dashboardBasicUser = process.env.DASHBOARD_BASIC_USER || "";
const dashboardBasicPassword = process.env.DASHBOARD_BASIC_PASSWORD || "";
const serverStartedAt = new Date();
const readOnlyAllowedPrefixes = [
  "/",
  "/dashboard",
  "/dashboard.html",
  "/bot_A",
  "/bot_B",
  "/bot_C",
  "/magi",
  "/assets/",
  "/static/",
  "/api/overview",
  "/api/snapshots",
  "/api/execution",
  "/api/governance",
  "/api/position/current",
  "/api/platform/summary",
  "/api/bot-a/events",
  "/api/magi/decisions",
  "/api/bot-b/events",
  "/api/bot-c/events",
  "/api/logs",
  "/api/bot-c/audit",
  "/health",
];

function parseDashboardUsers(rawValue) {
  if (!rawValue.trim()) {
    return { users: [], error: null };
  }

  try {
    const parsed = JSON.parse(rawValue);
    if (!Array.isArray(parsed)) {
      return { users: [], error: "DASHBOARD_USERS_JSON debe ser un arreglo JSON." };
    }

    const users = parsed
      .map((entry) => ({
        user: String(entry?.user || ""),
        password: String(entry?.password || ""),
      }))
      .filter((entry) => entry.user && entry.password);

    return { users, error: users.length ? null : "DASHBOARD_USERS_JSON no contiene usuarios validos." };
  } catch (error) {
    return { users: [], error: `DASHBOARD_USERS_JSON invalido: ${error.message}` };
  }
}

const dashboardUsersConfig = parseDashboardUsers(dashboardUsersJson);

function hasDashboardAuthConfigured() {
  return Boolean(dashboardAuthToken || dashboardUsersConfig.users.length || (dashboardBasicUser && dashboardBasicPassword));
}

function timingSafeEqualText(left, right) {
  const leftBuffer = Buffer.from(String(left || ""));
  const rightBuffer = Buffer.from(String(right || ""));
  return leftBuffer.length === rightBuffer.length && crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function isReadOnlyAllowedPath(requestPath) {
  return readOnlyAllowedPrefixes.some((allowedPath) => {
    if (allowedPath === "/") {
      return requestPath === "/";
    }
    if (allowedPath.endsWith("/")) {
      return requestPath.startsWith(allowedPath);
    }
    return requestPath === allowedPath;
  });
}

function cookieValue(req, name) {
  const cookies = String(req.get("cookie") || "").split(";");
  for (const cookie of cookies) {
    const [rawKey, ...rawValue] = cookie.trim().split("=");
    if (rawKey === name) {
      return decodeURIComponent(rawValue.join("="));
    }
  }
  return "";
}

function dashboardAuthMethod(req) {
  const authorization = req.get("authorization") || "";
  const bearerPrefix = "Bearer ";

  if (dashboardAuthToken && authorization.startsWith(bearerPrefix)) {
    return timingSafeEqualText(authorization.slice(bearerPrefix.length), dashboardAuthToken) ? "bearer" : null;
  }

  const token = req.query.token || req.get("x-dashboard-token") || cookieValue(req, "magi_dashboard_token");
  if (dashboardAuthToken && token) {
    return timingSafeEqualText(token, dashboardAuthToken) ? "token" : null;
  }

  if (authorization.startsWith("Basic ")) {
    const decoded = Buffer.from(authorization.slice("Basic ".length), "base64").toString("utf8");
    const separatorIndex = decoded.indexOf(":");
    const user = separatorIndex >= 0 ? decoded.slice(0, separatorIndex) : "";
    const password = separatorIndex >= 0 ? decoded.slice(separatorIndex + 1) : "";
    const matchesMultiUser = dashboardUsersConfig.users.some(
      (entry) => timingSafeEqualText(user, entry.user) && timingSafeEqualText(password, entry.password),
    );
    const matchesLegacyUser = Boolean(dashboardBasicUser && dashboardBasicPassword)
      && timingSafeEqualText(user, dashboardBasicUser)
      && timingSafeEqualText(password, dashboardBasicPassword);

    return matchesMultiUser || matchesLegacyUser ? "basic" : null;
  }

  return null;
}

function requireDashboardAuth(req, res, next) {
  if (!readOnlyDashboard) {
    next();
    return;
  }

  if (!["GET", "HEAD", "OPTIONS"].includes(req.method) || !isReadOnlyAllowedPath(req.path)) {
    res.status(404).json({ error: "Ruta no disponible en modo dashboard solo lectura." });
    return;
  }

  if (!hasDashboardAuthConfigured()) {
    res.status(503).json({
      error: "Dashboard privado sin credenciales configuradas.",
      message: "Defina DASHBOARD_USERS_JSON, DASHBOARD_AUTH_TOKEN o DASHBOARD_BASIC_USER/DASHBOARD_BASIC_PASSWORD.",
    });
    return;
  }

  if (dashboardUsersConfig.error) {
    res.status(503).json({
      error: "Configuracion de usuarios del dashboard invalida.",
      message: dashboardUsersConfig.error,
    });
    return;
  }

  res.set("X-Robots-Tag", "noindex, nofollow");
  res.set("X-Frame-Options", "DENY");
  res.set("Cross-Origin-Resource-Policy", "same-origin");
  res.set("Referrer-Policy", "no-referrer");

  const authMethod = dashboardAuthMethod(req);
  if (authMethod) {
    if (authMethod === "token" && req.query.token) {
      res.cookie("magi_dashboard_token", String(req.query.token), {
        httpOnly: true,
        sameSite: "strict",
        secure: req.secure || req.get("x-forwarded-proto") === "https",
      });
    }
    next();
    return;
  }

  res.set("WWW-Authenticate", 'Basic realm="MAGI Dashboard", charset="UTF-8"');
  res.status(401).json({ error: "Autenticacion requerida." });
}

function captureRawBody(req, _res, buffer) {
  req.rawBody = buffer?.length ? buffer.toString("utf8") : "";
}

function bodyPreview(req) {
  const rawBody = typeof req.rawBody === "string" ? req.rawBody : "";
  if (rawBody) {
    return rawBody.replace(/[\u0000-\u001F\u007F-\u009F]/g, "").slice(0, 500);
  }

  if (typeof req.body === "string") {
    return req.body.replace(/[\u0000-\u001F\u007F-\u009F]/g, "").slice(0, 500);
  }

  if (req.body && typeof req.body === "object") {
    return JSON.stringify(req.body).slice(0, 500);
  }

  return "";
}

function logPostAnalisisError(req, error, extra = {}) {
  const payload = {
    event: "post_analisis_error",
    message: error.message,
    content_type: req.get("content-type") || null,
    body_preview: bodyPreview(req),
    ...extra,
  };

  console.error(
    `[POST /analisis][error] message=${payload.message} content_type=${payload.content_type || "n/a"} body_preview=${payload.body_preview}`,
  );
  logger.logSystem(payload);
}

app.use(requireDashboardAuth);
app.use(express.json({ limit: "1mb", verify: captureRawBody }));
app.use(express.text({ type: ["text/*", "application/octet-stream"], verify: captureRawBody }));
app.use((error, req, res, next) => {
  if (error instanceof SyntaxError && "body" in error) {
    logPostAnalisisError(req, error, { parser: "express.json" });
    res.status(400).json({
      error: "JSON invalido en POST /analisis.",
      message: error.message,
    });
    return;
  }

  next(error);
});
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

function adaptBotAPayload(payload) {
  if (isSnapshotV2Payload(payload)) {
    const validation = validateSnapshotV2Payload(payload);
    return {
      validation,
      snapshotData: adaptBotASnapshotV2(payload, validation),
      contract: "magi.snapshot.v2",
      symbol: payload.symbol,
    };
  }

  const validation = validateLegacySnapshot(payload);
  return {
    validation,
    snapshotData: adaptBotALegacySnapshot(payload, validation),
    contract: validation.contract,
    symbol: payload?.pair,
  };
}

let statusBySymbol = loadStatusBySymbol();

function latestSnapshotSummary() {
  return listRecentSnapshots(1)[0] || null;
}

function logStartupSummary() {
  const baseUrl = `http://localhost:${port}`;
  const latestSnapshot = latestSnapshotSummary();
  const storageHealth = buildStorageHealth();

  console.log("MAGI backend demo");
  console.log(`Puerto activo: ${port}`);
  console.log(`URL base: ${baseUrl}`);
  console.log(`Ruta de datos: ${paths.data}`);
  console.log(`Endpoint Bot A: ${baseUrl}/analisis`);
  console.log(`Overview: ${baseUrl}/api/overview`);
  console.log(`Snapshots: ${baseUrl}/api/snapshots`);
  console.log(`Journal audit activo: ${storageHealth.audit ? "si" : "no"} (${paths.auditDecisions})`);
  console.log(
    `Ultimo snapshot recibido: ${
      latestSnapshot
        ? `${latestSnapshot.symbol} | ${latestSnapshot.snapshot_id} | ${latestSnapshot.timestamp || "sin timestamp"}`
        : "ninguno"
    }`,
  );
  console.log(`DEMO_MODE: ${demoMode ? "true" : "false"}`);
  const governanceConfig = getDemoGovernanceConfig({ demoMode });
  console.log(`MAGI demo lot size: ${governanceConfig.demo_lot_size}`);
  console.log(`MAGI demo mode until: ${governanceConfig.demo_mode_until}`);
  console.log(`READ_ONLY_DASHBOARD: ${readOnlyDashboard ? "true" : "false"}`);
  console.log("MAGI backend listo para conexion MT5");
  console.log("Esperando conexion desde MT5...");
}

if (process.argv.includes("--print-startup-check")) {
  logStartupSummary();
  process.exit(0);
}

function logIncomingSnapshot({ contract, symbol, snapshotData, validation }) {
  const normalized = snapshotData.normalized || {};
  const warnings = normalized.validation?.adapter_warnings || [];
  const riskWarnings = [];
  if (demoMode) {
    if (normalized.account?.daily_drawdown_percent === 0) {
      riskWarnings.push("daily_drawdown_percent=0.0 placeholder");
    }
    if (normalized.account?.risk_percent_per_trade === 0) {
      riskWarnings.push("risk_percent_per_trade=0.0 placeholder");
    }
  }

  console.log(
    `[BotA] contract=${contract} symbol=${symbol || normalized.symbol || "unknown"} snapshot_id=${
      normalized.snapshot_id || "n/a"
    } source_mode=${normalized.source?.source_mode || normalized.raw?.source_mode || "n/a"} valid=${
      validation.is_valid
    }`,
  );

  for (const warning of [...warnings, ...riskWarnings]) {
    console.log(`[BotA][warning] ${warning}`);
  }
}

function logDecisionReady({ decision, auditFile }) {
  console.log(
    `[MAGI] decision_id=${decision.decision_id} action=${decision.final_action} symbol=${decision.symbol} audit_journal=${
      auditFile ? "saved" : "missing"
    }`,
  );

  if (demoMode) {
    console.log(`[MAGI][demo] reason=${decision.reason || "sin razon"}`);
    console.log(
      `[MAGI][governance] lot_size=${decision.current_lot_size ?? decision.lot_size ?? 0} safe_mode=${
        decision.risk_state?.safe_mode_active || false
      } cluster_sl=${decision.cluster_state?.consecutive_sl ?? 0} shadow_friday=${
        decision.shadow_guardrails?.friday_guardrail_would_block || false
      } shadow_2sl=${decision.shadow_guardrails?.cluster_2sl_would_block || false}`,
    );
  }
}

app.get("/health", (_req, res) => {
  const services = buildStorageHealth();
  res.json({
    status: "ok",
    timestamp: new Date().toISOString(),
    started_at: serverStartedAt.toISOString(),
    uptime_seconds: Math.round(process.uptime()),
    services: {
      snapshots: Boolean(services.snapshots),
      execution: Boolean(services.execution),
      audit: Boolean(services.audit),
    },
  });
});

app.get("/", (_req, res) => {
  if (readOnlyDashboard) {
    res.redirect("/dashboard");
    return;
  }

  res.sendFile(path.join(paths.client, "index.html"));
});

app.get("/dashboard", (_req, res) => {
  res.sendFile(path.join(paths.client, "dashboard.html"));
});

app.get("/dashboard.html", (_req, res) => {
  res.redirect("/dashboard");
});

app.get("/bot_A", (_req, res) => {
  res.sendFile(path.join(paths.client, "bot_A.html"));
});

app.get("/bot_B", (_req, res) => {
  res.sendFile(path.join(paths.client, "bot_B.html"));
});

app.get("/bot_C", (_req, res) => {
  res.sendFile(path.join(paths.client, "bot_C.html"));
});

app.get("/magi", (_req, res) => {
  res.sendFile(path.join(paths.client, "magi.html"));
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
  const items = listRecentSnapshots(limit);

  res.json({
    items,
    latest: items[0] || null,
    total_returned: items.length,
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
  const items = listExecutionStates();

  res.json({
    items,
    latest: items[0] || null,
    total_returned: items.length,
  });
});

app.get("/api/governance", (_req, res) => {
  res.json(getOperationalState());
});

app.get("/api/position/current", (_req, res) => {
  res.json(getCurrentPositionSnapshot());
});

app.get("/api/platform/summary", (_req, res) => {
  res.json(
    buildPlatformSummary({
      range: _req.query.range || "day",
      startedAt: serverStartedAt,
      uptimeSeconds: Math.round(process.uptime()),
    }),
  );
});

app.get("/api/bot-a/events", (req, res) => {
  res.json({
    items: listBotAEvents({ limit: req.query.limit || 100 }),
  });
});

app.get("/api/magi/decisions", (req, res) => {
  res.json({
    items: listMagiDecisions({ limit: req.query.limit || 100 }),
  });
});

app.get("/api/bot-b/events", (req, res) => {
  res.json({
    items: listBotBEvents({ limit: req.query.limit || 100 }),
  });
});

app.get("/api/bot-c/events", (req, res) => {
  res.json(listBotCEvents({ limit: req.query.limit || 100 }));
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

app.get("/api/bot-c/audit", (req, res) => {
  try {
    res.json(
      getBotCAuditSnapshot({
        date: req.query.date || undefined,
        limit: req.query.limit || undefined,
      }),
    );
  } catch (error) {
    res.status(error.statusCode || 500).json({
      error: "No fue posible leer la auditoria de Bot C.",
      message: error.message,
    });
  }
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

    const { validation, snapshotData, contract, symbol } = adaptBotAPayload(payload);
    logIncomingSnapshot({ contract, symbol, snapshotData, validation });
    const snapshotArtifacts = persistSnapshotArtifacts(snapshotData);

    logger.logSystem({
      event: "snapshot_received",
      snapshot_id: snapshotArtifacts.snapshot_id,
      symbol: symbol || "unknown",
      contract,
      is_valid: validation.is_valid,
      issues: validation.issues,
      adapter_warnings: snapshotData.normalized?.validation?.adapter_warnings || [],
    });

    const mvpDecision = applyDemoLotSizing(
      ensureDecisionAuditIdentity(evaluateMvpDecision(snapshotData.normalized)),
      { demoMode },
    );
    const operationalState = persistOperationalState(snapshotData.normalized, mvpDecision);
    const botBResponse = mapMvpDecisionToBotBResponse(mvpDecision, payload);
    const executionState = persistExecutionState({
      decision: mvpDecision,
      response: botBResponse,
    });
    const auditRecord = buildDecisionAuditRecord({
      snapshot: snapshotData.normalized,
      decision: mvpDecision,
      executionPayload: botBResponse,
      snapshotArtifacts,
      executionState,
      status: "sent",
    });
    const decisionAudit = persistDecisionAuditRecord(auditRecord);
    logDecisionReady({ decision: mvpDecision, auditFile: decisionAudit.file_path });

    logger.logSystem({
      event: "mvp_decision_ready",
      snapshot_id: mvpDecision.snapshot_id,
      decision_id: mvpDecision.decision_id,
      symbol: mvpDecision.symbol,
      case_state: mvpDecision.case_state,
      case_type: mvpDecision.case_type,
      final_action: mvpDecision.final_action,
      risk_state: mvpDecision.risk_state || null,
      cluster_state: mvpDecision.cluster_state || null,
      shadow_guardrails: mvpDecision.shadow_guardrails || null,
      current_lot_size: mvpDecision.current_lot_size || mvpDecision.lot_size || 0,
      demo_mode_until: mvpDecision.demo_mode_until || null,
      operational_state_file: operationalState?.stored_at ? "saved" : "saved",
      execution_file: executionState.file_path,
      audit_file: decisionAudit.file_path,
    });

    logger.logBotB(botBResponse);
    persistDecision(botBResponse);
    statusBySymbol[botBResponse.details.symbol] = botBResponse;

    res.json(botBResponse);
  } catch (error) {
    const statusCode = error.statusCode || 500;
    logPostAnalisisError(req, error, {
      status_code: statusCode,
      validation: error.validation || null,
    });
    res.status(statusCode).json({
      error: "No fue posible procesar el analisis.",
      message: error.message,
      validation: error.validation || null,
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
  logStartupSummary();
  console.log(`Dashboard listo en http://localhost:${port}/dashboard`);
  console.log(`Modo dashboard privado: ${readOnlyDashboard ? "solo lectura" : "desactivado"}`);
  console.log(`Destino de despliegue previsto: ${siteUrl}`);
});
