"""Metrics tests — values computed by hand or from statistics."""

import math
import statistics

import pytest

from trading_bot.metrics import (
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    summarise,
    win_rate,
)


def test_win_rate():
    assert win_rate([100, -50, 200, -50]) == 0.5
    assert win_rate([]) == 0.0
    assert win_rate([10, 20]) == 1.0
    assert win_rate([-10]) == 0.0


def test_profit_factor():
    assert profit_factor([100, -50, 200, -50]) == 3.0
    assert profit_factor([100, 50]) == math.inf  # profit, no losses
    assert profit_factor([]) == 0.0
    assert profit_factor([-100]) == 0.0


def test_max_drawdown():
    # peak 11,000 -> trough 9,000 = 2,000/11,000
    assert max_drawdown([10_000, 11_000, 10_500, 9_000, 12_000]) == pytest.approx(
        2000 / 11_000
    )
    assert max_drawdown([10_000, 11_000, 12_000]) == 0.0
    assert max_drawdown([]) == 0.0
    assert max_drawdown([5_000]) == 0.0


def test_sharpe_ratio():
    curve = [100.0, 101.0, 103.02, 101.9898, 105.049494]
    returns = [
        (curve[i] - curve[i - 1]) / curve[i - 1] for i in range(1, len(curve))
    ]
    expected = statistics.mean(returns) / statistics.stdev(returns) * math.sqrt(252)
    assert sharpe_ratio(curve) == pytest.approx(expected)


def test_sharpe_ratio_edge_cases():
    assert sharpe_ratio([]) == 0.0
    assert sharpe_ratio([100.0]) == 0.0
    assert sharpe_ratio([100.0, 100.0, 100.0]) == 0.0  # zero variance
    assert sharpe_ratio([100.0, 110.0]) == 0.0  # single return


def test_summarise_bundles_everything():
    summary = summarise([100, -50], [10_000, 10_100, 10_050])
    assert summary["num_trades"] == 2.0
    assert summary["win_rate"] == 0.5
    assert summary["profit_factor"] == 2.0
    assert summary["total_pnl"] == 50.0
    assert summary["total_return"] == pytest.approx(0.005)
    assert "max_drawdown" in summary and "sharpe_ratio" in summary
