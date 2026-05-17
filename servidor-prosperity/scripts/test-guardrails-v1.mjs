import assert from "node:assert/strict";
import path from "node:path";

const root = process.cwd();
process.env.MAGI_BOT_C_AUDIT_DIR = path.join(root, "data", "__test_empty_bot_c_audit");
process.env.MAGI_DEMO_LOT_SIZE = "1.0";
process.env.MAGI_DEMO_MODE_UNTIL = "2026-06-05";

const { evaluateMvpDecision } = await import("../src/server/services/orchestrator/mvp-decision-engine.js");
const { mapMvpDecisionToBotBResponse } = await import("../src/server/services/adapters/mt5/bot-b-response-mapper.js");
const { applyDemoLotSizing } = await import("../src/server/services/governance/operational-governance.service.js");

const snapshot = {
  snapshot_id: "guardrails_v1_open_case",
  symbol: "EURUSD",
  timestamp: "2026-05-15T13:00:00.000Z",
  validation: { is_valid: true },
  source: { source_mode: "synthetic_test" },
  market: {
    price: 1.164,
    high: 1.1648,
    low: 1.1632,
    context: "waiting_for_entry",
    allowed_actions: ["open", "hold"],
    spread_pips: 0.3,
    session: "london",
  },
  risk: {
    risk_percent_per_trade: 0.05,
  },
  account: {
    daily_drawdown_percent: 0,
  },
  position: {
    has_open_position: false,
    open_positions_count: 0,
  },
  raw_indicators: {
    market_structure_H1: "uptrend",
    market_structure_H4: "uptrend",
    rsi14_H1: 56,
    rsi14_H4: 56,
    ema20_H1: 1.1642,
    ema50_H1: 1.1638,
    ema20_H4: 1.1641,
    ema50_H4: 1.1639,
  },
};

const decision = evaluateMvpDecision(snapshot);
assert.equal(decision.final_action, "open", "Baseline tecnico debe seguir abriendo.");
assert.equal(decision.lot_size, 0.01, "El core MVP conserva su lotaje base fuera de demo sizing.");
assert.ok(decision.risk_state, "La decision debe incluir risk_state.");
assert.ok(decision.cluster_state, "La decision debe incluir cluster_state.");
assert.ok(decision.shadow_guardrails, "La decision debe incluir shadow_guardrails.");
assert.equal(decision.be_auto_status, "not_enabled_no_mfe_mae_dataset");
assert.equal(decision.news_guardrail_status, "not_enabled_no_calendar");

const demoDecision = applyDemoLotSizing(decision, { demoMode: true });
assert.equal(demoDecision.lot_size, 1.0, "DEMO_MODE debe enviar lotaje 1.0.");
assert.equal(demoDecision.current_lot_size, 1.0);
assert.equal(demoDecision.demo_mode_until, "2026-06-05");

const botBPayload = mapMvpDecisionToBotBResponse(demoDecision, { symbol: "EURUSD" });
assert.equal(botBPayload.action, "open");
assert.equal(botBPayload.details.lot_size, 1.0);
assert.equal(botBPayload.current_lot_size, 1.0);
assert.equal(botBPayload.risk_state.safe_mode_active, false);
assert.equal(botBPayload.details.comment.startsWith("MAGI|"), true);

const safeModeHold = mapMvpDecisionToBotBResponse({
  ...demoDecision,
  final_action: "hold",
  direction: null,
  lot_size: 0,
  current_lot_size: 0,
  reason: "safe_mode_cluster_3_consecutive_sl",
  risk_state: {
    safe_mode_active: true,
    cluster_consecutive_sl: 3,
    blocked_direction: "BUY",
    blocked_until: "2026-05-15T15:00:00.000Z",
  },
});
assert.equal(safeModeHold.action, "hold");
assert.equal(safeModeHold.details.lot_size, 0);
assert.equal(safeModeHold.risk_state.safe_mode_active, true);

console.log(JSON.stringify({ ok: true, checks: ["demo lot 1.0", "risk_state presente", "SAFE_MODE hold no abre"] }, null, 2));
