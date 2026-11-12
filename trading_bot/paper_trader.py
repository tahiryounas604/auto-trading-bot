"""Paper-trading engine: simulated fills against a virtual cash balance.

No real orders are placed and no broker is contacted. A buy fills at
``price * (1 + slippage)`` and a sell at ``price * (1 - slippage)``;
``fee_pct`` is charged on the notional of every fill. Orders are
rejected (returning ``False``) when the circuit breaker has tripped,
when there is not enough cash, or when selling more than is held.
Position sizing uses the :class:`RiskManager` when no explicit size
is given.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .risk import RiskManager


@dataclass
class Fill:
    side: str  # "buy" | "sell"
    symbol: str
    price: float  # requested price (before slippage)
    fill_price: float  # price actually paid/received
    units: float
    fee: float
    cash_after: float


@dataclass
class Position:
    symbol: str
    units: float
    entry_price: float
    stop_price: float
    take_profit_price: float | None = None


class PaperTrader:
    def __init__(
        self,
        initial_cash: float = 10_000.0,
        risk_manager: RiskManager | None = None,
        slippage_pct: float = 0.0,
        fee_pct: float = 0.0,
    ) -> None:
        if initial_cash <= 0:
            raise ValueError("initial_cash must be > 0")
        if slippage_pct < 0 or fee_pct < 0:
            raise ValueError("slippage_pct and fee_pct must be >= 0")
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.risk = risk_manager or RiskManager()
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct
        self.positions: dict[str, Position] = {}
        self.fills: list[Fill] = []
        self.halted = False

    # -- orders ------------------------------------------------------------
    def buy(
        self,
        symbol: str,
        price: float,
        units: float | None = None,
    ) -> Fill | None:
        """Simulated market buy. Returns the fill, or ``None`` when the
        order is rejected. When ``units`` is omitted, size is computed
        from the risk manager (``risk_pct`` of cash at risk to the stop)."""
        if self.halted or self.risk.tripped or price <= 0:
            return None
        if symbol in self.positions:
            return None  # one open position per symbol in v0.1
        stop = self.risk.stop_price(price)
        size = units if units is not None else self.risk.position_size(
            self.cash, price, stop
        )
        if size <= 0:
            return None
        fill_price = price * (1.0 + self.slippage_pct / 100.0)
        cost = size * fill_price
        fee = cost * self.fee_pct / 100.0
        if cost + fee > self.cash:
            return None
        self.cash -= cost + fee
        self.positions[symbol] = Position(
            symbol=symbol,
            units=size,
            entry_price=fill_price,
            stop_price=stop,
            take_profit_price=self.risk.take_profit_price(price),
        )
        fill = Fill("buy", symbol, price, fill_price, size, fee, self.cash)
        self.fills.append(fill)
        self._refresh_breaker(symbol, fill_price)
        return fill

    def sell(self, symbol: str, price: float, units: float | None = None) -> Fill | None:
        """Simulated market sell of an open position (whole position when
        ``units`` is omitted). Returns the fill or ``None`` if rejected."""
        if self.halted or price <= 0:
            return None
        position = self.positions.get(symbol)
        if position is None:
            return None
        size = position.units if units is None else units
        if size <= 0 or size > position.units:
            return None
        fill_price = price * (1.0 - self.slippage_pct / 100.0)
        proceeds = size * fill_price
        fee = proceeds * self.fee_pct / 100.0
        self.cash += proceeds - fee
        position.units -= size
        if position.units == 0:
            del self.positions[symbol]
        fill = Fill("sell", symbol, price, fill_price, size, fee, self.cash)
        self.fills.append(fill)
        self._refresh_breaker(symbol, fill_price)
        return fill

    def check_stops(self, symbol: str, high: float, low: float) -> Fill | None:
        """Check the open position against its stop-loss / take-profit
        using the latest bar's high and low. Returns the exit fill when
        a level is hit, otherwise ``None``."""
        position = self.positions.get(symbol)
        if position is None:
            return None
        if low <= position.stop_price:
            return self.sell(symbol, position.stop_price)
        if (
            position.take_profit_price is not None
            and high >= position.take_profit_price
        ):
            return self.sell(symbol, position.take_profit_price)
        return None

    # -- state ---------------------------------------------------------------
    def equity(self, prices: dict[str, float]) -> float:
        """Cash plus the current value of all open positions."""
        total = self.cash
        for symbol, position in self.positions.items():
            total += position.units * prices.get(symbol, position.entry_price)
        return total

    def halt(self) -> None:
        """Manually halt trading (e.g. after a manual review)."""
        self.halted = True

    def _refresh_breaker(self, symbol: str, price: float) -> None:
        """Feed the breaker the current equity, marking the just-traded
        symbol at its fill price and other positions at entry price."""
        equity = self.cash
        for sym, position in self.positions.items():
            mark = price if sym == symbol else position.entry_price
            equity += position.units * mark
        self.risk.update(equity)
