import assert from "node:assert/strict";
import { evaluateMelchorRisk } from "../services/melchor-risk-engine.js";
import { mapMvpDecisionToBotBResponse } from "../src/server/services/adapters/mt5/bot-b-response-mapper.js";
import { evaluateMvpDecision } from "../src/server/services/orchestrator/mvp-decision-engine.js";

const baseSnapshot = {
  snapshot_id: "test_snapshot_001",
  symbol: "EURUSD",
  timestamp: "2026-04-24T13:00:00.000Z",
  market: {
    price: 1.1,
    session: "overlap",
    spread_pips: 1.0,
    allowed_actions: ["open"],
  },
  position: {
    has_open_position: false,
    open_positions_count: 0,
  },
  validation: {
    is_valid: true,
    issues: [],
  },
  account: {
    daily_drawdown_percent: 0,
    consecutive_losses: 0,
    risk_percent_per_trade: 0.1,
  },
};

const baseCandidateTrade = {
  action: "open",
  entry_price: 1.1,
  stop_loss: 1.099,
  take_profit: 1.102,
  risk_percent: 0.1,
  spread_pips: 1.0,
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function voteFor(snapshotOverrides = {}, candidateOverrides = {}) {
  return evaluateMelchorRisk(
    {
      ...clone(baseSnapshot),
      ...snapshotOverrides,
    },
    {
      candidateTrade: {
        ...baseCandidateTrade,
        ...candidateOverrides,
      },
      now: new Date("2026-04-24T13:00:00.000Z"),
    },
  );
}

const allowVote = voteFor();
assert.equal(allowVote.vote, "ALLOW", "Caso ALLOW normal");
assert.equal(allowVote.risk_block_recommendation, false, "ALLOW no debe recomendar bloqueo");

const lowRrVote = voteFor({}, { take_profit: 1.1012 });
assert.equal(lowRrVote.vote, "BLOCK", "RR menor a 1.5 debe bloquear");
assert.equal(lowRrVote.risk_block_recommendation, true, "Melchor puede recomendar bloqueo");
assert.equal(lowRrVote.rules_triggered[0], "min_rr");

const openPositionVote = voteFor({
  position: {
    has_open_position: true,
    open_positions_count: 1,
  },
});
assert.equal(openPositionVote.vote, "BLOCK", "Una operacion abierta debe bloquear entrada nueva");
assert.equal(openPositionVote.rules_triggered[0], "max_open_trades");

const notifyDrawdownVote = voteFor({
  account: {
    daily_drawdown_percent: 0.7,
    consecutive_losses: 0,
    risk_percent_per_trade: 0.1,
  },
});
assert.equal(notifyDrawdownVote.vote, "NOTIFY", "Drawdown >= 0.7% debe notificar");
assert.equal(notifyDrawdownVote.risk_block_recommendation, false);

const drawdownBlockVote = voteFor({
  account: {
    daily_drawdown_percent: 1.0,
    consecutive_losses: 0,
    risk_percent_per_trade: 0.1,
  },
});
assert.equal(drawdownBlockVote.vote, "CLOSE", "Drawdown >= 1.0% debe cerrar/proteger");
assert.equal(drawdownBlockVote.risk_block_recommendation, true);

const newsVote = voteFor({
  news: [
    {
      currency: "USD",
      impact: "high",
      timestamp: "2026-04-24T13:20:00.000Z",
    },
  ],
});
assert.equal(newsVote.vote, "BLOCK", "Noticia de alto impacto debe bloquear");
assert.equal(newsVote.rules_triggered[0], "high_impact_news_window");

const breakevenVote = evaluateMelchorRisk(
  {
    ...clone(baseSnapshot),
    position: {
      has_open_position: true,
      open_positions_count: 1,
      profit_progress_to_tp: 0.5,
    },
  },
  {
    candidateTrade: { action: "hold" },
  },
);
assert.equal(breakevenVote.vote, "PROTECT", "50% del TP debe activar proteccion");
assert.equal(breakevenVote.recommended_action.action, "move_to_breakeven");

const bullishSnapshot = {
  ...clone(baseSnapshot),
  snapshot_id: "ceo_respects_melchor_block",
  market: {
    ...clone(baseSnapshot.market),
    high: 1.1008,
    low: 1.0992,
    context: "waiting_for_entry",
    spread_pips: 3.0,
    allowed_actions: ["open"],
  },
  raw_indicators: {
    market_structure_H1: "uptrend",
    market_structure_H4: "uptrend",
    rsi14_H1: 58,
    rsi14_H4: 60,
    ema20_H1: 1.1005,
    ema50_H1: 1.099,
    ema20_H4: 1.1003,
    ema50_H4: 1.0985,
  },
};

const ceoRespectDecision = evaluateMvpDecision(bullishSnapshot);
assert.equal(
  ceoRespectDecision.melchor_vote.risk_block_recommendation,
  true,
  "CEO recibe voto Melchor con recomendacion de bloqueo",
);
assert.equal(ceoRespectDecision.final_action, "hold", "CEO puede respetar bloqueo");
assert.equal(
  ceoRespectDecision.ceo_magi_decision.action,
  "respect_melchor_risk_recommendation",
);

const ceoOverrideDecision = evaluateMvpDecision({
  ...bullishSnapshot,
  snapshot_id: "ceo_overrides_melchor_block",
  ceo_magi: {
    override_melchor: true,
    override_reason: "Entrada autorizada por playbook manual con liquidez excepcional.",
  },
});
assert.equal(
  ceoOverrideDecision.melchor_vote.risk_block_recommendation,
  true,
  "CEO puede recibir recomendacion de bloqueo y aun decidir",
);
assert.equal(ceoOverrideDecision.final_action, "open", "CEO puede ignorar bloqueo recomendado");
assert.equal(ceoOverrideDecision.override_melchor, true);
assert.equal(
  ceoOverrideDecision.override_reason,
  "Entrada autorizada por playbook manual con liquidez excepcional.",
);

const botBResponse = mapMvpDecisionToBotBResponse(ceoOverrideDecision, {
  pair: "EURUSD",
  id_operacion: "bot_b_final_decision",
});
assert.equal(botBResponse.action, "open", "Bot B recibe la decision final del CEO");
assert.equal(botBResponse.details.comment.includes("CEO-MAGI abre"), true);

console.log(
  JSON.stringify(
    {
      status: "ok",
      cases: [
        allowVote.vote,
        lowRrVote.vote,
        openPositionVote.vote,
        notifyDrawdownVote.vote,
        drawdownBlockVote.vote,
        newsVote.vote,
        breakevenVote.recommended_action.action,
        ceoRespectDecision.final_action,
        ceoOverrideDecision.final_action,
        botBResponse.action,
      ],
    },
    null,
    2,
  ),
);
