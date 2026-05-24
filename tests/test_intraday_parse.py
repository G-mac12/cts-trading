"""The intraday OHLCV parser must KEEP the bar timestamp (not collapse to the date,
which the daily parser does) and must not hit the RangeIndex->NaN reindex bug."""
from __future__ import annotations

import pandas as pd

from cts.data.coinapi import rows_to_intraday_ohlcv, rows_to_ohlcv

ROWS = [
    {"time_period_start": "2022-01-01T00:00:00.0000000Z", "price_open": 1.0, "price_high": 2.0,
     "price_low": 0.5, "price_close": 1.5, "volume_traded": 100.0},
    {"time_period_start": "2022-01-01T01:00:00.0000000Z", "price_open": 1.5, "price_high": 2.5,
     "price_low": 1.0, "price_close": 2.0, "volume_traded": 200.0},
    {"time_period_start": "2022-01-01T02:00:00.0000000Z", "price_open": 2.0, "price_high": 2.2,
     "price_low": 1.8, "price_close": 1.9, "volume_traded": 150.0},
]


def test_intraday_keeps_hourly_timestamps():
    df = rows_to_intraday_ohlcv(ROWS)
    assert len(df) == 3                       # NOT collapsed to one daily bar
    assert list(df.index.hour) == [0, 1, 2]
    assert str(df.index.tz) == "UTC"
    assert df["close"].tolist() == [1.5, 2.0, 1.9]   # real values, no NaN reindex
    assert not df.isna().any().any()


def test_daily_parser_still_collapses_to_date():
    # contrast: the daily parser normalizes to date, so the same 3 hourly rows -> 1 row
    df = rows_to_ohlcv(ROWS)
    assert len(df) == 1
    assert df.index[0] == pd.Timestamp("2022-01-01", tz="UTC")


def test_intraday_empty():
    df = rows_to_intraday_ohlcv([])
    assert df.empty and list(df.columns) == ["open", "high", "low", "close", "volume"]
