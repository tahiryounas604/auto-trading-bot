"""Backtester tests — exact PnL math on a fixed dataset."""

from trading_bot.backtester import Backtester
from trading_bot.data import Bar
from trading_bot.risk import RiskManager
from trading_bot.strategy import Strategy


class FixedSignalStrategy(Strategy):
    """Test-only strategy returning a fixed signal list."""

    def __init__(self, signals):
        self._signals = signals
        self.name = "fixed"

    def generate_signals(self, closes):
        return list(self._signals)


def _bar(close, high=None, low=None, ts="2025-01-01"):
    return Bar(ts, close, high if high is not None else close,
               low if low is not None else close, close, 100.0)


def test_backtest_exact_pnl_no_fees():
    # Buy at bar 1 close 100, sell at bar 4 close 130.
    # risk 1% of 10,000 = 100; stop 95 -> per-unit risk 5 -> 20 units.
    # PnL = 20 * (130 - 100) = 600; final cash 10,600.
    bars = [_bar(c) for c in [100, 100, 110, 120, 130]]
    risk = RiskManager(risk_pct=1.0, stop_loss_pct=5.0, take_profit_pct=0)
    result = Backtester(FixedSignalStrategy([0, 1, 0, 0, -1]),
                        risk_manager=risk).run(bars)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_price == 100.0
    assert trade.exit_price == 130.0
    assert trade.units == 20.0
    assert trade.pnl == 600.0
    assert trade.exit_reason == "signal"
    assert result.final_equity == 10_600.0
    assert result.metrics["num_trades"] == 1.0
    assert result.metrics["win_rate"] == 1.0


def test_backtest_stop_loss_exit():
    # Buy at 100 (stop 95). Bar 2 low 90 -> exit at the stop, 95.
    # PnL = 20 * (95 - 100) = -100.
    bars = [_bar(100), _bar(100), _bar(95, high=100, low=90), _bar(96)]
    risk = RiskManager(risk_pct=1.0, stop_loss_pct=5.0, take_profit_pct=0)
    result = Backtester(FixedSignalStrategy([0, 1, 0, 0]),
                        risk_manager=risk).run(bars)
    assert len(result.trades) == 1
    assert result.trades[0].exit_price == 95.0
    assert result.trades[0].exit_reason == "stop_loss"
    assert result.trades[0].pnl == -100.0


def test_backtest_take_profit_exit():
    # Buy at 100, target 104. Bar 2 high 110 -> exit at 104.
    bars = [_bar(100), _bar(100), _bar(108, high=110, low=105), _bar(108)]
    risk = RiskManager(risk_pct=1.0, stop_loss_pct=5.0, take_profit_pct=4.0)
    result = Backtester(FixedSignalStrategy([0, 1, 0, 0]),
                        risk_manager=risk).run(bars)
    assert len(result.trades) == 1
    assert result.trades[0].exit_price == 104.0
    assert result.trades[0].exit_reason == "take_profit"
    assert result.trades[0].pnl == 80.0  # 20 * 4


def test_backtest_open_position_closed_at_end_of_data():
    bars = [_bar(c) for c in [100, 100, 110]]
    risk = RiskManager(risk_pct=1.0, stop_loss_pct=5.0, take_profit_pct=0)
    result = Backtester(FixedSignalStrategy([0, 1, 0]),
                        risk_manager=risk).run(bars)
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "end_of_data"
    assert result.trades[0].pnl == 200.0  # 20 * (110 - 100)
    assert result.final_equity == 10_200.0


def test_backtest_fees_reduce_pnl():
    # 1% fee on entry (20*100=2000 -> 20) and exit (20*130=2600 -> 26).
    # PnL = 2600 - 26 - 2000 - 20 = 554.
    bars = [_bar(c) for c in [100, 100, 110, 120, 130]]
    risk = RiskManager(risk_pct=1.0, stop_loss_pct=5.0, take_profit_pct=0)
    result = Backtester(FixedSignalStrategy([0, 1, 0, 0, -1]),
                        risk_manager=risk, fee_pct=1.0).run(bars)
    assert result.trades[0].pnl == 554.0
    assert result.final_equity == 10_554.0


def test_backtest_no_signals_no_trades():
    bars = [_bar(c) for c in [100, 101, 102]]
    result = Backtester(FixedSignalStrategy([0, 0, 0])).run(bars)
    assert result.trades == []
    assert result.final_equity == 10_000.0
    assert result.metrics["win_rate"] == 0.0
    assert len(result.equity_curve) == 3


def test_backtest_sell_without_position_is_ignored():
    bars = [_bar(c) for c in [100, 101, 102]]
    result = Backtester(FixedSignalStrategy([-1, -1, -1])).run(bars)
    assert result.trades == []


def test_backtest_rejects_empty_bars_and_bad_cash():
    import pytest

    with pytest.raises(ValueError):
        Backtester(FixedSignalStrategy([])).run([])
    with pytest.raises(ValueError):
        Backtester(FixedSignalStrategy([]), initial_cash=0)
