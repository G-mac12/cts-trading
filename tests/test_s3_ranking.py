from __future__ import annotations

import numpy as np
import pandas as pd

from cts.s3.cost import CostModel
from cts.s3.ranking import risk_adjusted_momentum


def _idx(n):
    return pd.date_range("2023-01-01", periods=n, freq="D", tz="UTC")


def test_signal_nan_early_then_positive_for_steady_riser():
    close = pd.Series([10.0 + i for i in range(20)], index=_idx(20))
    sig = risk_adjusted_momentum(close, lookback=5, skip=2, vol_window=5)
    assert sig.iloc[:7].isna().all()       # insufficient history early
    assert sig.iloc[-1] > 0                 # steady rise -> positive relative strength


def test_flat_series_signal_is_nan():
    close = pd.Series([10.0] * 20, index=_idx(20))
    sig = risk_adjusted_momentum(close, lookback=5, skip=2, vol_window=5)
    assert sig.dropna().empty               # zero return / zero vol -> NaN, never inf


def test_higher_return_per_vol_ranks_higher():
    steady = pd.Series([10 * 1.01 ** i for i in range(80)], index=_idx(80))   # high ret, low vol
    choppy = pd.Series([10 * (1 + 0.05 * (-1) ** i) for i in range(80)], index=_idx(80))  # ~flat, high vol
    s_steady = risk_adjusted_momentum(steady, 30, 5, 30).iloc[-1]
    s_choppy = risk_adjusted_momentum(choppy, 30, 5, 30).iloc[-1]
    assert s_steady > s_choppy


def test_cost_grows_with_order_size_and_doubles_under_2x():
    base = CostModel(taker_pct=0.40, slippage_base_bps=5.0, slippage_impact_coef=10.0)
    dbl = CostModel(taker_pct=0.40, slippage_base_bps=5.0, slippage_impact_coef=10.0, slippage_mult=2.0)
    small = base.trade_cost(254.0, 1e6)      # £200-ish in a $1M/day name
    big = base.trade_cost(254.0, 1e4)        # same order in a far thinner name
    assert big > small                        # slippage rises as order/ADV rises
    # 2x multiplier doubles the slippage component (fee component unchanged)
    assert dbl.slippage_frac(254.0, 1e6) == 2 * base.slippage_frac(254.0, 1e6)
