"""End-to-end engine test on a fully hand-traced scenario.

X bases flat at ~100, breaks out on D5, we enter at D6's open, then D7 gaps down
through the 2*ATR stop. Every number below is computed by hand so the entry timing,
ATR sizing, stop fill, slippage and fees are all validated together.
"""
from __future__ import annotations

import pandas as pd
import pytest

from cts.data.universe import UniverseSchedule
from cts.engine.backtest import StrategyParams, run_backtest
from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel


def _scenario():
    idx = pd.date_range("2020-01-01", periods=10, freq="D", tz="UTC")
    rows = [
        # open, high, low, close, volume
        (100, 101, 99, 100, 100),
        (100, 101, 99, 100, 100),
        (100, 101, 99, 100, 100),
        (100, 101, 99, 100, 100),
        (100, 101, 99, 100, 100),
        (100, 110, 100, 109, 100),  # D5 breakout (prior-3-high=101, close 109)
        (108, 109, 107, 108, 100),  # D6 entry at open 108
        (100, 101, 95, 97, 100),    # D7 low 95 <= stop 96.162 -> stop
        (97, 98, 96, 97, 100),
        (97, 98, 96, 97, 100),
    ]
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=idx, dtype="float64")
    panel = {"X": df}
    btc = pd.Series([100 + i for i in range(10)], index=idx, dtype="float64")  # rising -> risk-on
    sched = UniverseSchedule(
        rebalance_dates=[idx[0]],
        eligible_by_date={idx[0]: ["X"]},
        top_tier_by_date={idx[0]: ["X"]},
        log=pd.DataFrame(columns=["rebalance_date", "symbol", "status", "reason"]),
    )
    params = StrategyParams(
        n_entry=3, n_exit=2, atr_period=2, atr_stop_mult=2.0,
        rvol_period=2, rvol_min=1.0, risk_per_position_pct=1.0,
        regime_ma_short=2, regime_ma_long=3,
    )
    return panel, btc, sched, params, idx


def test_single_stop_trade_is_hand_correct():
    panel, btc, sched, params, idx = _scenario()
    res = run_backtest(
        panel, btc, sched, params,
        FeeModel(taker_pct=0.40, maker_pct=0.25, exit_uses_maker=False),
        SlippageModel(per_side_pct=0.15),
        start_equity_usd=2000.0, start=idx[0], end=idx[-1],
        max_positions=5, max_deployed_pct=50.0, system_name="S1",
    )
    assert len(res.trades) == 1
    tr = res.trades[0]
    assert tr.exit_reason == "stop"
    assert tr.entry_date == idx[6]
    assert tr.exit_date == idx[7]
    # entry = 108 * 1.0015 ; ATR@D5 = 6 ; stop = entry - 12 = 96.162
    assert tr.entry_price == pytest.approx(108.162, abs=1e-3)
    assert tr.exit_price == pytest.approx(96.162 * 0.9985, abs=1e-3)
    assert tr.units == pytest.approx(20.0 / 12.0, rel=1e-4)   # risk 20 / stop dist 12
    assert tr.net_pnl == pytest.approx(-21.60, abs=0.15)      # ~ -1% + round-trip fees
    # capital is fully in cash (flat) until the entry executes
    assert res.equity_curve.loc[idx[5]] == pytest.approx(2000.0, abs=1e-6)
    assert res.equity_curve.iloc[-1] == pytest.approx(2000.0 + tr.net_pnl, abs=0.2)
