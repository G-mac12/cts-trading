"""Robustness (§9 / Task D): distrust single runs. Report distributions, not peaks.

  * Universe subsampling: random 2/3 of symbols across several seeds -> spread of
    outcomes. A real edge survives dropping a third of the names.
  * Parameter neighbourhood: vary parameters around the starting set and report the
    full distribution. A strategy that only works at one exact point is overfit.
"""
from __future__ import annotations

import itertools
from dataclasses import replace
from typing import Dict, List

import numpy as np

from cts.engine.backtest import StrategyParams


def subsample_symbols(symbols: List[str], frac: float, seed: int) -> List[str]:
    rng = np.random.RandomState(seed)
    n = max(1, int(len(symbols) * frac))
    idx = rng.choice(len(symbols), size=n, replace=False)
    return [symbols[i] for i in sorted(idx.tolist())]


def neighbourhood(base: StrategyParams, axes: Dict[str, List]) -> List[StrategyParams]:
    """Cartesian product of variations. ``axes`` keys are StrategyParams field names."""
    keys = list(axes.keys())
    out: List[StrategyParams] = []
    for combo in itertools.product(*[axes[k] for k in keys]):
        out.append(replace(base, **dict(zip(keys, combo))))
    return out


def distribution(values: List[float]) -> Dict[str, float]:
    a = np.array([v for v in values if np.isfinite(v)], dtype="float64")
    if a.size == 0:
        return {k: 0.0 for k in ("mean", "std", "min", "p25", "median", "p75", "max", "n")}
    return {
        "mean": float(a.mean()), "std": float(a.std(ddof=1)) if a.size > 1 else 0.0,
        "min": float(a.min()), "p25": float(np.percentile(a, 25)),
        "median": float(np.median(a)), "p75": float(np.percentile(a, 75)),
        "max": float(a.max()), "n": float(a.size),
    }
