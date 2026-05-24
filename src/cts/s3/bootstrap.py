"""Resampled confidence intervals on the EFFECTIVE sample (spec requirement).

- effective_n: independent-bet count from average pairwise correlation,
  N_eff = N / (1 + (N-1)·ρ̄).
- stationary bootstrap (Politis-Romano): resamples with geometric block lengths so
  serial autocorrelation in the return series is preserved (point-IID bootstrap would
  understate the CI width — exactly where the gate is decided).
- Report PF / Sharpe / maxDD as intervals, not point estimates.
"""
from __future__ import annotations

from typing import Callable, List, Tuple

import numpy as np
import pandas as pd


def avg_pairwise_corr(returns_df: pd.DataFrame) -> float:
    """Mean off-diagonal correlation of a (time x names) daily-return frame."""
    if returns_df.shape[1] < 2:
        return 0.0
    c = returns_df.corr().to_numpy()
    iu = np.triu_indices(c.shape[0], k=1)
    vals = c[iu]
    vals = vals[~np.isnan(vals)]
    return float(np.mean(vals)) if len(vals) else 0.0


def effective_n(nominal_n: float, rho_bar: float) -> float:
    rho_bar = min(max(rho_bar, 0.0), 0.999)
    if nominal_n <= 1:
        return float(nominal_n)
    return nominal_n / (1.0 + (nominal_n - 1.0) * rho_bar)


def pf_stat(trade_returns: np.ndarray) -> float:
    pos = trade_returns[trade_returns > 0].sum()
    neg = -trade_returns[trade_returns < 0].sum()
    return float(pos / neg) if neg > 0 else float("inf")


def sharpe_stat(daily: np.ndarray, periods: int = 365) -> float:
    sd = daily.std(ddof=1)
    return float(daily.mean() / sd * np.sqrt(periods)) if sd > 0 else 0.0


def maxdd_stat(daily: np.ndarray) -> float:
    eq = np.cumprod(1.0 + daily)
    peak = np.maximum.accumulate(eq)
    return float((eq / peak - 1.0).min())


def stationary_bootstrap(x: np.ndarray, stat: Callable, n_boot: int = 1000,
                         mean_block: int = 10, seed: int = 0) -> np.ndarray:
    """Apply `stat` to `n_boot` stationary-bootstrap resamples of 1D array `x`."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype="float64")
    n = len(x)
    if n < 3:
        return np.array([stat(x)] if n else [])
    p = 1.0 / mean_block
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.empty(n, dtype=np.int64)
        i = int(rng.integers(0, n))
        for t in range(n):
            idx[t] = i
            i = int(rng.integers(0, n)) if rng.random() < p else (i + 1) % n
        out[b] = stat(x[idx])
    return out[np.isfinite(out)]


def ci(arr: np.ndarray, lo: float = 5.0, hi: float = 95.0) -> Tuple[float, float]:
    if len(arr) == 0:
        return (float("nan"), float("nan"))
    return (float(np.percentile(arr, lo)), float(np.percentile(arr, hi)))
