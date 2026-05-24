"""S3 rotation engine — structural checks on a controlled synthetic scenario:
3 strong L1 names (must be capped at 2/segment), 1 each of majors/DeFi/privacy, BTC
risk-on throughout. Verifies slot cap, segment cap, regime gate, and outputs."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from cts.data.adapter import SymbolMeta
from cts.s3.cost import CostModel
from cts.s3.rotation import S3Params, run_s3
from cts.s3.universe import S3Universe

CFG_U = {"min_adv_usd": 1_000_000, "adv_window_days": 30, "min_listing_age_days": 60}


def _ohlcv(close, idx, vol_scale=5e5):
    close = pd.Series(close, index=idx)
    return pd.DataFrame({"open": close, "high": close * 1.001, "low": close * 0.999,
                         "close": close, "volume": vol_scale}, index=idx)  # close*vol ~ $50M


def _panel():
    n = 400
    idx = pd.date_range("2023-01-01", periods=n, freq="D", tz="UTC")
    t = np.arange(n)
    coins = {
        "KRAKEN_SPOT_BTC_USD": ("BTC", 30000 * (1 + 0.0015 * t)),          # majors, risk-on
        "KRAKEN_SPOT_SOL_USD": ("SOL", 20 * (1 + 0.004 * t)),             # L1 (strong)
        "KRAKEN_SPOT_ADA_USD": ("ADA", 0.3 * (1 + 0.0038 * t)),           # L1 (strong)
        "KRAKEN_SPOT_AVAX_USD": ("AVAX", 15 * (1 + 0.0036 * t)),          # L1 (strong)
        "KRAKEN_SPOT_UNI_USD": ("UNI", 6 * (1 + 0.001 * t)),             # DeFi (mild)
        "KRAKEN_SPOT_XMR_USD": ("XMR", 150 * (1 + 0.0008 * t)),          # privacy (mild)
    }
    panel, metas = {}, {}
    for sid, (base, px) in coins.items():
        panel[sid] = _ohlcv(px, idx)
        metas[sid] = SymbolMeta(sid, base, "USD", "KRAKEN", date(2023, 1, 1), None, True)
    return panel, metas, idx


def test_rotation_respects_caps_and_runs():
    panel, metas, idx = _panel()
    uni = S3Universe(panel, metas, CFG_U)
    btc = panel["KRAKEN_SPOT_BTC_USD"]["close"]
    res = run_s3(panel, btc, uni, S3Params(max_slots=4, segment_cap=2, hysteresis_buffer=3),
                 CostModel(), start_equity_usd=2540.0, start=idx[0], end=idx[-1])

    assert len(res.equity_curve) > 0
    days_with_holdings = [d for d, h in res.held_history.items() if h]
    assert days_with_holdings                                  # it actually traded
    for held in res.held_history.values():
        assert len(held) <= 4                                  # slot cap
        l1 = sum(1 for s in held if uni.segment(s) == "L1")
        assert l1 <= 2                                          # segment cap (3 L1 names, max 2 held)
    assert set(res.vol_profile) >= {"held_median_realized_vol", "avg_majors_share_of_book",
                                    "low_vol_majors_hug", "held_vs_universe_vol_ratio"}
    assert isinstance(res.trades, list)


def test_regime_off_goes_to_cash():
    panel, metas, idx = _panel()
    # BTC steadily FALLING -> regime risk-off -> no holdings
    falling = pd.Series(60000 * (1 - 0.0012 * np.arange(len(idx))), index=idx)
    uni = S3Universe(panel, metas, CFG_U)
    res = run_s3(panel, falling, uni, S3Params(max_slots=4, segment_cap=2),
                 CostModel(), start_equity_usd=2540.0, start=idx[0], end=idx[-1])
    assert all(len(h) == 0 for h in res.held_history.values())  # fully in cash when risk-off
