"""S3 ranking signal — risk-adjusted relative-strength momentum (pure functions).

signal[t] = return over [t-skip-lookback, t-skip]  /  realized daily vol over that window.

The skip drops the most-recent `skip` days (short-term reversal). The vol denominator
makes it risk-adjusted, so it differs from S1's raw 30d return on BOTH lookback and
risk-adjustment. For cross-sectional ranking only the ordering matters; the value is a
return-per-unit-vol relative-strength score. No lookahead (everything is trailing).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def realized_vol(close: pd.Series, window: int, skip: int = 0) -> pd.Series:
    """Std of daily returns over `window` bars ending `skip` days ago."""
    daily = close.pct_change()
    return daily.shift(skip).rolling(window, min_periods=max(2, window // 2)).std()


def risk_adjusted_momentum(close: pd.Series, lookback: int = 90, skip: int = 7,
                           vol_window: int = 90) -> pd.Series:
    """Return-per-unit-vol relative-strength score (NaN where insufficient history)."""
    px_now = close.shift(skip)
    px_then = close.shift(skip + lookback)
    ret = px_now / px_then - 1.0
    vol = realized_vol(close, vol_window, skip)
    sig = ret / vol
    return sig.replace([np.inf, -np.inf], np.nan)
