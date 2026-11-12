"""Backtester: run a strategy over historical OHLCV bars.

Long-only in v0.1. A signal on bar ``i`` is executed at that bar's
close, so there is no look-ahead. While a position is open, each new
bar is checked for a stop-loss or take-profit hit (using the bar's low
and high); a signal sell also closes the position. Any position still
open at the last bar is closed at the final close so every trade is
accounted for.

Fees are charged as a percentage of the traded notional on both entry
and exit (``fee_pct``); set to 0 for fee-free runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .data import Bar, closes
from .metrics import summarise
from .risk import RiskManager
from .strategy import Strategy


@dataclass
class Trade:
    entry_index: int
    entry_price: float
    exit_index: int
    exit_price: float
    units: float
    pnl: float
    exit_reason: str  # "signal" | "stop_loss" | "take_profit" | "end_of_data"


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    final_equity: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)


class Backtester:
    def __init__(
        self,
        strategy: Strategy,
        initial_cash: float = 10_000.0,
        risk_manager: RiskManager | None = None,
        fee_pct: float = 0.0,
    ) -> None:
        if initial_cash <= 0:
            raise ValueError("initial_cash must be > 0")
        if fee_pct < 0:
            raise ValueError("fee_pct must be >= 0")
        self.strategy = strategy
        self.initial_cash = initial_cash
        self.risk = risk_manager or RiskManager()
        self.fee_pct = fee_pct

    def run(self, bars: list[Bar]) -> BacktestResult:
        if not bars:
            raise ValueError("no bars to backtest")
        signals = self.strategy.generate_signals(closes(bars))
        cash = self.initial_cash
        units = 0.0
        entry_price = 0.0
        entry_index = -1
        stop = 0.0
        target: float | None = None
        trades: list[Trade] = []
        equity_curve: list[float] = []

        def close_position(i: int, price: float, reason: str) -> None:
            nonlocal cash, units
            proceeds = units * price
            fee = proceeds * self.fee_pct / 100.0
            pnl = proceeds - fee - (units * entry_price) - (
                units * entry_price * self.fee_pct / 100.0
            )
            cash += proceeds - fee
            trades.append(
                Trade(entry_index, entry_price, i, price, units, pnl, reason)
            )
            units = 0.0

        for i, bar in enumerate(bars):
            # 1. Stop-loss / take-profit check on the open position.
            if units > 0:
                if bar.low <= stop:
                    close_position(i, stop, "stop_loss")
                elif target is not None and bar.high >= target:
                    close_position(i, target, "take_profit")

            # 2. Strategy signal at this bar's close.
            if signals[i] == 1 and units == 0 and not self.risk.tripped:
                stop = self.risk.stop_price(bar.close)
                target = self.risk.take_profit_price(bar.close)
                size = self.risk.position_size(cash, bar.close, stop)
                if size > 0:
                    cost = size * bar.close
                    fee = cost * self.fee_pct / 100.0
                    if cost + fee <= cash:
                        cash -= cost + fee
                        units = size
                        entry_price = bar.close
                        entry_index = i
            elif signals[i] == -1 and units > 0:
                close_position(i, bar.close, "signal")

            equity = cash + units * bar.close
            equity_curve.append(equity)
            self.risk.update(equity)

        # 3. Close any open position at the final close.
        if units > 0:
            close_position(len(bars) - 1, bars[-1].close, "end_of_data")
            equity_curve[-1] = cash

        result = BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            final_equity=cash,
        )
        result.metrics = summarise([t.pnl for t in trades], equity_curve)
        return result
