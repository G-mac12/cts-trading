"""End-to-end pipeline smoke test on synthetic data (no API key needed).

Proves the full wiring runs and produces a coherent FINDINGS document:
universe -> walk-forward (fixed + tuned) -> metrics -> regime decomposition ->
benchmark -> robustness -> render. Trade economics are validated separately in
test_engine.py; this test is about the orchestration not falling over.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from cts.data.adapter import SymbolMeta
from cts.pipeline import run_analysis
from cts.reporting.findings import render_findings

U = {
    "exchange": "KRAKEN", "min_24h_usd_volume": 0, "liquidity_window_days": 3,
    "min_history_days": 60, "universe_size_cap": 50, "quote_currencies": ["USD", "USDT"],
    "exclude_stablecoins": True, "exclude_wrapped": True, "exclude_leveraged": True,
    "stablecoin_bases": ["USDT"], "wrapped_bases": ["WETH"], "leveraged_substrings": ["UP", "DOWN"],
}
B = {
    "equity": {"start_gbp": 2000.0, "gbp_usd_rate": 1.27},
    "strategy": {
        "systems": {"system1": {"donchian_entry": 10, "donchian_exit": 5},
                    "system2": {"donchian_entry": 20, "donchian_exit": 10}},
        "atr_period": 14, "atr_stop_mult": 2.0, "rvol_period": 20, "rvol_min": 1.5,
        "risk_per_position_pct": 1.0, "xs_momentum_lookback": 30, "xs_rebalance_days": 7,
        "xs_top_tier_frac": 0.5, "regime": {"ma_long": 50, "ma_short": 20},
    },
    "portfolio": {"max_concurrent_positions": 5, "max_deployed_pct": 50.0},
    "fees": {"taker_pct": 0.40, "maker_pct": 0.25, "exit_uses_maker": False},
    "slippage": {"per_side_pct": 0.15, "sensitivity_pcts": [0.05, 0.15, 0.30]},
    "walk_forward": {"in_sample_months": 6, "out_of_sample_months": 3, "step_months": 3, "rolling": True},
    "robustness": {"subsample_frac": 0.667, "subsample_seeds": [1, 2],
                   "param_neighbourhood": {"donchian_entry": [10, 15], "atr_stop_mult": [2.0, 2.5], "rvol_min": [1.5]}},
    "regime_decomp": {"ma_short": 20, "ma_long": 50},
}


def _series(n):
    # up 300, down 200, up 300 -> exercises bull / bear / chop classification
    seg1 = np.linspace(100, 300, 300)
    seg2 = np.linspace(300, 150, 200)
    seg3 = np.linspace(150, 400, n - 500)
    base = np.concatenate([seg1, seg2, seg3])
    wobble = 1 + 0.03 * np.sin(np.arange(n) / 9.0)
    return base * wobble


def _ohlcv(close, vol_scale, idx):
    close = pd.Series(close, index=idx)
    openp = close.shift(1).fillna(close.iloc[0])
    high = pd.concat([openp, close], axis=1).max(axis=1) * 1.0005
    low = pd.concat([openp, close], axis=1).min(axis=1) * 0.9995
    # periodic volume spikes -> some bars clear RVOL>=1.5 on new highs (real entries)
    chg = close.pct_change().fillna(0.0)
    spike = np.where(np.arange(len(close)) % 15 == 0, 3.0, 1.0)
    vol = vol_scale * 1e6 * spike * (1.0 + 2.0 * chg.clip(lower=0))
    return pd.DataFrame({"open": openp, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def _synthetic():
    n = 800
    idx = pd.date_range("2021-01-01", periods=n, freq="D", tz="UTC")
    btc = _series(n)
    panel = {"KRAKEN_SPOT_BTC_USD": _ohlcv(btc, 10, idx)}
    metas = {"KRAKEN_SPOT_BTC_USD": SymbolMeta("KRAKEN_SPOT_BTC_USD", "BTC", "USD", "KRAKEN", date(2021, 1, 1), None, True)}
    for i, name in enumerate(["AAA", "BBB", "CCC", "DDD"]):
        sid = f"KRAKEN_SPOT_{name}_USD"
        series = btc * (0.8 + 0.1 * i) + 5 * i + 10 * np.sin(np.arange(n) / (7 + i))
        panel[sid] = _ohlcv(series, 5, idx)
        metas[sid] = SymbolMeta(sid, name, "USD", "KRAKEN", date(2021, 1, 1), None, True)
    return panel, metas


def test_full_pipeline_runs_and_renders(monkeypatch):
    monkeypatch.setattr("cts.pipeline.universe_config", lambda: U)
    monkeypatch.setattr("cts.pipeline.backtest_config", lambda: B)
    panel, metas = _synthetic()
    manifest = {"source": "synthetic", "survivorship_clean": True, "exchange": "KRAKEN"}

    analysis = run_analysis(panel, metas, manifest)

    assert set(analysis["systems"]) == {"S1", "S2"}
    for s in analysis["systems"].values():
        h = s["headline"]
        for key in ("profit_factor", "max_drawdown", "sharpe", "trade_count", "total_return"):
            assert key in h
        assert set(s["regime"]) == {"bull", "bear", "chop"}
        assert "total_return" in s["benchmark"]
        assert s["robustness_neighbourhood"]["n"] == 4  # 2 x 2 x 1 grid

    # the entry path actually fires through the full pipeline (not just wiring)
    total_trades = sum(s["headline"]["trade_count"] for s in analysis["systems"].values())
    assert total_trades > 0

    md = render_findings(analysis)
    assert "VERDICT" in md
    assert "System S1" in md and "System S2" in md
    assert "Regime decomposition" in md
    # survivorship_clean True -> no provisional banner
    assert "PROVISIONAL" not in md
