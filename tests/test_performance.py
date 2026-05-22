from __future__ import annotations

import pandas as pd
import pytest

from cts.engine.portfolio import Trade
from cts.metrics.performance import (
    max_drawdown,
    payoff_ratio,
    profit_factor,
    sharpe,
    total_return,
    win_rate,
)


def _mk(net: float) -> Trade:
    d = pd.Timestamp("2024-01-01", tz="UTC")
    return Trade("X", "S1", d, d, 100.0, 100.0, 1.0, 0.0, 0.0, net, net, net / 100.0, "stop", 0)


def test_total_return_and_drawdown():
    eq = pd.Series([100, 120, 90, 150], index=pd.date_range("2024-01-01", periods=4, tz="UTC"))
    assert total_return(eq) == pytest.approx(0.5)
    # running max [100,120,120,150]; trough 90/120-1 = -0.25
    assert max_drawdown(eq) == pytest.approx(-0.25)


def test_profit_factor_winrate_payoff():
    trades = [_mk(10), _mk(-5), _mk(20), _mk(-5)]
    assert profit_factor(trades) == pytest.approx(30 / 10)   # 3.0
    assert win_rate(trades) == pytest.approx(0.5)
    assert payoff_ratio(trades) == pytest.approx(15 / 5)     # avg win 15 / avg loss 5


def test_profit_factor_no_losses_is_inf():
    assert profit_factor([_mk(10), _mk(5)]) == float("inf")


def test_sharpe_zero_when_flat_positive_when_drifting():
    flat = pd.Series([0.0, 0.0, 0.0])
    assert sharpe(flat) == 0.0
    drift = pd.Series([0.01, 0.02, 0.015, 0.012, 0.018])
    assert sharpe(drift) > 0
