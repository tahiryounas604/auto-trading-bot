# auto-trading-bot

Backtesting, paper trading and risk management for systematic trading
strategies — Python core plus a MetaTrader 5 Expert Advisor (MQL5).
Built clean-room from scratch, standard library only, no dependencies
beyond `pytest` for tests.

> ## ⚠️ RISK WARNING
>
> **Trading can lose money — including all of the money you put in.**
> This software is a research and education tool. It places **no real
> orders** in Python (backtests and paper trading only) and it makes **no
> promise of profit**. Past performance — of a backtest, of this sample
> data, of any strategy — means **nothing** about future results. A
> strategy that "worked" on historical data can and often does lose
> money live. **Paper trade first**, on a demo account, for weeks, before
> you risk a single unit of real currency. Never trade money you cannot
> afford to lose. If you attach the MQL5 EA to a live MetaTrader 5
> account, you do so entirely at your own risk.

## Features

- **Indicators** — SMA, EMA, RSI (Wilder's smoothing), pure Python.
- **Strategies** — a `Strategy` interface plus two built-ins:
  - SMA crossover (trend-following)
  - RSI mean-reversion (buy oversold, sell overbought)
- **Backtester** — runs a strategy over CSV OHLCV data; executes signals
  at the bar close (no look-ahead); honours stop-loss / take-profit
  intra-bar; closes open positions at end of data; optional fees.
- **Risk manager** — position sizing by % risk per trade, stop-loss /
  take-profit levels, max-position cap, max-drawdown circuit breaker.
- **Paper-trading engine** — simulated fills with slippage and fees,
  stop / take-profit checks, order rejection rules, manual halt.
- **Metrics** — win rate, profit factor, max drawdown, Sharpe ratio,
  total return.
- **MQL5 EA** — `mql5/Tytechlabs_SMA_Crossover.mq5` mirrors the Python
  SMA-crossover strategy for MetaTrader 5 (see Known limits).

## Install

Python 3.10+ required. No runtime dependencies.

```bash
git clone <repo-url>
cd auto-trading-bot
pip install pytest --break-system-packages   # tests only
```

## Usage

### CLI

```bash
# Backtest the SMA crossover on the bundled sample data
python3 -m trading_bot backtest --csv data/sample_btc_usdt_daily.csv

# Backtest the RSI strategy with $5,000 and a 0.1% fee
python3 -m trading_bot backtest --csv data/sample_btc_usdt_daily.csv \
  --strategy rsi --cash 5000 --fee-pct 0.1

# Replay the same data through the paper-trading engine
python3 -m trading_bot paper --csv data/sample_btc_usdt_daily.csv
```

Options: `--fast` / `--slow` (SMA periods), `--risk-pct`,
`--stop-loss-pct`, `--take-profit-pct`, `--max-drawdown-pct`,
`--fee-pct`, `--slippage-pct` (paper only), `--symbol` (paper only).

### Library

```python
from trading_bot import Backtester, PaperTrader, RiskManager, SMACrossoverStrategy, load_csv

bars = load_csv("data/sample_btc_usdt_daily.csv")
result = Backtester(SMACrossoverStrategy(10, 30), initial_cash=10_000).run(bars)
print(result.metrics)          # win rate, profit factor, max drawdown, Sharpe...
print(result.final_equity)

trader = PaperTrader(10_000, slippage_pct=0.05)
trader.buy("BTC/USDT", 67_000.0)          # risk-sized automatically
trader.check_stops("BTC/USDT", high=68_000, low=66_000)
print(trader.equity({"BTC/USDT": 67_500.0}))
```

### Your own strategy

```python
from trading_bot import Strategy

class MyStrategy(Strategy):
    def generate_signals(self, closes):
        # Return one signal per close: 1 = buy, -1 = sell, 0 = hold.
        return [0] * len(closes)
```

## Getting market data

The backtester reads CSV files with this header:

```
timestamp,open,high,low,close,volume
2025-01-01,60000.00,60210.50,59880.00,60100.25,1234.5
```

A synthetic 252-row daily sample is bundled at
`data/sample_btc_usdt_daily.csv` (seeded random walk — for smoke tests
and demos only, **not** real market data). To fetch real public data:

- **Binance public API** (no key needed for klines):
  `GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=500`
  returns `[open_time, open, high, low, close, volume, ...]` per row.
- **Stooq** (free daily CSV, no account):
  `https://stooq.com/q/d/l/?s=btcusd&i=d` — columns
  `Date,Open,High,Low,Close,Volume`.
- **Yahoo Finance** via the `yfinance` Python package
  (`pip install yfinance`), then `ticker.history()` and export to CSV.
- **Kraken public API**: `GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440`.

Always check the exchange's terms of use before downloading, and
remember: data quality decides backtest quality. Survivorship bias,
missing corporate actions, and exchange outages all distort results.

## Tests

```bash
python3 -m pytest tests/ -q
```

62 tests, covering indicators (hand-computed values), both strategies,
backtester PnL math (exact figures on a fixed dataset), risk-manager
edge cases, paper-trader fills / slippage / fees / rejections, CSV
loading, metrics, and CLI smoke tests. CI runs the same suite on
Python 3.11 and 3.12 (`.github/workflows/ci.yml`).

## Project layout

```
trading_bot/
  indicators.py     SMA / EMA / RSI
  strategy.py       Strategy interface + SMA crossover + RSI mean-reversion
  risk.py           Position sizing, stop / target, drawdown circuit breaker
  backtester.py     Historical simulation over OHLCV bars
  paper_trader.py   Simulated live engine (fills, slippage, fees, stops)
  metrics.py        Win rate, profit factor, max drawdown, Sharpe
  data.py           OHLCV CSV loading
  cli.py            `backtest` and `paper` commands
data/
  sample_btc_usdt_daily.csv   Synthetic 252-row sample
mql5/
  Tytechlabs_SMA_Crossover.mq5
tests/              pytest suite (62 tests)
```

## Known limits (honest)

- **Long-only.** No short selling in v0.1 (the risk manager has the
  short-side math; the backtester and paper trader do not use it yet).
- **One open position per symbol** in the paper trader; the backtester
  holds at most one position at a time.
- **No live trading in Python.** The Python code never connects to a
  broker or exchange. Live execution exists only as the MQL5 EA.
- **MQL5 EA not compiled or tested.** MetaTrader 5 / MetaEditor run
  only on Windows (or Wine); this Linux VM cannot compile or run it.
  The EA was written by hand to mirror the Python strategy and must be
  compiled in MetaEditor and strategy-tested on a demo account before
  any use. Treat it as unreviewed-by-compiler code until then.
- **Fills are simulated.** Backtests fill at the bar close; the paper
  trader fills at the requested price ± slippage. Real markets have
  gaps, partial fills, and slippage that no simulation reproduces.
- **Sample data is synthetic.** It is a seeded random walk, not real
  market history — useful for verifying the code runs, useless for
  judging a strategy.
- **No walk-forward / out-of-sample tooling yet.** Optimising strategy
  parameters on the same data you test on will overfit; v0.1 does not
  stop you from doing that.
- **No profit claims anywhere in this project, by design.** Any return
  figure you see from the sample data is an artefact of synthetic data.

## License

GPL-3.0 — see `LICENSE`.

Built by Tahir Younas — Penetration Tester & Application Security Engineer — https://www.linkedin.com/in/tahiryounas604 | Tytechlabs
