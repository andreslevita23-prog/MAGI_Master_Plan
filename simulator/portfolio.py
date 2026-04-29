from __future__ import annotations

from simulator.schemas import SimulatedTrade, TradeResult


class Portfolio:
    def __init__(self) -> None:
        self.open_trade: SimulatedTrade | None = None
        self.closed_trades: list[TradeResult] = []
        self.equity_r: float = 0.0
        self.peak_equity_r: float = 0.0
        self.max_drawdown_r: float = 0.0

    def can_open_trade(self) -> bool:
        return self.open_trade is None

    def open(self, trade: SimulatedTrade) -> bool:
        if self.open_trade is not None:
            return False
        self.open_trade = trade
        return True

    def close(self, result: TradeResult) -> None:
        if self.open_trade is None or self.open_trade.trade_id != result.trade_id:
            raise ValueError("Cannot close a trade that is not currently open")
        self.open_trade.status = "CLOSED"
        self.open_trade = None
        self.closed_trades.append(result)
        self.equity_r += result.pnl_r
        self.peak_equity_r = max(self.peak_equity_r, self.equity_r)
        drawdown = self.peak_equity_r - self.equity_r
        self.max_drawdown_r = max(self.max_drawdown_r, drawdown)
