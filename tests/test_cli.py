"""CLI smoke tests — run the real commands end to end."""

from pathlib import Path

import pytest

from trading_bot.cli import main

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE = str(DATA_DIR / "sample_btc_usdt_daily.csv")


def test_cli_backtest_sma(capsys):
    assert main(["backtest", "--csv", SAMPLE]) == 0
    out = capsys.readouterr().out
    assert "strategy:   sma_10_30" in out
    assert "bars:       252" in out
    assert "trades:" in out


def test_cli_backtest_rsi(capsys):
    assert main(["backtest", "--csv", SAMPLE, "--strategy", "rsi"]) == 0
    assert "strategy:   rsi_14_30_70" in capsys.readouterr().out


def test_cli_paper(capsys):
    assert main(["paper", "--csv", SAMPLE]) == 0
    out = capsys.readouterr().out
    assert "fills:" in out
    assert "equity:" in out
    assert "breaker:" in out


def test_cli_missing_file_returns_error(capsys):
    assert main(["backtest", "--csv", "/nonexistent.csv"]) == 1
    assert "error:" in capsys.readouterr().err


def test_cli_unknown_strategy_rejected():
    with pytest.raises(SystemExit):
        main(["backtest", "--csv", SAMPLE, "--strategy", "magic"])
