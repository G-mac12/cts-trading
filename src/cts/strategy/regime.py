"""Regime filter (§3.3) — master risk on/off switch.

Risk-on: BTC close > 100d MA AND 50d MA > 100d MA.
Risk-off: no new entries (open positions still managed by their exits; idle = cash).

Pure function. Before enough history exists for the long MA the regime is OFF
(conservative: don't trade what we can't yet classify).
"""
from __future__ import annotations

import pandas as pd

from cts.indicators import sma


def regime_on(btc_close: pd.Series, ma_short: int = 50, ma_long: int = 100) -> pd.Series:
    long_ma = sma(btc_close, ma_long)
    short_ma = sma(btc_close, ma_short)
    on = (btc_close > long_ma) & (short_ma > long_ma)
    return on.fillna(False).astype(bool)
