"""Deterministic technical indicators — pure functions, no lookahead.

Every band/average that feeds a same-day decision is shifted so it uses only data
from *strictly prior* bars. The single exception is moving averages used by the
regime filter and ranking, which legitimately include the current close (they are
computed from data up to and including day t, which is known at day t's close).

No randomness, no global state, no I/O. Inputs/outputs are pandas objects indexed
by a UTC DatetimeIndex (daily, 00:00-anchored).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def donchian_upper(high: pd.Series, n: int) -> pd.Series:
    """Upper Donchian band = highest HIGH over the *prior* n bars (excludes today).

    Shifted by 1 so a breakout test ``close[t] > donchian_upper(high, n)[t]`` can
    actually fire (close[t] <= high[t] always, so an unshifted band never breaks).
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    return high.rolling(window=n, min_periods=n).max().shift(1)


def donchian_lower(low: pd.Series, n: int) -> pd.Series:
    """Lower Donchian band = lowest LOW over the *prior* n bars (excludes today)."""
    if n < 1:
        raise ValueError("n must be >= 1")
    return low.rolling(window=n, min_periods=n).min().shift(1)


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Wilder true range: max(H-L, |H-prevC|, |L-prevC|). First bar = H-L."""
    prev_close = close.shift(1)
    hl = high - low
    hc = (high - prev_close).abs()
    lc = (low - prev_close).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    tr.iloc[0] = (high.iloc[0] - low.iloc[0]) if len(tr) else tr
    return tr


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
    method: str = "wilder",
) -> pd.Series:
    """Average True Range.

    method='wilder' (default, standard ATR): seed = simple mean of the first
    ``period`` true ranges (placed at index period-1), then
    ATR[t] = (ATR[t-1]*(period-1) + TR[t]) / period.
    method='sma': simple rolling mean of TR (easier to hand-verify in tests).
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    tr = true_range(high, low, close)
    if method == "sma":
        return tr.rolling(window=period, min_periods=period).mean()
    if method != "wilder":
        raise ValueError("method must be 'wilder' or 'sma'")

    out = pd.Series(np.nan, index=tr.index, dtype="float64")
    tr_vals = tr.to_numpy(dtype="float64")
    n = len(tr_vals)
    if n < period:
        return out
    seed = float(np.mean(tr_vals[:period]))
    out.iloc[period - 1] = seed
    prev = seed
    for i in range(period, n):
        prev = (prev * (period - 1) + tr_vals[i]) / period
        out.iloc[i] = prev
    return out


def rvol(volume: pd.Series, period: int = 20) -> pd.Series:
    """Relative volume = volume[t] / mean(volume over the prior ``period`` bars).

    The trailing average EXCLUDES the current bar (shift(1)) so a bar's own volume
    does not inflate its baseline.
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    avg = volume.rolling(window=period, min_periods=period).mean().shift(1)
    return volume / avg


def sma(series: pd.Series, n: int) -> pd.Series:
    """Simple moving average over n bars, INCLUDING the current bar (known at close)."""
    if n < 1:
        raise ValueError("n must be >= 1")
    return series.rolling(window=n, min_periods=n).mean()


def pct_return(close: pd.Series, lookback: int) -> pd.Series:
    """Trailing return over ``lookback`` bars: close[t] / close[t-lookback] - 1."""
    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    return close / close.shift(lookback) - 1.0
