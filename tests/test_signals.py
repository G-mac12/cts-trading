from __future__ import annotations

import pandas as pd

from cts.strategy.signals import breakout_signal, pullback_signal


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


def test_pullback_fires_on_dip_and_recover_in_uptrend():
    # close dips to/below the 2-day MA at idx5 then closes back above it (and above the
    # 3-day trend MA) at idx6 -> pullback entry only at idx6.
    close = [10, 11, 12, 13, 14, 13, 15]
    df = pd.DataFrame({"close": close}, index=_idx(7))
    sig = pullback_signal(df, ma_trend=3, ma_pull=2)
    assert bool(sig.iloc[6]) is True
    assert sig.sum() == 1


def test_pullback_needs_uptrend():
    # steadily falling: never above the trend MA -> never fires
    df = pd.DataFrame({"close": [20, 19, 18, 17, 16, 15, 14]}, index=_idx(7))
    assert pullback_signal(df, ma_trend=3, ma_pull=2).sum() == 0
