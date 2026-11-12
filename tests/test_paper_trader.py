"""Paper-trader tests — simulated fills, slippage, fees, rejections."""

from trading_bot.paper_trader import PaperTrader
from trading_bot.risk import RiskManager


def test_buy_and_sell_round_trip():
    trader = PaperTrader(10_000)
    fill = trader.buy("BTC/USDT", 100.0, units=10)
    assert fill is not None
    assert fill.fill_price == 100.0
    assert trader.cash == 9_000.0
    out = trader.sell("BTC/USDT", 110.0)
    assert out is not None and out.fill_price == 110.0
    assert trader.cash == 10_100.0
    assert trader.positions == {}


def test_slippage_makes_fills_worse():
    trader = PaperTrader(10_000, slippage_pct=1.0)
    fill = trader.buy("BTC/USDT", 100.0, units=10)
    assert fill.fill_price == 101.0  # pay 1% more
    assert trader.cash == 8_990.0
    out = trader.sell("BTC/USDT", 110.0)
    assert out.fill_price == 108.9  # receive 1% less


def test_fee_charged_on_both_sides():
    trader = PaperTrader(10_000, fee_pct=0.1)
    fill = trader.buy("BTC/USDT", 100.0, units=10)
    assert fill.fee == 1.0  # 0.1% of 1,000
    assert trader.cash == 8_999.0


def test_risk_based_sizing_when_units_omitted():
    # risk 1% of 10,000 = 100; stop 98 -> per-unit risk 2 -> 50 units.
    trader = PaperTrader(10_000, RiskManager(risk_pct=1.0, stop_loss_pct=2.0))
    fill = trader.buy("BTC/USDT", 100.0)
    assert fill is not None
    assert fill.units == 50.0
    assert trader.cash == 5_000.0


def test_rejections():
    trader = PaperTrader(10_000)
    assert trader.sell("BTC/USDT", 100.0) is None  # nothing held
    assert trader.buy("BTC/USDT", 100.0, units=0) is None
    assert trader.buy("BTC/USDT", 100.0, units=-5) is None
    assert trader.buy("BTC/USDT", 0) is None
    assert trader.buy("BTC/USDT", 100.0, units=10_000) is None  # can't afford
    trader.buy("BTC/USDT", 100.0, units=10)
    assert trader.buy("BTC/USDT", 100.0, units=5) is None  # already held
    assert trader.sell("BTC/USDT", 100.0, units=11) is None  # oversell
    assert trader.sell("BTC/USDT", 100.0, units=0) is None


def test_partial_sell_keeps_remainder():
    trader = PaperTrader(10_000)
    trader.buy("BTC/USDT", 100.0, units=10)
    trader.sell("BTC/USDT", 110.0, units=4)
    assert trader.positions["BTC/USDT"].units == 6
    assert trader.cash == 9_440.0  # 9,000 + 440


def test_check_stops_exits_at_stop_loss():
    trader = PaperTrader(10_000, RiskManager(stop_loss_pct=2.0, take_profit_pct=0))
    trader.buy("BTC/USDT", 100.0, units=10)
    assert trader.check_stops("BTC/USDT", high=105, low=99) is None
    fill = trader.check_stops("BTC/USDT", high=105, low=97)
    assert fill is not None
    assert fill.side == "sell"
    assert fill.fill_price == 98.0  # the stop price
    assert trader.positions == {}


def test_check_stops_exits_at_take_profit():
    trader = PaperTrader(10_000, RiskManager(take_profit_pct=4.0))
    trader.buy("BTC/USDT", 100.0, units=10)
    fill = trader.check_stops("BTC/USDT", high=105, low=99)
    assert fill is not None and fill.fill_price == 104.0


def test_halt_blocks_new_orders():
    trader = PaperTrader(10_000)
    trader.halt()
    assert trader.buy("BTC/USDT", 100.0, units=10) is None


def test_equity_marks_positions_at_given_prices():
    trader = PaperTrader(10_000)
    trader.buy("BTC/USDT", 100.0, units=10)
    assert trader.equity({"BTC/USDT": 120.0}) == 10_200.0
    assert trader.equity({"BTC/USDT": 80.0}) == 9_800.0


def test_circuit_breaker_blocks_orders_after_big_loss():
    # max drawdown 5%: buy 10 @100, price falls to 90 -> equity 9,900
    # (1% down, ok). Force the breaker via the risk manager directly,
    # then confirm the trader refuses new orders.
    trader = PaperTrader(10_000, RiskManager(max_drawdown_pct=5.0))
    trader.buy("BTC/USDT", 100.0, units=10)
    trader.risk.update(9_400.0)  # 6% below the 10,000 peak
    assert trader.risk.tripped is True
    assert trader.buy("ETH/USDT", 50.0, units=10) is None
