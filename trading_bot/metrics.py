"""Performance metrics computed from closed trades and an equity curve.

All functions are pure: they take numbers in and return numbers out.
Definitions:

* win rate — fraction of closed trades with positive PnL.
* profit factor — gross profit / gross loss (``inf`` when there are
  profits and no losses; ``0.0`` when there are no profits at all).
* max drawdown — largest peak-to-trough fall of the equity curve,
  as a fraction of the peak (0.0-1.0).
* Sharpe ratio — mean periodic return / sample standard deviation of
  returns, annualised with ``sqrt(periods_per_year)`` (default 252
  trading days). ``0.0`` when there are too few returns or no variance.
"""

from __future__ import annotations

import math
import statistics


def win_rate(pnls: list[float]) -> float:
    """Fraction of trades that were winners. 0.0 when there are no trades."""
    if not pnls:
        return 0.0
    return sum(1 for p in pnls if p > 0) / len(pnls)


def profit_factor(pnls: list[float]) -> float:
    """Gross profit / gross loss. ``inf`` with profit and no loss."""
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def max_drawdown(equity_curve: list[float]) -> float:
    """Largest peak-to-trough decline as a fraction of the peak."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst


def sharpe_ratio(
    equity_curve: list[float],
    periods_per_year: int = 252,
) -> float:
    """Annualised Sharpe ratio of the equity curve's periodic returns."""
    if len(equity_curve) < 2:
        return 0.0
    returns = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] != 0
    ]
    if len(returns) < 2:
        return 0.0
    std = statistics.stdev(returns)
    if std == 0:
        return 0.0
    return statistics.mean(returns) / std * math.sqrt(periods_per_year)


def summarise(pnls: list[float], equity_curve: list[float]) -> dict[str, float]:
    """One dict with every metric, for reports and the CLI."""
    total_return = 0.0
    if len(equity_curve) >= 2 and equity_curve[0] != 0:
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
    return {
        "num_trades": float(len(pnls)),
        "win_rate": win_rate(pnls),
        "profit_factor": profit_factor(pnls),
        "max_drawdown": max_drawdown(equity_curve),
        "sharpe_ratio": sharpe_ratio(equity_curve),
        "total_return": total_return,
        "total_pnl": float(sum(pnls)),
    }
