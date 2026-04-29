from __future__ import annotations

from collections import Counter
from typing import Any

from simulator.schemas import TradeResult


def calculate_metrics(trades: list[TradeResult]) -> dict[str, Any]:
    total = len(trades)
    wins = sum(1 for trade in trades if trade.pnl_r > 0)
    losses = sum(1 for trade in trades if trade.pnl_r < 0)
    gross_profit = sum(trade.pnl_r for trade in trades if trade.pnl_r > 0)
    gross_loss = abs(sum(trade.pnl_r for trade in trades if trade.pnl_r < 0))
    pnl_values = [trade.pnl_r for trade in trades]
    by_direction = Counter(trade.direction for trade in trades)

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total if total else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0),
        "expectancy_r": sum(pnl_values) / total if total else 0.0,
        "average_r": sum(pnl_values) / total if total else 0.0,
        "max_drawdown_r": calculate_max_drawdown_r(pnl_values),
        "ambiguous_trades": sum(1 for trade in trades if trade.exit_reason == "AMBIGUOUS"),
        "timeout_trades": sum(1 for trade in trades if trade.exit_reason == "TIMEOUT"),
        "trades_by_direction": dict(sorted(by_direction.items())),
    }


def calculate_max_drawdown_r(pnl_values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for pnl in pnl_values:
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return max_drawdown


def metrics_markdown(metrics: dict[str, Any]) -> str:
    lines = [
        "# MAGI Simulator Metrics",
        "",
        f"- total_trades: {metrics['total_trades']}",
        f"- wins: {metrics['wins']}",
        f"- losses: {metrics['losses']}",
        f"- win_rate: {metrics['win_rate']:.4f}",
        f"- profit_factor: {metrics['profit_factor']:.4f}",
        f"- expectancy_r: {metrics['expectancy_r']:.4f}",
        f"- average_r: {metrics['average_r']:.4f}",
        f"- max_drawdown_r: {metrics['max_drawdown_r']:.4f}",
        f"- ambiguous_trades: {metrics['ambiguous_trades']}",
        f"- timeout_trades: {metrics['timeout_trades']}",
        "",
        "## Trades By Direction",
        "",
    ]
    for direction, count in metrics["trades_by_direction"].items():
        lines.append(f"- {direction}: {count}")
    return "\n".join(lines) + "\n"
