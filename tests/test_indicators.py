"""Hand-computed fixtures for indicators. Every expected value is derived by hand
in the comments so a reviewer can verify without running anything."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cts.indicators import (
    atr,
    donchian_lower,
    donchian_upper,
    pct_return,
    rvol,
    sma,
    true_range,
)


def _idx(n):
    return pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")


def test_donchian_upper_excludes_today_and_shifts():
    high = pd.Series([10, 11, 12, 13, 14], index=_idx(5))
    # rolling max win3: [-, -, 12, 13, 14]; shift1: [-, -, -, 12, 13]
    out = donchian_upper(high, 3)
    assert np.isnan(out.iloc[2])
    assert out.iloc[3] == 12
    assert out.iloc[4] == 13


def test_donchian_lower_excludes_today_and_shifts():
    low = pd.Series([10, 9, 8, 7, 6], index=_idx(5))
    # rolling min win3: [-, -, 8, 7, 6]; shift1: [-, -, -, 8, 7]
    out = donchian_lower(low, 3)
    assert out.iloc[3] == 8
    assert out.iloc[4] == 7


def test_true_range():
    high = pd.Series([10, 12, 13, 12], index=_idx(4))
    low = pd.Series([8, 9, 11, 8], index=_idx(4))
    close = pd.Series([9, 11, 12, 9], index=_idx(4))
    # TR0 = H-L = 2
    # TR1 = max(12-9, |12-9|, |9-9|) = 3
    # TR2 = max(13-11, |13-11|, |11-11|) = 2
    # TR3 = max(12-8, |12-12|, |8-12|) = 4
    tr = true_range(high, low, close)
    assert list(tr.to_numpy()) == [2, 3, 2, 4]


def test_atr_sma():
    high = pd.Series([10, 12, 13, 12], index=_idx(4))
    low = pd.Series([8, 9, 11, 8], index=_idx(4))
    close = pd.Series([9, 11, 12, 9], index=_idx(4))
    # TR = [2,3,2,4]; sma period2: [-, 2.5, 2.5, 3.0]
    out = atr(high, low, close, period=2, method="sma")
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == pytest.approx(2.5)
    assert out.iloc[2] == pytest.approx(2.5)
    assert out.iloc[3] == pytest.approx(3.0)


def test_atr_wilder():
    high = pd.Series([10, 12, 13, 12], index=_idx(4))
    low = pd.Series([8, 9, 11, 8], index=_idx(4))
    close = pd.Series([9, 11, 12, 9], index=_idx(4))
    # TR = [2,3,2,4]; period2 wilder:
    # seed@idx1 = mean(2,3) = 2.5
    # idx2 = (2.5*1 + 2)/2 = 2.25
    # idx3 = (2.25*1 + 4)/2 = 3.125
    out = atr(high, low, close, period=2, method="wilder")
    assert out.iloc[1] == pytest.approx(2.5)
    assert out.iloc[2] == pytest.approx(2.25)
    assert out.iloc[3] == pytest.approx(3.125)


def test_rvol_excludes_current_bar():
    vol = pd.Series([100, 200, 300, 400], index=_idx(4))
    # avg = rolling mean win2 shift1: [-, -, 150, 250]
    # rvol = vol/avg: idx2 = 300/150 = 2.0 ; idx3 = 400/250 = 1.6
    out = rvol(vol, 2)
    assert out.iloc[2] == pytest.approx(2.0)
    assert out.iloc[3] == pytest.approx(1.6)


def test_sma_includes_current_bar():
    s = pd.Series([10, 20, 30, 40], index=_idx(4))
    out = sma(s, 2)  # [-, 15, 25, 35]
    assert out.iloc[1] == pytest.approx(15)
    assert out.iloc[3] == pytest.approx(35)


def test_pct_return():
    close = pd.Series([10, 11, 12], index=_idx(3))
    out = pct_return(close, 1)  # [-, 0.1, 0.0909...]
    assert out.iloc[1] == pytest.approx(0.1)
    assert out.iloc[2] == pytest.approx(12 / 11 - 1)
