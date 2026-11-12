"""Trading strategies.

A strategy turns a list of closing prices into a list of signals aligned
with the prices:

* ``1``  — open (or stay in) a long position
* ``-1`` — close a long position / stay flat
* ``0``  — no action

Signals are generated on the close of bar ``i`` and acted on at that same
close by the backtester and the paper trader, so there is no look-ahead:
a signal never uses a price from the future.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .indicators import rsi, sma

Signal = int  # 1 (buy), -1 (sell), 0 (hold)


class Strategy(ABC):
    """Interface every strategy must implement."""

    name: str = "base"

    @abstractmethod
    def generate_signals(self, closes: list[float]) -> list[Signal]:
        """Return one signal per close, aligned with ``closes``."""

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"{type(self).__name__}(name={self.name!r})"


class SMACrossoverStrategy(Strategy):
    """Buy when the fast SMA crosses above the slow SMA; sell on the
    opposite cross. Classic trend-following. Long-only in v0.1."""

    def __init__(self, fast_period: int = 10, slow_period: int = 30) -> None:
        if fast_period < 1 or slow_period < 1:
            raise ValueError("periods must be >= 1")
        if fast_period >= slow_period:
            raise ValueError("fast_period must be smaller than slow_period")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = f"sma_{fast_period}_{slow_period}"

    def generate_signals(self, closes: list[float]) -> list[Signal]:
        fast = sma(closes, self.fast_period)
        slow = sma(closes, self.slow_period)
        signals: list[Signal] = [0] * len(closes)
        for i in range(1, len(closes)):
            if fast[i] is None or slow[i] is None:
                continue
            if fast[i - 1] is None or slow[i - 1] is None:
                continue
            if fast[i - 1] <= slow[i - 1] and fast[i] > slow[i]:
                signals[i] = 1
            elif fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
                signals[i] = -1
        return signals


class RSIMeanReversionStrategy(Strategy):
    """Buy when RSI crosses down into oversold territory (price is
    expected to revert upward); sell when RSI crosses up into
    overbought territory. Long-only in v0.1."""

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> None:
        if period < 1:
            raise ValueError("period must be >= 1")
        if not 0.0 <= oversold < overbought <= 100.0:
            raise ValueError("require 0 <= oversold < overbought <= 100")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"rsi_{period}_{oversold:g}_{overbought:g}"

    def generate_signals(self, closes: list[float]) -> list[Signal]:
        values = rsi(closes, self.period)
        signals: list[Signal] = [0] * len(closes)
        for i in range(1, len(closes)):
            if values[i] is None:
                continue
            # The previous value is None only at the first defined RSI
            # point; treat "no previous reading" as neutral (50).
            previous = values[i - 1] if values[i - 1] is not None else 50.0
            if previous >= self.oversold and values[i] < self.oversold:
                signals[i] = 1
            elif previous <= self.overbought and values[i] > self.overbought:
                signals[i] = -1
        return signals
