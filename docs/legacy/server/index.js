// index.js - Servidor Prosperity actualizado

import express from "express";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";
import OpenAI from "openai";
import logger from "./logger.mjs";
import systemPrompt from "./prompt.js";
import { fileURLToPath } from "url";

dotenv.config();
const app = express();
const port = 3000;
const carpetaAnalisis = "./analisis";
const carpetaErrores = "./errores";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

if (!fs.existsSync(carpetaAnalisis)) fs.mkdirSync(carpetaAnalisis);
if (!fs.existsSync(carpetaErrores)) fs.mkdirSync(carpetaErrores);

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
app.use(express.text({ type: "*/*" }));

let statusBySymbol = {};

// Servir archivos estáticos desde carpeta raíz (para acceder al logo directamente)
app.use(express.static(__dirname));

app.get("/api/status", (req, res) => {
  const formattedStatus = {};
  for (const [symbol, data] of Object.entries(statusBySymbol)) {
    formattedStatus[symbol] = {
      comment: data.details?.comment || "-",
      timestamp: data.timestamp || new Date().toISOString(),
      decision: data.action || "-",
      order_type: data.details?.order_type || "-",
      entry_price: data.details?.entry_price || "-",
      stop_loss: data.details?.stop_loss || "-",
      take_profit: data.details?.take_profit || "-"
    };
  }
  res.json(formattedStatus);
});

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "landing.html"));
});

app.get("/dashboard.html", (req, res) => {
  res.sendFile(path.join(__dirname, "dashboard.html"));
});

app.post("/analisis", async (req, res) => {
  try {
    const cleanText = req.body.replace(/[\u0000-\u001F\u007F-\u009F]/g, "").trim();
    const json = JSON.parse(cleanText);

    logger.logBotA(json);

    const chatResponse = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: JSON.stringify(json) }
      ],
      temperature: 0.3
    });

    let respuesta = chatResponse.choices[0].message.content;
    if (respuesta.startsWith("```json")) {
      respuesta = respuesta.replace(/^```json/, "").replace(/```$/, "").trim();
    }

    try {
      const parsed = JSON.parse(respuesta);
      if (!parsed.details) parsed.details = {};
      if (!parsed.details.symbol && json.pair) parsed.details.symbol = json.pair;
      if (parsed.action === "open" && !parsed.details.order_type) parsed.details.order_type = "buy";

      logger.logAPI({ respuesta_raw: respuesta });
      logger.logBotB(parsed);

      const symbol = parsed.details?.symbol?.toUpperCase() || json.pair || "unknown";
      const filepath = path.join(carpetaAnalisis, `${symbol}.json`);
      fs.writeFileSync(filepath, JSON.stringify(parsed, null, 2));

      statusBySymbol[symbol] = parsed;

      console.log(`✅ Análisis guardado para ${symbol}`);
      console.log("🧠 Estado actualizado para", symbol, "→", statusBySymbol[symbol]);
      res.send(parsed);

    } catch (jsonError) {
      const errorPath = path.join(carpetaErrores, `error_${Date.now()}.txt`);
      fs.writeFileSync(errorPath, respuesta);
      console.error("❌ JSON inválido recibido:", respuesta);
      throw jsonError;
    }

  } catch (error) {
    console.error("❌ Error procesando análisis:", error);
    res.status(500).send({
      error: "Respuesta de IA no es JSON válido o error de OpenAI",
      message: error.message,
      stack: error.stack
    });
  }
});

app.get("/analisis/:symbol", (req, res) => {
  const symbol = req.params.symbol.toUpperCase();
  const filepath = path.join(carpetaAnalisis, `${symbol}.json`);

  if (!fs.existsSync(filepath)) {
    return res.status(404).send({
      action: "hold",
      details: {
        symbol: "none",
        order_type: null,
        entry_price: null,
        stop_loss: null,
        take_profit: null
      }
    });
  }

  try {
    const data = fs.readFileSync(filepath, "utf-8");
    res.send(JSON.parse(data));
  } catch (err) {
    console.error("❌ Error al leer archivo:", err);
    res.status(500).send({ error: "No se pudo leer el análisis del símbolo." });
  }
});

app.listen(port, () => {
  console.log(`🚀 Servidor local escuchando en http://localhost:${port}`);
});
