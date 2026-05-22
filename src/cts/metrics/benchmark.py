"""Buy-and-hold BTC benchmark over a window (the thing the strategy must beat to
justify its complexity)."""
from __future__ import annotations

from typing import Dict

import pandas as pd

from cts.metrics.performance import cagr, max_drawdown, sharpe, total_return


def buy_and_hold(btc_close: pd.Series, start: pd.Timestamp, end: pd.Timestamp,
                 start_equity: float = 1.0) -> pd.Series:
    s = btc_close[(btc_close.index >= pd.Timestamp(start)) & (btc_close.index <= pd.Timestamp(end))].dropna()
    if len(s) == 0:
        return pd.Series(dtype="float64")
    return start_equity * s / s.iloc[0]


def benchmark_summary(btc_close: pd.Series, start: pd.Timestamp, end: pd.Timestamp,
                      start_equity: float = 1.0) -> Dict[str, float]:
    eq = buy_and_hold(btc_close, start, end, start_equity)
    if len(eq) == 0:
        return {"total_return": 0.0, "cagr": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}
    return {
        "total_return": total_return(eq),
        "cagr": cagr(eq),
        "max_drawdown": max_drawdown(eq),
        "sharpe": sharpe(eq.pct_change().dropna()),
    }
