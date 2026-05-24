from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cts.s3.bootstrap import (avg_pairwise_corr, ci, effective_n, maxdd_stat,
                              pf_stat, sharpe_stat, stationary_bootstrap)


def test_effective_n_matches_spec_table():
    # spec: N=30, rho=0.5 -> ~1.9 independent bets
    assert abs(effective_n(30, 0.5) - 1.94) < 0.05
    assert effective_n(30, 0.0) == 30.0          # independent -> no discount
    assert effective_n(1, 0.5) == 1.0


def test_avg_pairwise_corr():
    base = np.random.default_rng(0).normal(size=300)
    perfectly = pd.DataFrame({"a": base, "b": base, "c": base})
    assert avg_pairwise_corr(perfectly) > 0.99
    rng = np.random.default_rng(1)
    indep = pd.DataFrame({c: rng.normal(size=300) for c in "abcd"})
    assert abs(avg_pairwise_corr(indep)) < 0.2


def test_stat_helpers():
    assert pf_stat(np.array([0.1, -0.05, 0.2, -0.05])) == pytest.approx(3.0)
    assert pf_stat(np.array([0.1, 0.2])) == float("inf")
    assert sharpe_stat(np.array([0.0, 0.0, 0.0])) == 0.0
    eq_daily = pd.Series([100, 120, 90, 150]).pct_change().dropna().to_numpy()
    assert abs(maxdd_stat(eq_daily) - (-0.25)) < 1e-9


def test_bootstrap_ci_brackets_point_estimate():
    rng = np.random.default_rng(3)
    daily = rng.normal(0.002, 0.02, size=600)            # positive-drift series
    dist = stationary_bootstrap(daily, sharpe_stat, n_boot=400, mean_block=10)
    lo, hi = ci(dist)
    point = sharpe_stat(daily)
    assert lo < point < hi                                # CI brackets the point estimate
    assert hi - lo > 0
