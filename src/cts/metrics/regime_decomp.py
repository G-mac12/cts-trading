"""Regime decomposition (§9 — a pass/fail criterion, not a nice-to-have).

Regime is classified independently of the strategy's own switch, from BTC's MA
structure:
  bull: close > MA_long AND MA_short > MA_long
  bear: close < MA_long AND MA_short < MA_long
  chop: everything else
The system must demonstrably go to cash and PRESERVE capital in bear/chop, not
merely profit in bull. We report per-regime exposure, return, drawdown, and the
P&L of trades entered in each regime.
"""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from cts.engine.portfolio import Trade
from cts.indicators import sma
from cts.metrics.performance import max_drawdown

LABELS = ["bull", "bear", "chop"]


def classify_regime(btc_close: pd.Series, ma_short: int = 50, ma_long: int = 100) -> pd.Series:
    long_ma = sma(btc_close, ma_long)
    short_ma = sma(btc_close, ma_short)
    label = pd.Series("chop", index=btc_close.index, dtype="object")
    bull = (btc_close > long_ma) & (short_ma > long_ma)
    bear = (btc_close < long_ma) & (short_ma < long_ma)
    label[bull] = "bull"
    label[bear] = "bear"
    label[long_ma.isna()] = "chop"  # insufficient history -> treat as chop
    return label


def decompose(equity: pd.Series, trades: List[Trade], regime_labels: pd.Series) -> Dict[str, Dict[str, float]]:
    dr = equity.pct_change()
    labels = regime_labels.reindex(equity.index).ffill().fillna("chop")
    total_days = len(equity)

    covered = set()
    for t in trades:
        span = equity.index[(equity.index >= t.entry_date) & (equity.index <= t.exit_date)]
        covered.update(span)

    out: Dict[str, Dict[str, float]] = {}
    for lab in LABELS:
        mask = labels == lab
        days = int(mask.sum())
        sub_r = dr[mask].dropna()
        comp_return = float((1.0 + sub_r).prod() - 1.0) if len(sub_r) else 0.0
        sub_equity = (1.0 + sub_r).cumprod()
        dd = max_drawdown(sub_equity) if len(sub_equity) > 1 else 0.0
        regime_days = set(equity.index[mask])
        exp = len(covered & regime_days) / days if days else 0.0
        in_regime_trades = [t for t in trades if regime_labels.reindex([t.entry_date]).iloc[0] == lab] if len(regime_labels) else []
        out[lab] = {
            "days": float(days),
            "pct_of_period": float(days / total_days) if total_days else 0.0,
            "compounded_return": comp_return,
            "max_drawdown": float(dd),
            "exposure": float(exp),
            "trades_entered": float(len(in_regime_trades)),
            "trades_net_pnl": float(sum(t.net_pnl for t in in_regime_trades)),
        }
    return out
