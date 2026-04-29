from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from magi.contracts import CeoDecision
from simulator.portfolio import Portfolio
from simulator.schemas import EquityPoint, SimulatedTrade, Snapshot, TradeResult


class ExecutionEngine:
    def __init__(self, config: dict):
        self.config = config
        self.sl_pips = float(config.get("sl_pips", 10.0))
        self.tp_rr = float(config.get("tp_rr", 2.0))
        self.timeout_snapshots = int(config.get("timeout_snapshots", 12))
        self.default_pip_size = float(config.get("default_pip_size", 0.0001))
        self.symbol_pip_size = {str(k): float(v) for k, v in config.get("symbol_pip_size", {}).items()}
        self.portfolio = Portfolio()
        self.trade_attempts_blocked_by_open_trade = 0
        self.equity_curve: list[EquityPoint] = []

    @property
    def open_trade(self) -> SimulatedTrade | None:
        return self.portfolio.open_trade

    @property
    def closed_trades(self) -> list[TradeResult]:
        return self.portfolio.closed_trades

    def on_snapshot(self, snapshot: Snapshot, decision: CeoDecision) -> None:
        if self.portfolio.open_trade is not None:
            result = self.evaluate_open_trade(snapshot)
            if result is not None:
                self.portfolio.close(result)

        if decision.action in {"OPEN_LONG", "OPEN_SHORT"}:
            if self.portfolio.can_open_trade():
                trade = self.open_trade_from_decision(snapshot, decision)
                if trade is not None:
                    self.portfolio.open(trade)
            else:
                self.trade_attempts_blocked_by_open_trade += 1

        self.record_equity(snapshot)

    def open_trade_from_decision(self, snapshot: Snapshot, decision: CeoDecision) -> SimulatedTrade | None:
        if snapshot.current_price is None:
            return None
        direction = "LONG" if decision.action == "OPEN_LONG" else "SHORT"
        pip_size = self.pip_size(snapshot.symbol)
        risk = self.sl_pips * pip_size
        if risk <= 0:
            return None
        entry = snapshot.current_price
        if direction == "LONG":
            sl = entry - risk
            tp = entry + risk * self.tp_rr
        else:
            sl = entry + risk
            tp = entry - risk * self.tp_rr

        trade_id = str(uuid5(NAMESPACE_URL, f"{decision.decision_id}:{snapshot.snapshot_id}:trade"))
        return SimulatedTrade(
            schema_version="simulated_trade_v1",
            trade_id=trade_id,
            decision_id=decision.decision_id,
            snapshot_id=snapshot.snapshot_id,
            symbol=snapshot.symbol,
            direction=direction,
            entry_timestamp=snapshot.anchor_bar_timestamp,
            entry_price=entry,
            sl=sl,
            tp=tp,
            initial_risk_price=risk,
            timeout_snapshots=self.timeout_snapshots,
        )

    def evaluate_open_trade(self, snapshot: Snapshot) -> TradeResult | None:
        trade = self.portfolio.open_trade
        if trade is None:
            return None
        if snapshot.symbol != trade.symbol:
            return None

        trade.snapshots_held += 1
        high = snapshot.high if snapshot.high is not None else snapshot.current_price
        low = snapshot.low if snapshot.low is not None else snapshot.current_price
        close = snapshot.current_price if snapshot.current_price is not None else snapshot.close
        if high is None or low is None or close is None:
            return None

        if trade.direction == "LONG":
            hit_tp = high >= trade.tp
            hit_sl = low <= trade.sl
        else:
            hit_tp = low <= trade.tp
            hit_sl = high >= trade.sl

        if hit_tp and hit_sl:
            return self._result(snapshot, trade, close, "AMBIGUOUS", 0.0, True)
        if hit_tp:
            return self._result(snapshot, trade, trade.tp, "TP", self.tp_rr, False)
        if hit_sl:
            return self._result(snapshot, trade, trade.sl, "SL", -1.0, False)
        if trade.snapshots_held >= trade.timeout_snapshots:
            return self._result(snapshot, trade, close, "TIMEOUT", self._pnl_r(trade, close), False)
        return None

    def close_end_of_data(self, snapshot: Snapshot | None) -> TradeResult | None:
        trade = self.portfolio.open_trade
        if trade is None:
            return None
        exit_snapshot = snapshot
        if exit_snapshot is None:
            return None
        exit_price = exit_snapshot.current_price if exit_snapshot.current_price is not None else exit_snapshot.close
        if exit_price is None:
            exit_price = trade.entry_price
        result = self._result(exit_snapshot, trade, exit_price, "END_OF_DATA", self._pnl_r(trade, exit_price), False)
        self.portfolio.close(result)
        self.record_equity(exit_snapshot)
        return result

    def record_equity(self, snapshot: Snapshot) -> None:
        drawdown = self.portfolio.peak_equity_r - self.portfolio.equity_r
        self.equity_curve.append(
            EquityPoint(
                timestamp=snapshot.anchor_bar_timestamp,
                snapshot_id=snapshot.snapshot_id,
                closed_trades=len(self.portfolio.closed_trades),
                equity_r=self.portfolio.equity_r,
                drawdown_r=drawdown,
            )
        )

    def pip_size(self, symbol: str) -> float:
        if symbol in self.symbol_pip_size:
            return self.symbol_pip_size[symbol]
        if "JPY" in symbol.upper():
            return 0.01
        return self.default_pip_size

    def _pnl_r(self, trade: SimulatedTrade, exit_price: float) -> float:
        if trade.direction == "LONG":
            return (exit_price - trade.entry_price) / trade.initial_risk_price
        return (trade.entry_price - exit_price) / trade.initial_risk_price

    def _result(self, snapshot: Snapshot, trade: SimulatedTrade, exit_price: float, reason: str, pnl_r: float, ambiguous: bool) -> TradeResult:
        return TradeResult(
            schema_version="trade_result_v1",
            trade_id=trade.trade_id,
            decision_id=trade.decision_id,
            entry_snapshot_id=trade.snapshot_id,
            exit_snapshot_id=snapshot.snapshot_id,
            symbol=trade.symbol,
            direction=trade.direction,
            entry_timestamp=trade.entry_timestamp,
            exit_timestamp=snapshot.anchor_bar_timestamp,
            entry_price=trade.entry_price,
            exit_price=exit_price,
            sl=trade.sl,
            tp=trade.tp,
            exit_reason=reason,
            pnl_r=round(pnl_r, 8),
            snapshots_held=trade.snapshots_held,
            ambiguous_intrabar=ambiguous,
        )
