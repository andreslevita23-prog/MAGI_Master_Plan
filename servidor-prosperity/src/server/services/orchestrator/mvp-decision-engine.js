import { evaluateAndPersistMelchorVote } from "../voting/melchor-voting.service.js";

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function roundPrice(value) {
  return Number(toNumber(value).toFixed(5));
}

function hasAction(snapshot, action) {
  return Array.isArray(snapshot?.market?.allowed_actions)
    && snapshot.market.allowed_actions.includes(action);
}

function getIndicator(snapshot, key, fallback = null) {
  return snapshot?.raw_indicators?.[key] ?? fallback;
}

function isBullishSetup(snapshot) {
  return (
    getIndicator(snapshot, "market_structure_H1") === "uptrend"
    && getIndicator(snapshot, "market_structure_H4") === "uptrend"
    && toNumber(getIndicator(snapshot, "rsi14_H1")) >= 55
    && toNumber(getIndicator(snapshot, "rsi14_H4")) >= 55
    && toNumber(getIndicator(snapshot, "ema20_H1")) > toNumber(getIndicator(snapshot, "ema50_H1"))
    && toNumber(getIndicator(snapshot, "ema20_H4")) > toNumber(getIndicator(snapshot, "ema50_H4"))
  );
}

function isBearishSetup(snapshot) {
  return (
    getIndicator(snapshot, "market_structure_H1") === "downtrend"
    && getIndicator(snapshot, "market_structure_H4") === "downtrend"
    && toNumber(getIndicator(snapshot, "rsi14_H1")) <= 45
    && toNumber(getIndicator(snapshot, "rsi14_H4")) <= 45
    && toNumber(getIndicator(snapshot, "ema20_H1")) < toNumber(getIndicator(snapshot, "ema50_H1"))
    && toNumber(getIndicator(snapshot, "ema20_H4")) < toNumber(getIndicator(snapshot, "ema50_H4"))
  );
}

function buildHoldDecision(snapshot, reason, overrides = {}) {
  return {
    snapshot_id: snapshot.snapshot_id,
    symbol: snapshot.symbol,
    case_state: "sin_caso",
    case_type: null,
    final_action: "hold",
    direction: null,
    entry_price: null,
    stop_loss: null,
    take_profit: null,
    lot_size: 0,
    reason,
    source: "mvp_engine",
    ...overrides,
  };
}

function buildOpenDecision(snapshot, direction, reason) {
  const entryPrice = toNumber(snapshot.market?.price);
  const rawHigh = toNumber(snapshot.market?.high, null);
  const rawLow = toNumber(snapshot.market?.low, null);
  const high = rawHigh && rawHigh > 0 ? rawHigh : entryPrice;
  const low = rawLow && rawLow > 0 ? rawLow : entryPrice;
  const baseRisk = Math.max(
    toNumber(snapshot.market?.stop_distance_pips) * 0.0001,
    Math.abs(entryPrice - low),
    Math.abs(high - entryPrice),
    0.0008,
  );

  const stopLoss = direction === "buy"
    ? roundPrice(entryPrice - baseRisk)
    : roundPrice(entryPrice + baseRisk);
  const takeProfit = direction === "buy"
    ? roundPrice(entryPrice + baseRisk * 2)
    : roundPrice(entryPrice - baseRisk * 2);

  return {
    snapshot_id: snapshot.snapshot_id,
    symbol: snapshot.symbol,
    case_state: "caso_mvp",
    case_type: "entry_case",
    final_action: "open",
    direction,
    entry_price: roundPrice(entryPrice),
    stop_loss: stopLoss,
    take_profit: takeProfit,
    lot_size: 0.01,
    reason,
    source: "mvp_engine",
  };
}

function getCeoOverride(snapshot = {}) {
  const override = snapshot.ceo_magi?.melchor_risk_override || snapshot.ceo_magi?.risk_override || {};
  const enabled = override.enabled === true || snapshot.ceo_magi?.override_melchor === true;
  const justification = String(
    override.justification || snapshot.ceo_magi?.override_reason || "",
  ).trim();

  if (!enabled || !justification) {
    return null;
  }

  return {
    override_melchor: true,
    override_reason: justification,
    approved_by: override.approved_by || "CEO-MAGI",
    recorded_at: new Date().toISOString(),
  };
}

