import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const port = 3110;
const baseUrl = `http://127.0.0.1:${port}`;
const root = process.cwd();
const testSymbols = ["E2EV2", "E2ELEG"];
const today = new Date().toISOString().slice(0, 10);
const auditJournal = path.join(root, "data/audit/decisions", today, "magi_decisions.jsonl");
const originalAuditJournal = fs.existsSync(auditJournal)
  ? fs.readFileSync(auditJournal, "utf8")
  : null;

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(`${baseUrl}/health`);
      if (response.ok) {
        return;
      }
    } catch {
      await wait(250);
    }
  }

  throw new Error("Servidor de prueba no respondio en /health.");
}

async function postAnalysis(payload) {
  const response = await fetch(`${baseUrl}/analisis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  return { response, body };
}

async function getJson(pathname) {
  const response = await fetch(`${baseUrl}${pathname}`);
  assert.equal(response.ok, true, `${pathname} debe responder OK.`);
  return response.json();
}

function buildSnapshotV2Payload(overrides = {}) {
  return {
    schema_version: "magi.snapshot.v2",
    snapshot_id: "E2EV2_M5_2026-05-05T12:00:00_live",
    symbol: "E2EV2",
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
    account: {
      balance: 10000,
      equity: 10000,
      daily_drawdown_percent: 0,
      risk_percent_per_trade: 0,
    },
    news: [],
    operational_notes: "daily_drawdown_percent,risk_percent_per_trade,news_context pending",
    position: {
      has_open_position: false,
      open_positions_count: 0,
      position_type: null,
      entry_price: null,
      sl: null,
      tp: null,
      floating_pnl: null,
    },
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
      {
        timeframe: "H1",
        candle_pattern: "none",
        market_structure: "trend",
        structure_direction: "bullish",
        ema_20: 1.101,
        ema_50: 1.099,
        ema_200: 1.09,
        rsi_14: 61.5,
        recent_range: 0.01,
      },
      {
        timeframe: "H4",
        candle_pattern: "none",
        market_structure: "trend",
        structure_direction: "bullish",
        ema_20: 1.1,
        ema_50: 1.098,
        ema_200: 1.09,
        rsi_14: 62,
        recent_range: 0.02,
      },
    ],
    validation: {
      is_valid: true,
      issues: [],
    },
    ...overrides,
  };
}

function buildLegacyPayload() {
  return {
    timestamp: "2026-05-05T12:00:00Z",
    pair: "E2ELEG",
    price: 1.12,
    high: 1.125,
    low: 1.115,
    context: "waiting_for_entry",
    allowed_actions: ["open"],
    id_operacion: "e2e_legacy_decision",
    open_positions_count: 0,
    market_structure_H1: "uptrend",
    market_structure_H4: "uptrend",
    ema20_H1: 1.1185,
    ema50_H1: 1.117,
    ema20_H4: 1.115,
    ema50_H4: 1.112,
    rsi14_H1: 60.3,
    rsi14_H4: 62.7,
  };
}

function assertBotBPayload(payload, expectedSymbol) {
  assert.equal(typeof payload.action, "string", "Bot B payload debe tener action.");
  assert.equal(payload.details?.symbol, expectedSymbol, "Bot B payload debe tener details.symbol correcto.");
  assert.equal(typeof payload.decision_id, "string", "Bot B payload debe incluir decision_id.");
  assert.ok(payload.decision_id.length > 0, "decision_id no debe estar vacio.");
  assert.equal(typeof payload.snapshot_id, "string", "Bot B payload debe incluir snapshot_id.");
  assert.ok(payload.snapshot_id.length > 0, "snapshot_id no debe estar vacio.");
  assert.equal(typeof payload.decision_time, "string", "Bot B payload debe incluir decision_time.");
  assert.match(payload.details?.comment || "", /^MAGI\|[A-Za-z0-9_-]+$/, "comment debe usar formato MAGI|short_id.");
}

function readAuditRecordsFor(decisionId) {
  if (!fs.existsSync(auditJournal)) {
    return [];
  }

  return fs
    .readFileSync(auditJournal, "utf8")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line))
    .filter((record) => record.decision_id === decisionId);
}

function cleanupTestArtifacts() {
  const files = [
    "data/analysis/E2EV2.json",
    "data/execution/E2EV2.json",
    "data/responses/E2EV2.json",
    "data/snapshots/legacy/E2EV2_M5_2026-05-05T12-00-00_live.json",
    "data/snapshots/normalized/E2EV2_M5_2026-05-05T12-00-00_live.json",
    "data/analysis/E2ELEG.json",
    "data/execution/E2ELEG.json",
    "data/responses/E2ELEG.json",
    "data/snapshots/legacy/E2ELEG_e2e_legacy_decision.json",
    "data/snapshots/normalized/E2ELEG_e2e_legacy_decision.json",
  ];

  for (const relative of files) {
    const filePath = path.join(root, relative);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  }

  const votesDir = path.join(root, "data/votes/melchor");
  if (fs.existsSync(votesDir)) {
    for (const fileName of fs.readdirSync(votesDir)) {
      if (testSymbols.some((symbol) => fileName.includes(symbol))) {
        fs.unlinkSync(path.join(votesDir, fileName));
      }
    }
  }
}

function restoreAuditJournal() {
  if (originalAuditJournal === null) {
    if (fs.existsSync(auditJournal)) {
      fs.unlinkSync(auditJournal);
    }
    return;
  }

  fs.mkdirSync(path.dirname(auditJournal), { recursive: true });
  fs.writeFileSync(auditJournal, originalAuditJournal, "utf8");
}

cleanupTestArtifacts();

const server = spawn("node", ["src/server/index.js"], {
  cwd: root,
  env: { ...process.env, PORT: String(port) },
  stdio: "ignore",
});

const checks = [];

try {
  await waitForServer();
  checks.push("Servidor local respondio /health");

  const validV2 = await postAnalysis(buildSnapshotV2Payload());
  assert.equal(validV2.response.ok, true, "v2 valido debe aceptarse.");
  assertBotBPayload(validV2.body, "E2EV2");
  checks.push("POST /analisis acepto magi.snapshot.v2 valido");
  checks.push("Payload Bot B de v2 contiene decision_id/snapshot_id/decision_time/comment MAGI");

  const journalRecords = readAuditRecordsFor(validV2.body.decision_id);
  assert.equal(journalRecords.length, 1, "Journal cognitivo debe contener la decision v2.");
  assert.equal(journalRecords[0].execution_payload?.decision_id, validV2.body.decision_id);
  assert.equal(journalRecords[0].snapshot_id, validV2.body.snapshot_id);
  checks.push("Journal cognitivo escribio la decision v2");

  const botBFromGet = await getJson("/analisis/E2EV2");
  assertBotBPayload(botBFromGet, "E2EV2");
  assert.equal(botBFromGet.decision_id, validV2.body.decision_id);
  checks.push("GET /analisis/:symbol devuelve payload compatible con Bot B");

  const snapshots = await getJson("/api/snapshots?limit=5");
  assert.equal(Array.isArray(snapshots.items), true, "/api/snapshots debe devolver items.");
  assert.ok(snapshots.items.some((item) => item.symbol === "E2EV2"), "/api/snapshots debe incluir E2EV2.");
  checks.push("/api/snapshots funciona e incluye snapshot v2");

  const overview = await getJson("/api/overview");
  assert.equal(typeof overview.status, "string", "/api/overview debe devolver status.");
  checks.push("/api/overview funciona");

  const execution = await getJson("/api/execution");
  assert.equal(Array.isArray(execution.items), true, "/api/execution debe devolver items.");
  assert.ok(execution.items.some((item) => item.symbol === "E2EV2"), "/api/execution debe incluir E2EV2.");
  checks.push("/api/execution funciona e incluye decision v2");

  const invalidV2 = await postAnalysis(buildSnapshotV2Payload({ symbol: "", current_price: 0 }));
  assert.equal(invalidV2.response.status, 400, "v2 invalido debe rechazarse con 400.");
  assert.match(invalidV2.body.message, /magi\.snapshot\.v2 invalido/);
  checks.push("POST /analisis rechaza magi.snapshot.v2 invalido");

  const legacy = await postAnalysis(buildLegacyPayload());
  assert.equal(legacy.response.ok, true, "legacy valido debe aceptarse.");
  assertBotBPayload(legacy.body, "E2ELEG");
  checks.push("POST /analisis mantiene compatibilidad legacy valida");

  console.log(
    JSON.stringify(
      {
        ok: true,
        checks,
        v2: {
          symbol: validV2.body.details.symbol,
          action: validV2.body.action,
          decision_id: validV2.body.decision_id,
          snapshot_id: validV2.body.snapshot_id,
          comment: validV2.body.details.comment,
        },
        legacy: {
          symbol: legacy.body.details.symbol,
          action: legacy.body.action,
          decision_id: legacy.body.decision_id,
          snapshot_id: legacy.body.snapshot_id,
          comment: legacy.body.details.comment,
        },
      },
      null,
      2,
    ),
  );
} finally {
  server.kill();
  cleanupTestArtifacts();
  restoreAuditJournal();
}
