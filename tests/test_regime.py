from __future__ import annotations

import pandas as pd

from cts.strategy.regime import regime_on


def _idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")


def test_regime_on_requires_both_conditions():
    # close=[10,10,10,10,20], ma_short=2, ma_long=3
    # long MA: idx2=10, idx3=10, idx4=(10+10+20)/3=13.33
    # short MA: idx3=10, idx4=(10+20)/2=15
    # risk-on only at idx4: close 20>13.33 AND short 15>long 13.33
    close = pd.Series([10, 10, 10, 10, 20], index=_idx(5))
    on = regime_on(close, ma_short=2, ma_long=3)
    assert on.iloc[4] is True or bool(on.iloc[4]) is True
    assert bool(on.iloc[3]) is False
    assert bool(on.iloc[0]) is False  # NaN region -> off (conservative)


def test_regime_off_when_below_long_ma():
    close = pd.Series([20, 19, 18, 17, 16, 15], index=_idx(6))
    on = regime_on(close, ma_short=2, ma_long=3)
    # steadily declining: price never above its own rising-from-below long MA here
    assert bool(on.iloc[-1]) is False
