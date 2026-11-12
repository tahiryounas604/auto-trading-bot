"""Risk-manager tests, including edge cases."""

import pytest

from trading_bot.risk import RiskManager


def test_position_size_basic():
    # risk 1% of 10,000 = 100; per-unit risk 100-95 = 5 -> 20 units.
    rm = RiskManager(risk_pct=1.0)
    assert rm.position_size(10_000, 100, 95) == 20.0


def test_position_size_zero_when_stop_equals_entry():
    assert RiskManager().position_size(10_000, 100, 100) == 0.0


def test_position_size_zero_on_invalid_inputs():
    rm = RiskManager(risk_pct=1.0)
    assert rm.position_size(0, 100, 95) == 0.0
    assert rm.position_size(-500, 100, 95) == 0.0
    assert rm.position_size(10_000, 0, 95) == 0.0
    assert rm.position_size(10_000, -100, 95) == 0.0
    assert RiskManager(risk_pct=0).position_size(10_000, 100, 95) == 0.0


def test_position_size_capped_by_max_position_pct():
    # Uncapped: risk 10% -> 1000 risk / 1 per-unit = 1000 units (100k notional).
    # Cap 50% of 10,000 = 5,000 notional -> 50 units at entry 100.
    rm = RiskManager(risk_pct=10.0, max_position_pct=50.0)
    assert rm.position_size(10_000, 100, 99) == 50.0


def test_stop_and_target_prices():
    rm = RiskManager(stop_loss_pct=2.0, take_profit_pct=4.0)
    assert rm.stop_price(100) == 98.0
    assert rm.take_profit_price(100) == 104.0
    assert rm.stop_price(100, "short") == 102.0
    assert rm.take_profit_price(100, "short") == 96.0
    with pytest.raises(ValueError):
        rm.stop_price(100, "sideways")


def test_take_profit_disabled_returns_none():
    assert RiskManager(take_profit_pct=0).take_profit_price(100) is None


def test_circuit_breaker_trips_at_limit_and_stays_tripped():
    rm = RiskManager(max_drawdown_pct=10.0)
    assert rm.update(10_000) is True
    assert rm.update(9_500) is True  # 5% down: still ok
    assert rm.update(9_000) is False  # exactly 10% down: tripped
    assert rm.tripped is True
    assert rm.update(12_000) is False  # stays tripped even after recovery
    rm.reset()
    assert rm.tripped is False
    assert rm.update(12_000) is True


def test_circuit_breaker_disabled_when_zero():
    rm = RiskManager(max_drawdown_pct=0)
    assert rm.update(10_000) is True
    assert rm.update(1) is True


def test_negative_config_rejected():
    with pytest.raises(ValueError):
        RiskManager(risk_pct=-1)
    with pytest.raises(ValueError):
        RiskManager(max_drawdown_pct=-5)
