"""Command-line interface.

Usage::

    python3 -m trading_bot backtest --csv data/sample_btc_usdt_daily.csv
    python3 -m trading_bot backtest --csv data.csv --strategy rsi --cash 5000
    python3 -m trading_bot paper --csv data/sample_btc_usdt_daily.csv

The ``paper`` command replays a CSV through the paper-trading engine
(one bar at a time) so you can watch fills, stops and the circuit
breaker behave on real-shaped data without risking money.
"""

from __future__ import annotations

import argparse
import sys

from .backtester import Backtester
from .data import load_csv
from .paper_trader import PaperTrader
from .risk import RiskManager
from .strategy import RSIMeanReversionStrategy, SMACrossoverStrategy


def build_strategy(name: str, fast: int, slow: int):
    if name == "sma":
        return SMACrossoverStrategy(fast_period=fast, slow_period=slow)
    if name == "rsi":
        return RSIMeanReversionStrategy()
    raise ValueError(f"unknown strategy: {name!r} (choose 'sma' or 'rsi')")


def cmd_backtest(args: argparse.Namespace) -> int:
    bars = load_csv(args.csv)
    risk = RiskManager(
        risk_pct=args.risk_pct,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        max_drawdown_pct=args.max_drawdown_pct,
    )
    tester = Backtester(
        build_strategy(args.strategy, args.fast, args.slow),
        initial_cash=args.cash,
        risk_manager=risk,
        fee_pct=args.fee_pct,
    )
    result = tester.run(bars)
    print(f"strategy:   {tester.strategy.name}")
    print(f"bars:       {len(bars)} ({bars[0].timestamp} .. {bars[-1].timestamp})")
    print(f"trades:     {len(result.trades)}")
    print(f"final cash: {result.final_equity:,.2f} (started {args.cash:,.2f})")
    for key, value in result.metrics.items():
        if key in ("num_trades", "total_pnl"):
            continue
        print(f"{key:15} {value:.4f}")
    print(f"total pnl:  {result.metrics['total_pnl']:,.2f}")
    for trade in result.trades:
        print(
            f"  bar {trade.entry_index:>3} -> {trade.exit_index:>3} "
            f"@ {trade.entry_price:,.2f} -> {trade.exit_price:,.2f} "
            f"x{trade.units:.4f} pnl {trade.pnl:+,.2f} ({trade.exit_reason})"
        )
    return 0


def cmd_paper(args: argparse.Namespace) -> int:
    bars = load_csv(args.csv)
    risk = RiskManager(
        risk_pct=args.risk_pct,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        max_drawdown_pct=args.max_drawdown_pct,
    )
    strategy = build_strategy(args.strategy, args.fast, args.slow)
    trader = PaperTrader(
        initial_cash=args.cash,
        risk_manager=risk,
        slippage_pct=args.slippage_pct,
        fee_pct=args.fee_pct,
    )
    from .data import closes as _closes

    signals = strategy.generate_signals(_closes(bars))
    symbol = args.symbol
    for i, bar in enumerate(bars):
        trader.check_stops(symbol, bar.high, bar.low)
        if signals[i] == 1:
            trader.buy(symbol, bar.close)
        elif signals[i] == -1:
            trader.sell(symbol, bar.close)
    equity = trader.equity({symbol: bars[-1].close})
    print(f"strategy:   {strategy.name}")
    print(f"bars:       {len(bars)}")
    print(f"fills:      {len(trader.fills)}")
    print(f"final cash: {trader.cash:,.2f} (started {args.cash:,.2f})")
    print(f"equity:     {equity:,.2f}")
    print(f"open pos:   {len(trader.positions)}")
    print(f"breaker:    {'TRIPPED' if risk.tripped else 'ok'}")
    for fill in trader.fills:
        print(
            f"  {fill.side:4} {fill.units:.4f} {symbol} "
            f"@ {fill.fill_price:,.2f} fee {fill.fee:.2f} cash {fill.cash_after:,.2f}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Backtest and paper-trade systematic strategies (no real orders).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("backtest", "paper"):
        p = sub.add_parser(name)
        p.add_argument("--csv", required=True, help="OHLCV CSV file")
        p.add_argument("--strategy", default="sma", choices=["sma", "rsi"])
        p.add_argument("--fast", type=int, default=10, help="SMA fast period")
        p.add_argument("--slow", type=int, default=30, help="SMA slow period")
        p.add_argument("--cash", type=float, default=10_000.0)
        p.add_argument("--risk-pct", type=float, default=1.0)
        p.add_argument("--stop-loss-pct", type=float, default=2.0)
        p.add_argument("--take-profit-pct", type=float, default=4.0)
        p.add_argument("--max-drawdown-pct", type=float, default=10.0)
        p.add_argument("--fee-pct", type=float, default=0.0)
        if name == "paper":
            p.add_argument("--symbol", default="BTC/USDT")
            p.add_argument("--slippage-pct", type=float, default=0.05)

    args = parser.parse_args(argv)
    try:
        if args.command == "backtest":
            return cmd_backtest(args)
        return cmd_paper(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
