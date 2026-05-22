"""Entry breakout signal (§3.1) — pure, per-symbol.

A breakout fires when the daily close exceeds the prior N-day high (Donchian upper
band) AND breakout-bar volume confirms (RVOL >= threshold). Regime and
cross-sectional gates are applied at the portfolio level in the engine, not here.
"""
from __future__ import annotations

import pandas as pd

from cts.indicators import donchian_upper, rvol


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
