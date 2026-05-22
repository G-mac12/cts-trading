"""Cross-sectional momentum ranking (§3.2).

Rank the eligible universe by trailing 30-day return; the engine only fires in
coins in the top tier. Re-evaluated every 7 days (rebalance cadence lives in the
engine; these are pure per-date helpers).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def top_tier_mask(scores: pd.Series, frac: float) -> pd.Series:
    """Boolean mask (indexed like ``scores``) marking the top ``frac`` by score.

    NaN scores (insufficient history) are never in the top tier. At least one
    symbol is selected when any valid score exists (ceil), matching "top tier"
    rather than an empty set on small universes.
    """
    if not 0 < frac <= 1:
        raise ValueError("frac must be in (0, 1]")
    result = pd.Series(False, index=scores.index)
    valid = scores.dropna()
    if valid.empty:
        return result
    k = max(1, int(np.ceil(len(valid) * frac)))
    top = valid.sort_values(ascending=False, kind="mergesort").head(k).index
    result.loc[top] = True
    return result
