"""Integration test for the lean paper-trader on synthetic data (no disk cache,
no network). Validates variant construction, forward-window run, persistence, and
the status render."""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from cts.data.adapter import SymbolMeta

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
    "robustness": {"subsample_frac": 0.667, "subsample_seeds": [1],
                   "param_neighbourhood": {"donchian_entry": [10], "atr_stop_mult": [2.0], "rvol_min": [1.5]}},
    "regime_decomp": {"ma_short": 20, "ma_long": 50},
}


def _ohlcv(close, vol_scale, idx):
    close = pd.Series(close, index=idx)
    openp = close.shift(1).fillna(close.iloc[0])
    high = pd.concat([openp, close], axis=1).max(axis=1) * 1.0005
    low = pd.concat([openp, close], axis=1).min(axis=1) * 0.9995
    chg = close.pct_change().fillna(0.0)
    spike = np.where(np.arange(len(close)) % 15 == 0, 3.0, 1.0)
    vol = vol_scale * 1e6 * spike * (1.0 + 2.0 * chg.clip(lower=0))
    return pd.DataFrame({"open": openp, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def _synthetic():
    n = 700
    idx = pd.date_range("2021-01-01", periods=n, freq="D", tz="UTC")
    btc = np.concatenate([np.linspace(100, 300, 300), np.linspace(300, 160, 200), np.linspace(160, 380, n - 500)])
    btc = btc * (1 + 0.03 * np.sin(np.arange(n) / 9.0))
    panel = {"KRAKEN_SPOT_BTC_USD": _ohlcv(btc, 10, idx)}
    metas = {"KRAKEN_SPOT_BTC_USD": SymbolMeta("KRAKEN_SPOT_BTC_USD", "BTC", "USD", "KRAKEN", date(2021, 1, 1), None, True)}
    for i, nm in enumerate(["AAA", "BBB", "CCC"]):
        sid = f"KRAKEN_SPOT_{nm}_USD"
        s = btc * (0.8 + 0.1 * i) + 6 * i + 10 * np.sin(np.arange(n) / (7 + i))
        panel[sid] = _ohlcv(s, 5, idx)
        metas[sid] = SymbolMeta(sid, nm, "USD", "KRAKEN", date(2021, 1, 1), None, True)
    return panel, metas


def test_run_paper_forward_and_persist(monkeypatch, tmp_path):
    panel, metas = _synthetic()
    manifest = {"source": "synthetic", "survivorship_clean": True, "exchange": "KRAKEN"}
    monkeypatch.setattr("cts.paper.runner.universe_config", lambda: U)
    monkeypatch.setattr("cts.paper.runner.backtest_config", lambda: B)
    monkeypatch.setattr("cts.paper.runner.load_cached", lambda cache, source: (panel, metas, manifest))
    monkeypatch.setattr("cts.paper.runner.PAPER_DIR", tmp_path)
    # pre-seed an earlier paper-start so the forward window has real trades
    (tmp_path / "paper_state.json").write_text(json.dumps(
        {"paper_start": "2021-06-01", "inception_equity_usd": 2540.0, "first_run_at": "x"}))

    from cts.paper.runner import run_paper
    rep = run_paper(as_of="2023-01-01")

    assert {"S1-baseline", "S1-chopfix", "S2-baseline", "S2-chopfix"} <= set(rep["variants"])
    assert rep["variants"]["S1-chopfix"]["regime_exit"] is True
    assert rep["variants"]["S1-baseline"]["regime_exit"] is False
    # forward window had trades, and persistence happened
    assert sum(v["n_forward_trades"] for v in rep["variants"].values()) > 0
    assert (tmp_path / "paper_snapshot.json").exists()
    assert (tmp_path / "paper_runs.csv").exists()

    from cts.paper.report import render_paper
    md = render_paper(rep)
    assert "Paper Trading" in md and "SIMULATED ONLY" in md
