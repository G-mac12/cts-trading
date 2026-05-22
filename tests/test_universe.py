from __future__ import annotations

from datetime import date

import pandas as pd

from cts.data.adapter import SymbolMeta
from cts.data.universe import build_schedule

CFG_U = {
    "min_24h_usd_volume": 0,
    "liquidity_window_days": 2,
    "min_history_days": 5,
    "universe_size_cap": 50,
    "quote_currencies": ["USD", "USDT"],
    "exclude_stablecoins": True,
    "exclude_wrapped": True,
    "exclude_leveraged": True,
    "stablecoin_bases": ["USDT"],
    "wrapped_bases": ["WETH"],
    "leveraged_substrings": ["UP", "DOWN"],
}
CFG_S = {"xs_momentum_lookback": 3, "xs_rebalance_days": 7, "xs_top_tier_frac": 1.0}


def _df(closes):
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="D", tz="UTC")
    return pd.DataFrame(
        {"open": closes, "high": [c + 1 for c in closes], "low": [c - 1 for c in closes],
         "close": closes, "volume": [1000] * len(closes)},
        index=idx,
    )


def _meta(sym, base):
    return SymbolMeta(sym, base, "USD", "KRAKEN", date(2020, 1, 1), None, True)


def _panel():
    closes = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    panel = {s: _df(closes) for s in ("GOOD", "USDT_STBL", "WETH", "BTCUP")}
    metas = {
        "GOOD": _meta("GOOD", "GOOD"),
        "USDT_STBL": _meta("USDT_STBL", "USDT"),
        "WETH": _meta("WETH", "WETH"),
        "BTCUP": _meta("BTCUP", "BTCUP"),
    }
    return panel, metas


def test_exclusions_logged_with_reasons():
    panel, metas = _panel()
    rb = panel["GOOD"].index[6]
    sched = build_schedule(panel, metas, CFG_U, CFG_S, [rb])
    assert "GOOD" in sched.eligible_by_date[rb]
    assert "GOOD" in sched.top_tier_by_date[rb]
    reasons = dict(zip(sched.log["symbol"], sched.log["reason"]))
    assert reasons["USDT_STBL"] == "stablecoin"
    assert reasons["WETH"] == "wrapped"
    assert reasons["BTCUP"] == "leveraged"


def test_no_lookahead_future_data_does_not_change_decision():
    panel, metas = _panel()
    rb = panel["GOOD"].index[6]
    before = build_schedule(panel, metas, CFG_U, CFG_S, [rb]).log

    # Mutate GOOD prices AFTER the rebalance date to absurd values.
    panel["GOOD"].loc[panel["GOOD"].index[7]:, "close"] = 9999
    after = build_schedule(panel, metas, CFG_U, CFG_S, [rb]).log

    pd.testing.assert_frame_equal(
        before.sort_values("symbol").reset_index(drop=True),
        after.sort_values("symbol").reset_index(drop=True),
    )
