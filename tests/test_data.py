"""CSV loading tests."""

from pathlib import Path

import pytest

from trading_bot.data import closes, load_csv

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_load_sample_csv():
    bars = load_csv(str(DATA_DIR / "sample_btc_usdt_daily.csv"))
    assert len(bars) == 252
    assert bars[0].timestamp == "2025-01-01"
    assert bars[0].close == pytest.approx(59_880.38)
    assert all(b.high >= b.close >= b.low for b in bars)
    assert all(b.high >= b.open >= b.low for b in bars)
    assert closes(bars)[0] == bars[0].close


def test_load_csv_missing_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("timestamp,open,high,low,close\n2025-01-01,1,1,1,1\n")
    with pytest.raises(ValueError, match="missing columns"):
        load_csv(str(bad))


def test_load_csv_bad_number(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "timestamp,open,high,low,close,volume\n2025-01-01,1,1,1,abc,1\n"
    )
    with pytest.raises(ValueError, match="bad numeric value"):
        load_csv(str(bad))


def test_load_csv_empty_file(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("timestamp,open,high,low,close,volume\n")
    with pytest.raises(ValueError, match="no data rows"):
        load_csv(str(empty))


def test_load_csv_missing_file():
    with pytest.raises(FileNotFoundError):
        load_csv("/nonexistent/file.csv")
