"""Tytechlabs auto-trading-bot — backtesting, paper trading and risk
management for systematic trading strategies (Python core).

This is a research and education tool. It places no real orders and
makes no promise of profit. See README.md for the risk warning.
"""

from .backtester import Backtester, BacktestResult, Trade
from .data import Bar, load_csv
from .indicators import ema, rsi, sma
from .metrics import max_drawdown, profit_factor, sharpe_ratio, summarise, win_rate
from .paper_trader import Fill, PaperTrader, Position
from .risk import RiskManager
from .strategy import RSIMeanReversionStrategy, SMACrossoverStrategy, Strategy

__version__ = "0.1.0"

__all__ = [
    "Backtester",
    "BacktestResult",
    "Bar",
    "ema",
    "Fill",
    "load_csv",
    "max_drawdown",
    "PaperTrader",
    "Position",
    "profit_factor",
    "RiskManager",
    "rsi",
    "RSIMeanReversionStrategy",
    "sharpe_ratio",
    "sma",
    "SMACrossoverStrategy",
    "Strategy",
    "summarise",
    "Trade",
    "win_rate",
    "__version__",
]
