"""OHLCV data loading.

CSV format (one row per bar, header required)::

    timestamp,open,high,low,close,volume
    2025-01-01,100.0,101.5,99.0,100.8,1234.5

``timestamp`` is kept as a plain string so any date format works;
the backtester only needs the numeric columns.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class Bar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def load_csv(path: str) -> list[Bar]:
    """Load OHLCV bars from a CSV file. Raises ``ValueError`` on a
    missing column, a non-numeric value, or an empty file."""
    bars: list[Bar] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: empty file (no header row)")
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        for line_no, row in enumerate(reader, start=2):
            try:
                bars.append(
                    Bar(
                        timestamp=row["timestamp"],
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path}: line {line_no}: bad numeric value: {exc}"
                ) from exc
    if not bars:
        raise ValueError(f"{path}: no data rows")
    return bars


def closes(bars: list[Bar]) -> list[float]:
    return [b.close for b in bars]
