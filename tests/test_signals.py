from __future__ import annotations

import pandas as pd

from cts.strategy.signals import breakout_signal


def _idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")


def test_breakout_requires_price_and_volume():
    # idx5: price clears the prior-3-day high (14) at close 18 AND volume spikes -> True
    # idx6: price clears the band (20) at close 25 but volume collapses -> False (vol gate)
    df = pd.DataFrame(
        {
            "high":   [10, 11, 12, 13, 14, 20, 21],
            "low":    [9, 10, 11, 12, 13, 15, 18],
            "close":  [9, 10, 11, 12, 13, 18, 25],
            "volume": [100, 100, 100, 100, 100, 300, 100],
        },
        index=_idx(7),
    )
    sig = breakout_signal(df, n_entry=3, rvol_period=2, rvol_min=1.5)
    assert bool(sig.iloc[5]) is True
    assert bool(sig.iloc[6]) is False
    assert sig.iloc[:5].sum() == 0  # nothing fires before there is a real breakout


def test_breakout_needs_strict_break():
    # close exactly equal to the band must NOT trigger (strict >)
    df = pd.DataFrame(
        {
            "high":   [10, 11, 12, 13],
            "low":    [9, 10, 11, 12],
            "close":  [9, 10, 11, 12],  # idx3 close 12 == prior-3-day high 12
            "volume": [100, 100, 100, 999],
        },
        index=_idx(4),
    )
    sig = breakout_signal(df, n_entry=3, rvol_period=2, rvol_min=1.0)
    assert bool(sig.iloc[3]) is False
