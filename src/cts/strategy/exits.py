"""Exits (§3.1): close below the M-day low (Donchian lower band) OR the 2*ATR
stop, whichever fires first. Pure helpers; the "whichever first" arbitration and
tie-breaking live in the engine (see engine.backtest)."""
from __future__ import annotations

import pandas as pd

from cts.indicators import donchian_lower


def donchian_exit_signal(df: pd.DataFrame, n_exit: int) -> pd.Series:
    """Boolean exit signal per bar: close < prior M-day low. df needs low, close."""
    lower = donchian_lower(df["low"], n_exit)
    return (df["close"] < lower).fillna(False).astype(bool)


def stop_hit(day_low: float, stop: float) -> bool:
    """True if the day's low touched/breached the stop level."""
    return day_low <= stop
