from __future__ import annotations

import pandas as pd

from cts.strategy.exits import donchian_exit_signal, stop_hit


def _idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")


def test_donchian_exit_signal():
    # lows -> prior-3-day low at idx3 = min(10,9,8) = 8; close 6 < 8 -> exit True
    df = pd.DataFrame(
        {"low": [10, 9, 8, 7], "close": [11, 10, 9, 6]},
        index=_idx(4),
    )
    sig = donchian_exit_signal(df, n_exit=3)
    assert bool(sig.iloc[3]) is True
    assert sig.iloc[:3].sum() == 0


def test_stop_hit_is_inclusive():
    assert stop_hit(90.0, 90.0) is True   # touching the stop counts
    assert stop_hit(89.9, 90.0) is True
    assert stop_hit(90.1, 90.0) is False
