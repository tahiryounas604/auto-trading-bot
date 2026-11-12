"""Tytechlabs auto-trading-bot — technical indicators.

Clean-room implementation using only the Python standard library.
All functions take plain lists of floats and return plain lists, so they
are easy to test and to reuse from strategies, the backtester and the
paper-trading engine.

Conventions
-----------
* Returned lists are aligned with the input: ``result[i]`` describes the
  value at ``prices[i]``.
* ``None`` marks values that cannot be computed yet (warm-up period).
* RSI follows Wilder's smoothing.
* EMA is seeded with the first price (a common, documented choice).
"""

from __future__ import annotations


def sma(prices: list[float], period: int) -> list[float | None]:
    """Simple moving average.

    ``result[i]`` is the mean of ``prices[i-period+1:i+1]`` once at least
    ``period`` values are available, otherwise ``None``.
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    if not prices:
        return []
    result: list[float | None] = [None] * len(prices)
    window_sum = 0.0
    for i, price in enumerate(prices):
        window_sum += price
        if i >= period:
            window_sum -= prices[i - period]
        if i >= period - 1:
            result[i] = window_sum / period
    return result


def ema(prices: list[float], period: int) -> list[float | None]:
    """Exponential moving average (Wilder-style, ``k = 2 / (period + 1)``).

    Seeded with ``prices[0]``; the first value is therefore always
    defined (no warm-up ``None`` values).
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    if not prices:
        return []
    k = 2.0 / (period + 1)
    result: list[float | None] = [None] * len(prices)
    current = float(prices[0])
    result[0] = current
    for i in range(1, len(prices)):
        current = prices[i] * k + current * (1.0 - k)
        result[i] = current
    return result


def rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index (0-100) with Wilder's smoothing.

    * ``result[i]`` is ``None`` for the first ``period`` values.
    * A run of only gains gives 100; only losses gives 0; no price
      movement at all gives 50 (neither overbought nor oversold).
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    if not prices:
        return []
    result: list[float | None] = [None] * len(prices)
    if len(prices) <= period:
        return result

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(change if change > 0 else 0.0)
        losses.append(-change if change < 0 else 0.0)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result[period] = _rsi_value(avg_gain, avg_loss)

    for i in range(period + 1, len(prices)):
        # gains/losses index: change into prices[i] is gains[i-1].
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        result[i] = _rsi_value(avg_gain, avg_loss)
    return result


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0.0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
