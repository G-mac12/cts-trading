"""Performance metrics. Pure functions over an equity curve (pd.Series indexed by
date) and a list of trades. Sharpe annualised with 365 (crypto trades 24/7)."""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
import pandas as pd

from cts.engine.portfolio import Trade

PERIODS_PER_YEAR = 365


def total_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] == 0:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1.0)


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    days = (equity.index[-1] - equity.index[0]).days
    if days <= 0:
        return 0.0
    return float((equity.iloc[-1] / equity.iloc[0]) ** (365.0 / days) - 1.0)


def max_drawdown(equity: pd.Series) -> float:
    """Most negative peak-to-trough fraction (e.g. -0.23 = 23% drawdown)."""
    if len(equity) < 2:
        return 0.0
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    return float(dd.min())


def sharpe(daily_returns: pd.Series, periods: int = PERIODS_PER_YEAR) -> float:
    r = daily_returns.dropna()
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(periods))


def sortino(daily_returns: pd.Series, periods: int = PERIODS_PER_YEAR) -> float:
    r = daily_returns.dropna()
    downside = r[r < 0]
    if len(r) < 2 or len(downside) == 0 or downside.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / downside.std(ddof=1) * math.sqrt(periods))


def profit_factor(trades: List[Trade]) -> float:
    gains = sum(t.net_pnl for t in trades if t.net_pnl > 0)
    losses = -sum(t.net_pnl for t in trades if t.net_pnl < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def win_rate(trades: List[Trade]) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.net_pnl > 0)
    return float(wins / len(trades))


def payoff_ratio(trades: List[Trade]) -> float:
    wins = [t.net_pnl for t in trades if t.net_pnl > 0]
    losses = [-t.net_pnl for t in trades if t.net_pnl < 0]
    if not wins or not losses:
        return 0.0
    return float(np.mean(wins) / np.mean(losses))


def expectancy(trades: List[Trade]) -> float:
    if not trades:
        return 0.0
    return float(np.mean([t.net_pnl for t in trades]))


def exposure(trades: List[Trade], equity: pd.Series) -> float:
    """Fraction of trading days with >=1 open position (approx, from trade spans)."""
    if not trades or len(equity) == 0:
        return 0.0
    covered = set()
    idx = equity.index
    for t in trades:
        span = idx[(idx >= t.entry_date) & (idx <= t.exit_date)]
        covered.update(span)
    return float(len(covered) / len(idx))


def metrics_summary(equity: pd.Series, trades: List[Trade]) -> Dict[str, float]:
    dr = equity.pct_change().dropna()
    return {
        "profit_factor": profit_factor(trades),
        "total_return": total_return(equity),
        "cagr": cagr(equity),
        "max_drawdown": max_drawdown(equity),
        "sharpe": sharpe(dr),
        "sortino": sortino(dr),
        "win_rate": win_rate(trades),
        "payoff_ratio": payoff_ratio(trades),
        "expectancy": expectancy(trades),
        "trade_count": float(len(trades)),
        "exposure": exposure(trades, equity),
    }
