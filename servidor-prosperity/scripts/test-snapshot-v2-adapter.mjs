import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const port = 3105;
const baseUrl = `http://127.0.0.1:${port}`;
const root = process.cwd();

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer() {
  for (let attempt = 0; attempt < 30; attempt += 1) {
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

function buildLegacyPayload() {
  return {
    timestamp: "2026-05-05T12:00:00Z",
    pair: "LEGTEST",
    price: 1.12,
    high: 1.125,
    low: 1.115,
    context: "waiting_for_entry",
    allowed_actions: ["open"],
    id_operacion: "test_legacy_snapshot_v2_adapter",
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

function buildSnapshotV2Payload(overrides = {}) {
  return {
    schema_version: "magi.snapshot.v2",
    snapshot_id: "V2TEST_M5_2026-05-05T12:00:00_live",
    symbol: "V2TEST",
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

function cleanupTestArtifacts() {
  const relativeFiles = [
    "data/analysis/LEGTEST.json",
    "data/execution/LEGTEST.json",
    "data/responses/LEGTEST.json",
    "data/snapshots/legacy/LEGTEST_test_legacy_snapshot_v2_adapter.json",
    "data/snapshots/normalized/LEGTEST_test_legacy_snapshot_v2_adapter.json",
    "data/analysis/V2TEST.json",
    "data/execution/V2TEST.json",
    "data/responses/V2TEST.json",
    "data/snapshots/legacy/V2TEST_M5_2026-05-05T12-00-00_live.json",
    "data/snapshots/normalized/V2TEST_M5_2026-05-05T12-00-00_live.json",
  ];

  for (const relative of relativeFiles) {
    const filePath = path.join(root, relative);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  }

  const votesDir = path.join(root, "data/votes/melchor");
  if (fs.existsSync(votesDir)) {
    for (const fileName of fs.readdirSync(votesDir)) {
      if (fileName.includes("LEGTEST") || fileName.includes("V2TEST")) {
        fs.unlinkSync(path.join(votesDir, fileName));
      }
    }
  }
}

cleanupTestArtifacts();

const server = spawn("node", ["src/server/index.js"], {
  cwd: root,
  env: { ...process.env, PORT: String(port) },
  stdio: "ignore",
});

try {
  await waitForServer();

  const legacy = await postAnalysis(buildLegacyPayload());
  assert.equal(legacy.response.ok, true, "Payload legacy debe seguir aceptandose.");
  assert.equal(legacy.body.details.symbol, "LEGTEST");

  const validV2 = await postAnalysis(buildSnapshotV2Payload());
  assert.equal(validV2.response.ok, true, "Payload magi.snapshot.v2 valido debe aceptarse.");
  assert.equal(validV2.body.details.symbol, "V2TEST");
  assert.ok(["hold", "open", "close_for_safety", "protect", "move_to_breakeven"].includes(validV2.body.action));

  const invalidV2 = await postAnalysis(buildSnapshotV2Payload({ symbol: "", current_price: 0 }));
  assert.equal(invalidV2.response.status, 400, "Payload v2 invalido debe rechazarse con 400.");
  assert.match(invalidV2.body.message, /magi\.snapshot\.v2 invalido/);

  const botBCompatible = await fetch(`${baseUrl}/analisis/V2TEST`).then((response) => response.json());
  assert.equal(botBCompatible.details.symbol, "V2TEST");
  assert.equal(typeof botBCompatible.action, "string");
  assert.equal(typeof botBCompatible.id_operacion, "string");

  console.log("OK snapshot-v2-adapter: legacy, v2 valido, v2 invalido y GET /analisis/:symbol verificados.");
} finally {
  server.kill();
  cleanupTestArtifacts();
}
