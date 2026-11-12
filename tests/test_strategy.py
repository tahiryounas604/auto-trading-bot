"""Strategy tests — signals verified against hand-computed crossovers."""

from trading_bot.strategy import RSIMeanReversionStrategy, SMACrossoverStrategy


def test_sma_crossover_buy_and_sell():
    # fast=2, slow=3. Hand-computed (verified by running):
    # SMA2: -,10,10,9.5,9,9,10.5,12,12,10,8,8
    # SMA3: -,-,10,9.667,9.333,9,10,11,12,10.667,9.333,8
    # cross down at i=3 (10->9.5 vs 10->9.667), cross up at i=6,
    # cross down again at i=9.
    closes = [10, 10, 10, 9, 9, 9, 12, 12, 12, 8, 8, 8]
    signals = SMACrossoverStrategy(2, 3).generate_signals(closes)
    assert signals[3] == -1
    assert signals[6] == 1
    assert signals[9] == -1
    assert all(s == 0 for i, s in enumerate(signals) if i not in (3, 6, 9))


def test_sma_crossover_flat_series_no_signals():
    signals = SMACrossoverStrategy(2, 3).generate_signals([5.0] * 10)
    assert signals == [0] * 10


def test_sma_crossover_signals_aligned_and_valid():
    closes = [10, 11, 9, 12, 8, 13, 7, 14, 6, 15, 5, 16]
    signals = SMACrossoverStrategy(2, 4).generate_signals(closes)
    assert len(signals) == len(closes)
    assert set(signals) <= {1, -1, 0}


def test_sma_strategy_rejects_bad_periods():
    import pytest

    with pytest.raises(ValueError):
        SMACrossoverStrategy(30, 10)  # fast must be < slow
    with pytest.raises(ValueError):
        SMACrossoverStrategy(0, 10)


def test_rsi_strategy_buy_on_oversold_cross():
    # Steady fall: RSI hits 0 at i=3, crossing below 30 -> buy.
    closes = [10, 9, 8, 7, 6, 5, 4]
    signals = RSIMeanReversionStrategy(period=3).generate_signals(closes)
    assert signals[3] == 1
    assert all(s == 0 for i, s in enumerate(signals) if i != 3)


def test_rsi_strategy_sell_on_overbought_cross():
    # Steady rise: RSI hits 100 at i=3, crossing above 70 -> sell.
    closes = [4, 5, 6, 7, 8, 9, 10]
    signals = RSIMeanReversionStrategy(period=3).generate_signals(closes)
    assert signals[3] == -1
    assert all(s == 0 for i, s in enumerate(signals) if i != 3)


def test_rsi_strategy_rejects_bad_thresholds():
    import pytest

    with pytest.raises(ValueError):
        RSIMeanReversionStrategy(oversold=70, overbought=30)
