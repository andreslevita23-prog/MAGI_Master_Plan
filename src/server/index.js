import express from "express";
import dotenv from "dotenv";
import fs from "fs";
import path from "path";
import OpenAI from "openai";
import { paths } from "./config/paths.js";
import prompt from "./prompt.js";
import { buildDashboardSnapshot } from "./services/dashboard.js";
import { logger } from "./services/logger.js";
import {
  ensureProjectDirectories,
  readJson,
  writeJson,
} from "./services/storage.js";

dotenv.config();
ensureProjectDirectories();

const app = express();
const port = Number(process.env.PORT || 3000);
const siteUrl = process.env.MAGI_SITE_URL || "https://prosperity.lat";
const hasOpenAIKey = Boolean(process.env.OPENAI_API_KEY);
const allowMocks = process.env.MAGI_ENABLE_MOCKS !== "false";
const openai = hasOpenAIKey
  ? new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
  : null;

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

function normalizeDecision(parsed, sourcePayload = {}) {
  const symbol = (parsed.details?.symbol || sourcePayload.pair || "unknown").toUpperCase();

  return {
    action: parsed.action || "hold",
    id_operacion:
      parsed.id_operacion ||
      sourcePayload.id_operacion ||
      `${new Date().toISOString()}_${symbol}`,
    details: {
      symbol,
      order_type: parsed.details?.order_type || "",
      entry_price: Number(parsed.details?.entry_price || 0),
      stop_loss: Number(parsed.details?.stop_loss || 0),
      take_profit: Number(parsed.details?.take_profit || 0),
      lot_size: Number(parsed.details?.lot_size || 0),
      comment: parsed.details?.comment || "Decision sin comentario.",
    },
    timestamp: new Date().toISOString(),
  };
}

function buildMockDecision(payload) {
  return normalizeDecision(
    {
      action: "hold",
      details: {
        symbol: payload?.pair || "unknown",
        comment:
          "Modo local activo: se devolvio una decision mock mientras se completa la integracion con IA.",
      },
    },
    payload,
  );
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
  res.json(
    buildDashboardSnapshot({
      uptimeSeconds: Math.round(process.uptime()),
      port,
      hasOpenAIKey,
    }).logs,
  );
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

    let decision;

    if (!openai) {
      decision = buildMockDecision(payload);
    } else {
      try {
        const completion = await openai.chat.completions.create({
          model: process.env.MAGI_OPENAI_MODEL || "gpt-4o-mini",
          messages: [
            { role: "system", content: prompt },
            { role: "user", content: JSON.stringify(payload) },
          ],
          temperature: 0.3,
        });

        let content = completion.choices[0]?.message?.content || "";
        if (content.startsWith("```json")) {
          content = content.replace(/^```json/, "").replace(/```$/, "").trim();
        }

        try {
          decision = normalizeDecision(JSON.parse(content), payload);
          logger.logAPI({ respuesta_raw: content });
        } catch (parseError) {
          if (!allowMocks) {
            throw parseError;
          }

          const errorPath = path.join(paths.errors, `error_${Date.now()}.txt`);
          fs.writeFileSync(errorPath, content, "utf8");
          decision = buildMockDecision(payload);
        }
      } catch (apiError) {
        if (!allowMocks) {
          throw apiError;
        }

        logger.logAPI({ error: apiError.message, fallback: "mock_decision" });
        decision = buildMockDecision(payload);
      }
    }

    logger.logBotB(decision);
    persistDecision(decision);
    statusBySymbol[decision.details.symbol] = decision;

    res.json(decision);
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
