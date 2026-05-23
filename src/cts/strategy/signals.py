"""Entry breakout signal (§3.1) — pure, per-symbol.

A breakout fires when the daily close exceeds the prior N-day high (Donchian upper
band) AND breakout-bar volume confirms (RVOL >= threshold). Regime and
cross-sectional gates are applied at the portfolio level in the engine, not here.
"""
from __future__ import annotations

import pandas as pd

from cts.indicators import donchian_upper, rvol, sma


def pullback_signal(df: pd.DataFrame, ma_trend: int = 50, ma_pull: int = 10) -> pd.Series:
    """Pullback-in-uptrend entry: price above the trend MA (uptrend intact) and the
    close crosses back ABOVE the short MA after being at/below it the prior bar.

    A complementary momentum entry that fires during established uptrends (not just
    on fresh breakouts), so it targets the same multi-day moves the fee floor needs.
    No volume-spike gate — pullbacks are naturally low-volume. df needs: close.
    """
    mt = sma(df["close"], ma_trend)
    mp = sma(df["close"], ma_pull)
    sig = (df["close"] > mt) & (df["close"] > mp) & (df["close"].shift(1) <= mp.shift(1))
    return sig.fillna(False).astype(bool)


def breakout_signal(
    df: pd.DataFrame,
    n_entry: int,
    rvol_period: int = 20,
    rvol_min: float = 1.5,
) -> pd.Series:
    """Boolean entry signal per bar. df needs columns: high, close, volume."""
    upper = donchian_upper(df["high"], n_entry)
    rv = rvol(df["volume"], rvol_period)
    sig = (df["close"] > upper) & (rv >= rvol_min)
    return sig.fillna(False).astype(bool)