function buildCeoRiskGovernanceDecision(snapshot, preliminaryDecision, melchorVote, voteFilePath = null) {
  const action = melchorVote?.recommended_action?.action || "hold";
  const baseDecision = buildHoldDecision(snapshot, melchorVote.reason, {
    case_state: snapshot.position?.has_open_position ? "caso_mvp" : "sin_caso",
    case_type: snapshot.position?.has_open_position ? "management_case" : null,
    source: "ceo_magi",
    melchor_vote: melchorVote,
    melchor_vote_file: voteFilePath,
    preliminary_decision: preliminaryDecision,
    ceo_magi_decision: {
      action: "respect_melchor_risk_recommendation",
      reason: melchorVote.reason,
    },
  });

  if (melchorVote.vote === "CLOSE" || action === "close_for_safety") {
    return {
      ...baseDecision,
      final_action: "close_for_safety",
      case_state: "caso_mvp",
      case_type: "management_case",
    };
  }

  if (action === "move_to_breakeven") {
    return {
      ...baseDecision,
      final_action: "move_to_breakeven",
      case_state: "caso_mvp",
      case_type: "management_case",
    };
  }

  if (melchorVote.vote === "PROTECT" || action === "protect") {
    return {
      ...baseDecision,
      final_action: "protect",
      case_state: "caso_mvp",
      case_type: "management_case",
    };
  }

  return baseDecision;
}

function applyCeoRiskGovernance(snapshot, preliminaryDecision) {
  const candidateTrade =
    preliminaryDecision.final_action === "open"
      ? {
          ...preliminaryDecision,
          action: "open",
          risk_percent: snapshot?.risk?.risk_percent_per_trade,
          spread_pips: snapshot?.market?.spread_pips,
        }
      : {
          action: preliminaryDecision.final_action,
        };
  const { vote, file_path: voteFilePath } = evaluateAndPersistMelchorVote(snapshot, {
    candidateTrade,
  });

  const decisionWithVote = {
    ...preliminaryDecision,
    source: preliminaryDecision.final_action === "open" ? "ceo_magi" : preliminaryDecision.source,
    melchor_vote: vote,
    melchor_vote_file: voteFilePath,
  };

  if (preliminaryDecision.final_action !== "open") {
    if (vote.vote === "PROTECT" || vote.vote === "CLOSE") {
      return buildCeoRiskGovernanceDecision(snapshot, preliminaryDecision, vote, voteFilePath);
    }

    return decisionWithVote;
  }

  if (vote.risk_block_recommendation !== true) {
    return decisionWithVote;
  }

  const ceoOverride = getCeoOverride(snapshot);

  if (ceoOverride) {
    return {
      ...decisionWithVote,
      override_melchor: true,
      override_reason: ceoOverride.override_reason,
      ceo_magi_risk_override: ceoOverride,
      reason: `${preliminaryDecision.reason} CEO-MAGI abre pese a recomendacion de bloqueo de Melchor: ${ceoOverride.override_reason}`,
    };
  }

  return buildCeoRiskGovernanceDecision(snapshot, preliminaryDecision, vote, voteFilePath);
}

export function evaluateMvpDecision(snapshot) {
  let preliminaryDecision;

  if (!snapshot?.validation?.is_valid) {
    preliminaryDecision = buildHoldDecision(
      snapshot,
      "No se crea caso: el snapshot llego con validaciones pendientes.",
    );
    return applyCeoRiskGovernance(snapshot, preliminaryDecision);
  }

  if (snapshot.symbol !== "EURUSD") {
    preliminaryDecision = buildHoldDecision(
      snapshot,
      "No se crea caso: el MVP actual solo opera EURUSD.",
    );
    return applyCeoRiskGovernance(snapshot, preliminaryDecision);
  }

  if (snapshot.position?.has_open_position || snapshot.position?.open_positions_count > 0) {
    preliminaryDecision = buildHoldDecision(
      snapshot,
      "Se detecta posicion abierta. El MVP conserva gestion pasiva y no envia cambios todavia.",
      { case_state: "caso_mvp", case_type: "management_case" },
    );
    return applyCeoRiskGovernance(snapshot, preliminaryDecision);
  }

  if (snapshot.market?.context !== "waiting_for_entry" || !hasAction(snapshot, "open")) {
    preliminaryDecision = buildHoldDecision(
      snapshot,
      "No se crea caso: el contexto actual no habilita una entrada MVP.",
    );
    return applyCeoRiskGovernance(snapshot, preliminaryDecision);
  }

  if (isBullishSetup(snapshot)) {
    preliminaryDecision = buildOpenDecision(
      snapshot,
      "buy",
      "Caso MVP detectado: confluencia alcista H1/H4 con RSI y EMAs alineadas.",
    );
    return applyCeoRiskGovernance(snapshot, preliminaryDecision);
  }

  if (isBearishSetup(snapshot)) {
    preliminaryDecision = buildOpenDecision(
      snapshot,
      "sell",
      "Caso MVP detectado: confluencia bajista H1/H4 con RSI y EMAs alineadas.",
    );
    return applyCeoRiskGovernance(snapshot, preliminaryDecision);
  }

  preliminaryDecision = buildHoldDecision(
    snapshot,
    "No se crea caso: no hay confluencia minima suficiente para abrir entrada.",
  );
  return applyCeoRiskGovernance(snapshot, preliminaryDecision);
}
