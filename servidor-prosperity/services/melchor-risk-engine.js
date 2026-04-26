import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const defaultRulesPath = path.join(repoRoot, "config", "melchor_rules.json");

function toNumber(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeSymbol(value) {
  return String(value || "UNKNOWN").trim().toUpperCase();
}

function loadRules(rulesPath = defaultRulesPath) {
  return JSON.parse(fs.readFileSync(rulesPath, "utf8"));
}

function pipSizeForSymbol(symbol) {
  if (symbol.includes("JPY")) {
    return 0.01;
  }

  if (symbol.includes("XAU")) {
    return 0.1;
  }

  return 0.0001;
}

function distanceInPips(symbol, firstPrice, secondPrice) {
  const first = toNumber(firstPrice);
  const second = toNumber(secondPrice);

  if (first === null || second === null) {
    return null;
  }

  return Math.abs(first - second) / pipSizeForSymbol(symbol);
}

function calculateRiskReward(symbol, candidateTrade = {}, snapshot = {}) {
  const explicit = toNumber(
    candidateTrade.risk_reward_ratio
      ?? candidateTrade.rr
      ?? snapshot?.trade?.risk_reward_ratio
      ?? snapshot?.risk?.risk_reward_ratio,
  );

  if (explicit !== null) {
    return explicit;
  }

  const entry = toNumber(candidateTrade.entry_price ?? candidateTrade.entryPrice);
  const stopLoss = toNumber(candidateTrade.stop_loss ?? candidateTrade.stopLoss);
  const takeProfit = toNumber(candidateTrade.take_profit ?? candidateTrade.takeProfit);

  if (entry === null || stopLoss === null || takeProfit === null || entry === stopLoss) {
    return null;
  }

  return Math.abs(takeProfit - entry) / Math.abs(entry - stopLoss);
}

function calculateSlPips(symbol, candidateTrade = {}, snapshot = {}) {
  const explicit = toNumber(
    candidateTrade.stop_loss_pips
      ?? candidateTrade.sl_pips
      ?? snapshot?.market?.stop_distance_pips
      ?? snapshot?.trade?.stop_loss_pips,
  );

  if (explicit !== null && explicit > 0) {
    return explicit;
  }

  return distanceInPips(
    symbol,
    candidateTrade.entry_price ?? candidateTrade.entryPrice ?? snapshot?.market?.price,
    candidateTrade.stop_loss ?? candidateTrade.stopLoss,
  );
}

function parseUtcMinutes(value) {
  const [hours, minutes] = String(value || "00:00").split(":").map(Number);
  return hours * 60 + minutes;
}

function isInsideWindow(minutes, window) {
  const start = parseUtcMinutes(window.start);
  const end = parseUtcMinutes(window.end);

  if (start <= end) {
    return minutes >= start && minutes <= end;
  }

  return minutes >= start || minutes <= end;
}

function isAllowedSession(snapshot = {}, rules) {
  const explicitSession = String(
    snapshot?.market?.session ?? snapshot?.session ?? snapshot?.raw?.session ?? "",
  )
    .trim()
    .toLowerCase();

  if (explicitSession) {
    return rules.sessions.allowed.includes(explicitSession);
  }

  const timestamp = new Date(snapshot.timestamp || Date.now());

  if (Number.isNaN(timestamp.getTime())) {
    return false;
  }

  const minutes = timestamp.getUTCHours() * 60 + timestamp.getUTCMinutes();
  return rules.sessions.utc_windows.some((window) => isInsideWindow(minutes, window));
}

function extractAccountContext(snapshot = {}, accountContext = {}) {
  return {
    ...snapshot.account,
    ...snapshot.risk,
    ...accountContext,
  };
}

function getOpenPositionsCount(snapshot = {}, accountContext = {}) {
  return toNumber(
    accountContext.open_positions_count
      ?? accountContext.openPositionsCount
      ?? snapshot?.position?.open_positions_count,
    0,
  );
}

function hasHighImpactNews(snapshot = {}, rules, now = new Date()) {
  const newsItems = Array.isArray(snapshot?.news)
    ? snapshot.news
    : Array.isArray(snapshot?.market?.news)
      ? snapshot.market.news
      : snapshot?.news
        ? [snapshot.news]
        : [];

  return newsItems.some((item) => {
    const impact = String(item.impact || item.importance || "").toLowerCase();
    const currency = String(item.currency || "").toUpperCase();

    if (
      impact !== rules.news.blocked_impact
      || !rules.news.blocked_currencies.includes(currency)
    ) {
      return false;
    }

    if (item.active === true || item.in_window === true) {
      return true;
    }

    const newsTime = new Date(item.timestamp || item.time || item.datetime || "");

    if (Number.isNaN(newsTime.getTime())) {
      return false;
    }

    const minutesAway = Math.abs(newsTime.getTime() - now.getTime()) / 60000;
    return minutesAway <= Math.max(
      rules.news.window_minutes_before,
      rules.news.window_minutes_after,
    );
  });
}

function hasCriticalData(snapshot = {}, candidateTrade = {}, needsTradeData) {
  if (snapshot.validation?.is_valid !== true) {
    return false;
  }

  const criticalSnapshotFields = [
    snapshot.snapshot_id,
    snapshot.symbol,
    snapshot.timestamp,
    snapshot.market?.price,
  ];

  if (criticalSnapshotFields.some((field) => field === undefined || field === null || field === "")) {
    return false;
  }

  if (!needsTradeData) {
    return true;
  }

  return [
    candidateTrade.entry_price ?? candidateTrade.entryPrice,
    candidateTrade.stop_loss ?? candidateTrade.stopLoss,
    candidateTrade.take_profit ?? candidateTrade.takeProfit,
  ].every((field) => field !== undefined && field !== null && field !== "");
}

function buildVote({
  vote,
  riskBlockRecommendation,
  riskLevel,
  reason,
  rulesTriggered,
  recommendedAction,
}) {
  return {
    module: "MELCHOR",
    version: "v1.0",
    vote,
    risk_block_recommendation: riskBlockRecommendation,
    confidence: 1.0,
    risk_level: riskLevel,
    reason,
    rules_triggered: rulesTriggered,
    recommended_action: recommendedAction,
  };
}

function decorateVote(vote, snapshot = {}) {
  return {
    ...vote,
    timestamp: new Date().toISOString(),
    symbol: normalizeSymbol(snapshot.symbol),
    snapshot_id: snapshot.snapshot_id || null,
  };
}

export function evaluateMelchorRisk(snapshot = {}, options = {}) {
  const rules = options.rules || loadRules(options.rulesPath);
  const candidateTrade = options.candidateTrade || snapshot.candidate_trade || {};
  const accountContext = extractAccountContext(snapshot, options.accountContext || {});
  const symbol = normalizeSymbol(snapshot.symbol);
  const openPositionsCount = getOpenPositionsCount(snapshot, accountContext);
  const finalAction = String(candidateTrade.final_action || candidateTrade.action || "").toLowerCase();
  const wantsOpen = finalAction === "open";
  const hasOpenPosition = openPositionsCount > 0 || Boolean(snapshot?.position?.has_open_position);
  const profitProgress = toNumber(
    accountContext.profit_progress_to_tp
      ?? snapshot?.position?.profit_progress_to_tp
      ?? snapshot?.position?.summary?.profit_progress_to_tp,
    0,
  );
  const rulesTriggered = [];

  if (!hasCriticalData(snapshot, candidateTrade, wantsOpen)) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "CRITICAL",
        reason: "Faltan datos criticos para evaluar riesgo.",
        rulesTriggered: ["missing_critical_data"],
        recommendedAction: { action: "hold", details: { missing_critical_data: true } },
      }),
      snapshot,
    );
  }

  const dailyDrawdown = toNumber(
    accountContext.daily_drawdown_percent ?? accountContext.dailyDrawdownPercent,
    0,
  );

  if (dailyDrawdown >= rules.risk.daily_drawdown_block_percent) {
    return decorateVote(
      buildVote({
        vote: "CLOSE",
        riskBlockRecommendation: true,
        riskLevel: "CRITICAL",
        reason: "Drawdown diario igual o superior al limite de bloqueo.",
        rulesTriggered: ["daily_drawdown_block"],
        recommendedAction: {
          action: hasOpenPosition ? "close_for_safety" : "hold",
          details: { daily_drawdown_percent: dailyDrawdown },
        },
      }),
      snapshot,
    );
  }

  if (
    hasOpenPosition
    && profitProgress >= rules.trade_management.move_sl_to_breakeven_at_tp_progress
  ) {
    return decorateVote(
      buildVote({
        vote: "PROTECT",
        riskBlockRecommendation: false,
        riskLevel: "MEDIUM",
        reason: "La operacion alcanzo 50% del TP; proteger en breakeven.",
        rulesTriggered: ["move_sl_to_breakeven"],
        recommendedAction: {
          action: "move_to_breakeven",
          details: {
            profit_progress_to_tp: profitProgress,
            trailing_after_be: rules.trade_management.after_breakeven,
          },
        },
      }),
      snapshot,
    );
  }

  const consecutiveLosses = toNumber(
    accountContext.consecutive_losses ?? accountContext.consecutiveLosses,
    0,
  );

  if (consecutiveLosses >= rules.risk.max_consecutive_losses) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "CRITICAL",
        reason: "Racha de 5 perdidas consecutivas; bloquear nuevas entradas y notificar.",
        rulesTriggered: ["max_consecutive_losses"],
        recommendedAction: {
          action: "hold",
          details: { notify: true, consecutive_losses: consecutiveLosses },
        },
      }),
      snapshot,
    );
  }

  if (hasHighImpactNews(snapshot, rules, options.now || new Date())) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "HIGH",
        reason: "Noticia de alto impacto activa para USD, EUR o GBP.",
        rulesTriggered: ["high_impact_news_window"],
        recommendedAction: { action: "hold", details: { news_window_blocked: true } },
      }),
      snapshot,
    );
  }

  if (wantsOpen && openPositionsCount >= rules.risk.max_open_trades) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "HIGH",
        reason: "Ya existe una operacion abierta.",
        rulesTriggered: ["max_open_trades"],
        recommendedAction: { action: "hold", details: { open_positions_count: openPositionsCount } },
      }),
      snapshot,
    );
  }

  if (wantsOpen && !isAllowedSession(snapshot, rules)) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "HIGH",
        reason: "Fuera de sesiones Londres/Nueva York.",
        rulesTriggered: ["session_block"],
        recommendedAction: { action: "hold", details: { allowed_sessions: rules.sessions.allowed } },
      }),
      snapshot,
    );
  }

  const spreadPips = toNumber(
    candidateTrade.spread_pips ?? snapshot?.market?.spread_pips ?? snapshot?.spread_pips,
  );

  if (wantsOpen && spreadPips !== null && spreadPips > rules.market.max_spread_pips) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "HIGH",
        reason: "Spread superior al maximo permitido.",
        rulesTriggered: ["max_spread_pips"],
        recommendedAction: { action: "hold", details: { spread_pips: spreadPips } },
      }),
      snapshot,
    );
  }

  const riskPercent = toNumber(
    candidateTrade.risk_percent
      ?? candidateTrade.riskPercent
      ?? accountContext.risk_percent_per_trade
      ?? accountContext.riskPercentPerTrade,
  );

  if (wantsOpen && riskPercent !== null && riskPercent > rules.risk.max_risk_percent_per_trade) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "HIGH",
        reason: "Riesgo por operacion superior a 0.1% del capital.",
        rulesTriggered: ["max_risk_percent_per_trade"],
        recommendedAction: { action: "hold", details: { risk_percent: riskPercent } },
      }),
      snapshot,
    );
  }

  const rr = calculateRiskReward(symbol, candidateTrade, snapshot);

  if (wantsOpen && (rr === null || rr < rules.risk.min_rr)) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "HIGH",
        reason: "Relacion riesgo/beneficio menor a 1.5.",
        rulesTriggered: ["min_rr"],
        recommendedAction: { action: "hold", details: { risk_reward_ratio: rr } },
      }),
      snapshot,
    );
  }

  const slPips = calculateSlPips(symbol, candidateTrade, snapshot);

  if (
    wantsOpen
    && (slPips === null || slPips < rules.market.min_sl_pips || slPips > rules.market.max_sl_pips)
  ) {
    return decorateVote(
      buildVote({
        vote: "BLOCK",
        riskBlockRecommendation: true,
        riskLevel: "HIGH",
        reason: "Distancia de SL fuera del rango permitido.",
        rulesTriggered: ["sl_bounds"],
        recommendedAction: {
          action: "hold",
          details: {
            sl_pips: slPips,
            min_sl_pips: rules.market.min_sl_pips,
            max_sl_pips: rules.market.max_sl_pips,
          },
        },
      }),
      snapshot,
    );
  }

  if (dailyDrawdown >= rules.risk.daily_drawdown_notify_percent) {
    return decorateVote(
      buildVote({
        vote: "NOTIFY",
        riskBlockRecommendation: false,
        riskLevel: "MEDIUM",
        reason: "Drawdown diario igual o superior al umbral de notificacion.",
        rulesTriggered: ["daily_drawdown_notify"],
        recommendedAction: {
          action: "hold",
          details: { notify: true, daily_drawdown_percent: dailyDrawdown },
        },
      }),
      snapshot,
    );
  }

  if (wantsOpen && rr !== null && rr < rules.risk.preferred_rr) {
    rulesTriggered.push("rr_below_preferred");
  }

  return decorateVote(
    buildVote({
      vote: "ALLOW",
      riskBlockRecommendation: false,
      riskLevel: rulesTriggered.length ? "MEDIUM" : "LOW",
      reason: rulesTriggered.length
        ? "Entrada permitida, aunque RR queda por debajo del preferente."
        : "Reglas Melchor v1 superadas.",
      rulesTriggered,
      recommendedAction: {
        action: "hold",
        details: {
          risk_reward_ratio: rr,
          preferred_rr: rules.risk.preferred_rr,
        },
      },
    }),
    snapshot,
  );
}

export { defaultRulesPath, loadRules };
