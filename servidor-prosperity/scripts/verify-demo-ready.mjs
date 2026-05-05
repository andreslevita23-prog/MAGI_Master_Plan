import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const port = 3120;
const baseUrl = `http://127.0.0.1:${port}`;
const root = process.cwd();
const today = new Date().toISOString().slice(0, 10);
const auditJournal = path.join(root, "data/audit/decisions", today, "magi_decisions.jsonl");
const originalAuditJournal = fs.existsSync(auditJournal) ? fs.readFileSync(auditJournal, "utf8") : null;

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForHealth() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(`${baseUrl}/health`);
      if (response.ok) return response.json();
    } catch {
      await wait(250);
    }
  }
  throw new Error("Servidor demo no respondio /health.");
}

async function postAnalysis(payload) {
  const response = await fetch(`${baseUrl}/analisis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return { response, body: await response.json() };
}

function buildV2Payload() {
  return {
    schema_version: "magi.snapshot.v2",
    snapshot_id: "VERIFYDEMO_M5_2026-05-05T12:00:00_live",
    symbol: "VERIFYDEMO",
    source_mode: "live",
    trigger_type: "closed_bar",
    timestamp: "2026-05-05T12:00:01Z",
    anchor_bar_timestamp: "2026-05-05T12:00:00",
    bar_timestamp: "2026-05-05T12:00:00",
    anchor_timeframe: "M5",
    primary_timeframe: "H1",
    anchor_open: 1.1,
    anchor_high: 1.105,
    anchor_low: 1.095,
    anchor_close: 1.102,
    market_structure: "trend",
    structure_direction: "bullish",
    support_levels: [1.095, 1.09],
    resistance_levels: [1.105, 1.11],
    ema_20: 1.101,
    ema_50: 1.099,
    ema_200: 1.09,
    rsi_14: 61.5,
    momentum: "bullish",
    current_price: 1.102,
    recent_range: 0.01,
    spread_pips: 0.4,
    active_session: "london",
    mtf_alignment_status: "ok",
    mtf_alignment_warnings: "",
    mtf_data_source_status: "OK",
    allowed_actions: ["open", "hold"],
    account: { balance: 10000, equity: 10000, daily_drawdown_percent: 0, risk_percent_per_trade: 0 },
    news: [],
    operational_notes: "risk placeholders pending",
    position: { has_open_position: false, open_positions_count: 0 },
    gaspar_context: {
      is_available: true,
      proposed_direction: "BUY",
      higher_timeframe_confluence: {
        h4_structure: "bullish",
        d1_structure: "bullish",
        directional_alignment: "aligned",
      },
      price_structure_position: {
        distance_to_d1_support: 0.01,
        distance_to_d1_resistance: 0.02,
        position_in_d1_range: 0.33,
        near_key_level: false,
      },
      timing_quality: {
        active_session: "london",
        daily_atr_consumed_pct: 0.4,
        available_range_to_next_level: 0.02,
        h4_candle_pattern: "none",
      },
      day_context: {
        day_of_week: "tuesday",
        d1_volatility_vs_20d_avg: 0.9,
        current_d1_range_vs_atr: 0.4,
      },
    },
    features: [
      { timeframe: "H1", market_structure: "trend", structure_direction: "bullish", ema_20: 1.101, ema_50: 1.099, ema_200: 1.09, rsi_14: 61.5, recent_range: 0.01 },
      { timeframe: "H4", market_structure: "trend", structure_direction: "bullish", ema_20: 1.1, ema_50: 1.098, ema_200: 1.09, rsi_14: 62, recent_range: 0.02 },
    ],
    validation: { is_valid: true, issues: [] },
  };
}

function cleanup() {
  for (const relative of [
    "data/analysis/VERIFYDEMO.json",
    "data/execution/VERIFYDEMO.json",
    "data/snapshots/legacy/VERIFYDEMO_M5_2026-05-05T12-00-00_live.json",
    "data/snapshots/normalized/VERIFYDEMO_M5_2026-05-05T12-00-00_live.json",
  ]) {
    const filePath = path.join(root, relative);
    if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
  }
  const votesDir = path.join(root, "data/votes/melchor");
  if (fs.existsSync(votesDir)) {
    for (const fileName of fs.readdirSync(votesDir)) {
      if (fileName.includes("VERIFYDEMO")) fs.unlinkSync(path.join(votesDir, fileName));
    }
  }
}

function restoreAuditJournal() {
  if (originalAuditJournal === null) {
    if (fs.existsSync(auditJournal)) fs.unlinkSync(auditJournal);
    return;
  }
  fs.mkdirSync(path.dirname(auditJournal), { recursive: true });
  fs.writeFileSync(auditJournal, originalAuditJournal, "utf8");
}

cleanup();

const indexSource = fs.readFileSync(path.join(root, "src/server/index.js"), "utf8");
assert.match(indexSource, /MAGI backend listo para conexion MT5/);
assert.match(indexSource, /Esperando conexion desde MT5/);

const server = spawn("node", ["src/server/index.js"], {
  cwd: root,
  env: { ...process.env, PORT: String(port), DEMO_MODE: "true" },
  stdio: "ignore",
});

try {
  const health = await waitForHealth();
  assert.equal(health.status, "ok");
  assert.equal(health.services.snapshots, true);
  assert.equal(health.services.execution, true);
  assert.equal(health.services.audit, true);

  for (const relativeDir of ["data", "data/audit", "data/snapshots", "data/execution"]) {
    const dirPath = path.join(root, relativeDir);
    assert.equal(fs.existsSync(dirPath), true, `${relativeDir} debe existir.`);
    const probe = path.join(dirPath, `.verify-demo-${Date.now()}`);
    fs.writeFileSync(probe, "ok", "utf8");
    fs.unlinkSync(probe);
  }

  const posted = await postAnalysis(buildV2Payload());
  assert.equal(posted.response.ok, true);
  assert.equal(posted.body.details.symbol, "VERIFYDEMO");
  assert.equal(typeof posted.body.decision_id, "string");
  assert.equal(typeof posted.body.snapshot_id, "string");
  assert.equal(typeof posted.body.decision_time, "string");
  assert.match(posted.body.details.comment, /^MAGI\|/);

  const getPayload = await fetch(`${baseUrl}/analisis/VERIFYDEMO`).then((response) => response.json());
  assert.equal(getPayload.decision_id, posted.body.decision_id);

  const auditText = fs.existsSync(auditJournal) ? fs.readFileSync(auditJournal, "utf8") : "";
  assert.match(auditText, new RegExp(posted.body.decision_id));

  console.log(JSON.stringify({
    ok: true,
    checks: [
      "Backend levanta sin errores",
      "/health responde OK",
      "Carpetas requeridas existen y son escribibles",
      "Logs de arranque configurados",
      "Test end-to-end pasa",
    ],
    health,
  }, null, 2));
} finally {
  server.kill();
  cleanup();
  restoreAuditJournal();
}
