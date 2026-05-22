"""Regression test for the OHLCV parser. A previous version built the DataFrame
with a datetime index while the column Series still carried a RangeIndex, which
pandas silently reindexed to ALL-NaN — producing a backtest on empty data and a
false NO-GO. This locks the values in."""
from __future__ import annotations

import pandas as pd

from cts.data.coinapi import rows_to_ohlcv


def test_rows_to_ohlcv_keeps_real_values_and_utc_index():
    rows = [
        {"time_period_start": "2021-01-01T00:00:00.0000000Z", "price_open": 1.0,
         "price_high": 2.0, "price_low": 0.5, "price_close": 1.5, "volume_traded": 100.0},
        {"time_period_start": "2021-01-02T00:00:00.0000000Z", "price_open": 1.5,
         "price_high": 2.5, "price_low": 1.0, "price_close": 2.0, "volume_traded": 200.0},
    ]
    df = rows_to_ohlcv(rows)
    assert df["close"].notna().all()              # the bug: was all-NaN
    assert df["close"].iloc[0] == 1.5 and df["close"].iloc[1] == 2.0
    assert df["volume"].iloc[1] == 200.0
    assert str(df.index.tz) == "UTC"
    assert df.index[0] == pd.Timestamp("2021-01-01", tz="UTC")


def test_rows_to_ohlcv_empty():
    df = rows_to_ohlcv([])
    assert len(df) == 0 and list(df.columns) == ["open", "high", "low", "close", "volume"]
