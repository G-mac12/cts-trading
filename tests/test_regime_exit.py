"""The chop-fix flag (regime_exit): when the master regime flips off, open positions
are exited (next open) instead of being left to a slow Donchian/stop. Hand-built
scenario: X enters in a bull regime, then BTC rolls over (regime off) while X stays
flat (no Donchian exit, no stop). With regime_exit the position is closed on the
flip; without it, the position is still held."""
from __future__ import annotations

import pandas as pd

from cts.data.universe import UniverseSchedule
from cts.engine.backtest import StrategyParams, run_backtest
from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel


def _scenario():
    idx = pd.date_range("2020-01-01", periods=13, freq="D", tz="UTC")
    x = [
        (100, 101, 99, 100, 100), (100, 101, 99, 100, 100), (100, 101, 99, 100, 100),
        (100, 101, 99, 100, 100), (100, 101, 99, 100, 100),
        (100, 110, 100, 109, 300),                       # D5 breakout
        (108, 109, 107, 108, 100),                       # D6 entry at open
        (108, 109, 107, 108, 100), (108, 109, 107, 108, 100), (108, 109, 107, 108, 100),
        (108, 109, 107, 108, 100), (108, 109, 107, 108, 100), (108, 109, 107, 108, 100),
    ]
    df = pd.DataFrame(x, columns=["open", "high", "low", "close", "volume"], index=idx, dtype="float64")
    # BTC rises (regime ON at D5/D6) then rolls over -> regime OFF from D7
    btc = pd.Series([100, 101, 102, 103, 104, 105, 106, 104, 101, 97, 93, 89, 85], index=idx, dtype="float64")
    sched = UniverseSchedule([idx[0]], {idx[0]: ["X"]}, {idx[0]: ["X"]},
                             pd.DataFrame(columns=["rebalance_date", "symbol", "status", "reason"]))
    return {"X": df}, btc, sched, idx


def _params(regime_exit):
    return StrategyParams(n_entry=3, n_exit=3, atr_period=2, atr_stop_mult=2.0, rvol_period=2,
                          rvol_min=1.0, regime_ma_short=2, regime_ma_long=3, regime_exit=regime_exit)


def _run(regime_exit):
    panel, btc, sched, idx = _scenario()
    return run_backtest(panel, btc, sched, _params(regime_exit),
                        FeeModel(), SlippageModel(per_side_pct=0.15), 2000.0, idx[0], idx[-1],
                        close_at_end=False, system_name="S1")


def test_regime_exit_closes_on_flip():
    res = _run(regime_exit=True)
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "regime"
    assert len(res.open_positions) == 0  # de-risked when regime flipped off


def test_without_regime_exit_position_is_still_held():
    res = _run(regime_exit=False)
    assert not any(t.exit_reason == "regime" for t in res.trades)
    assert [p.symbol for p in res.open_positions] == ["X"]  # still holding into the chop
