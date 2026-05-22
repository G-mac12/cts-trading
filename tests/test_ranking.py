from __future__ import annotations

import numpy as np
import pandas as pd

from cts.strategy.ranking import top_tier_mask


def test_top_tier_selects_highest_scores():
    scores = pd.Series({"A": 0.5, "B": 0.3, "C": 0.9, "D": np.nan, "E": 0.1})
    # 4 valid; frac 0.5 -> k=ceil(4*0.5)=2 -> top {C(0.9), A(0.5)}
    mask = top_tier_mask(scores, 0.5)
    assert mask["C"] and mask["A"]
    assert not mask["B"] and not mask["E"]
    assert not mask["D"]  # NaN never in top tier


def test_top_tier_ceil_keeps_at_least_one():
    scores = pd.Series({"A": 0.5, "B": 0.3, "C": 0.9, "E": 0.1})
    # frac 0.1 -> k=ceil(4*0.1)=ceil(0.4)=1 -> only the single best (C)
    mask = top_tier_mask(scores, 0.1)
    assert mask.sum() == 1 and mask["C"]


def test_top_tier_all_nan_selects_none():
    scores = pd.Series({"A": np.nan, "B": np.nan})
    assert top_tier_mask(scores, 0.5).sum() == 0
