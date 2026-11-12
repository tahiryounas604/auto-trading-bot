"""Indicator tests — expected values computed by hand."""

import pytest

from trading_bot.indicators import ema, rsi, sma


def test_sma_known_series():
    assert sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_sma_period_1_is_identity():
    assert sma([3.0, 1.5, 7.0], 1) == [3.0, 1.5, 7.0]


def test_sma_empty_and_invalid_period():
    assert sma([], 3) == []
    with pytest.raises(ValueError):
        sma([1, 2, 3], 0)


def test_ema_known_series():
    # k = 2/(3+1) = 0.5, seeded with first price:
    # 10, 12*0.5+10*0.5=11, 14*0.5+11*0.5=12.5
    assert ema([10, 12, 14], 3) == [10.0, 11.0, 12.5]


def test_ema_flat_series_stays_flat():
    assert ema([5.0, 5.0, 5.0, 5.0], 3) == [5.0, 5.0, 5.0, 5.0]


def test_ema_invalid_period():
    with pytest.raises(ValueError):
        ema([1, 2], 0)


def test_rsi_all_gains_is_100():
    assert rsi([1, 2, 3, 4, 5, 6], 3)[3:] == [100.0, 100.0, 100.0]


def test_rsi_all_losses_is_0():
    assert rsi([6, 5, 4, 3, 2, 1], 3)[3:] == [0.0, 0.0, 0.0]


def test_rsi_flat_series_is_50():
    assert rsi([5, 5, 5, 5, 5], 2)[2:] == [50.0, 50.0, 50.0]


def test_rsi_mixed_series_wilder_smoothing():
    # changes +1,-1,+1,-1, period 2:
    # i=2: avg gain .5, avg loss .5 -> RSI 50
    # i=3: avg gain .75, avg loss .25 -> RS 3 -> RSI 75
    # i=4: avg gain .375, avg loss .625 -> RS .6 -> RSI 37.5
    assert rsi([10, 11, 10, 11, 10], 2) == [None, None, 50.0, 75.0, 37.5]


def test_rsi_warmup_is_none_and_aligned():
    out = rsi([1, 2, 3, 4, 5], 3)
    assert len(out) == 5
    assert out[:3] == [None, None, None]
    assert out[3] is not None
