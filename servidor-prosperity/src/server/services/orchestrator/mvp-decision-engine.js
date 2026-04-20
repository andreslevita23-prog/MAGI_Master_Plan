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
  const high = toNumber(snapshot.market?.high, entryPrice);
  const low = toNumber(snapshot.market?.low, entryPrice);
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

export function evaluateMvpDecision(snapshot) {
  if (!snapshot?.validation?.is_valid) {
    return buildHoldDecision(snapshot, "No se crea caso: el snapshot llego con validaciones pendientes.");
  }

  if (snapshot.symbol !== "EURUSD") {
    return buildHoldDecision(snapshot, "No se crea caso: el MVP actual solo opera EURUSD.");
  }

  if (snapshot.position?.has_open_position || snapshot.position?.open_positions_count > 0) {
    return buildHoldDecision(
      snapshot,
      "Se detecta posicion abierta. El MVP conserva gestion pasiva y no envia cambios todavia.",
      { case_state: "caso_mvp", case_type: "management_case" },
    );
  }

  if (snapshot.market?.context !== "waiting_for_entry" || !hasAction(snapshot, "open")) {
    return buildHoldDecision(snapshot, "No se crea caso: el contexto actual no habilita una entrada MVP.");
  }

  if (isBullishSetup(snapshot)) {
    return buildOpenDecision(
      snapshot,
      "buy",
      "Caso MVP detectado: confluencia alcista H1/H4 con RSI y EMAs alineadas.",
    );
  }

  if (isBearishSetup(snapshot)) {
    return buildOpenDecision(
      snapshot,
      "sell",
      "Caso MVP detectado: confluencia bajista H1/H4 con RSI y EMAs alineadas.",
    );
  }

  return buildHoldDecision(snapshot, "No se crea caso: no hay confluencia minima suficiente para abrir entrada.");
}
