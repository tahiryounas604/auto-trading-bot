"""Risk management: position sizing, stop-loss / take-profit levels and
a max-drawdown circuit breaker.

All money math is explicit and unit-tested. Nothing here places a real
order — it only computes sizes and decides whether trading may continue.
"""

from __future__ import annotations


class RiskManager:
    """Position sizing by fixed fractional risk plus a drawdown breaker.

    Parameters
    ----------
    risk_pct:
        Percent of the account balance risked on a single trade
        (e.g. 1.0 means risk at most 1% of balance per trade).
    stop_loss_pct:
        Default stop-loss distance from the entry price, in percent.
    take_profit_pct:
        Default take-profit distance from the entry price, in percent.
        ``0`` disables take-profit.
    max_drawdown_pct:
        Circuit breaker: trading halts once equity has fallen this far
        (in percent) from its peak. ``0`` disables the breaker.
    max_position_pct:
        Hard cap: one position may never use more than this percent of
        the account balance as notional value.
    """

    def __init__(
        self,
        risk_pct: float = 1.0,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0,
        max_drawdown_pct: float = 10.0,
        max_position_pct: float = 100.0,
    ) -> None:
        for label, value in (
            ("risk_pct", risk_pct),
            ("stop_loss_pct", stop_loss_pct),
            ("take_profit_pct", take_profit_pct),
            ("max_drawdown_pct", max_drawdown_pct),
            ("max_position_pct", max_position_pct),
        ):
            if value < 0:
                raise ValueError(f"{label} must be >= 0")
        self.risk_pct = risk_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_position_pct = max_position_pct
        self._peak_equity: float | None = None
        self.tripped = False

    # -- position sizing -------------------------------------------------
    def position_size(
        self,
        balance: float,
        entry_price: float,
        stop_price: float,
    ) -> float:
        """Units to buy so that a stop-out loses ~``risk_pct`` of balance.

        ``risk_amount / |entry - stop|``, capped so the notional value
        never exceeds ``max_position_pct`` of the balance. Returns 0.0
        for any invalid input (zero/negative balance, price, risk, or a
        stop equal to the entry).
        """
        if balance <= 0 or entry_price <= 0 or self.risk_pct <= 0:
            return 0.0
        per_unit_risk = abs(entry_price - stop_price)
        if per_unit_risk <= 0:
            return 0.0
        risk_amount = balance * self.risk_pct / 100.0
        units = risk_amount / per_unit_risk
        max_notional = balance * self.max_position_pct / 100.0
        return min(units, max_notional / entry_price)

    def stop_price(self, entry_price: float, side: str = "long") -> float:
        """Stop-loss price for an entry. Long: below entry; short: above
        (shorts are not traded in v0.1, but the math is kept symmetric)."""
        if side == "long":
            return entry_price * (1.0 - self.stop_loss_pct / 100.0)
        if side == "short":
            return entry_price * (1.0 + self.stop_loss_pct / 100.0)
        raise ValueError("side must be 'long' or 'short'")

    def take_profit_price(self, entry_price: float, side: str = "long") -> float | None:
        """Take-profit price, or ``None`` when take-profit is disabled."""
        if self.take_profit_pct <= 0:
            return None
        if side == "long":
            return entry_price * (1.0 + self.take_profit_pct / 100.0)
        if side == "short":
            return entry_price * (1.0 - self.take_profit_pct / 100.0)
        raise ValueError("side must be 'long' or 'short'")

    # -- circuit breaker ---------------------------------------------------
    def update(self, equity: float) -> bool:
        """Feed the current equity; returns ``True`` while trading is
        allowed, ``False`` once the breaker has tripped. Once tripped it
        stays tripped until :meth:`reset` is called."""
        if self._peak_equity is None or equity > self._peak_equity:
            self._peak_equity = equity
        if self.max_drawdown_pct > 0 and self._peak_equity > 0:
            drawdown_pct = (self._peak_equity - equity) / self._peak_equity * 100.0
            if drawdown_pct >= self.max_drawdown_pct:
                self.tripped = True
        return not self.tripped

    def reset(self) -> None:
        """Clear the breaker state (e.g. after a manual review)."""
        self._peak_equity = None
        self.tripped = False

    @property
    def peak_equity(self) -> float | None:
        return self._peak_equity
