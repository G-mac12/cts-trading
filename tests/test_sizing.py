from __future__ import annotations

import pytest

from cts.strategy.sizing import position_units, stop_price


def test_stop_price():
    # 2*ATR below entry: 100 - 2*5 = 90
    assert stop_price(100.0, 5.0, 2.0) == pytest.approx(90.0)


def test_position_units_risks_one_percent():
    # equity 2000, risk 1% = 20; stop distance 2*5 = 10; units = 20/10 = 2
    units = position_units(2000.0, 1.0, 5.0, 2.0)
    assert units == pytest.approx(2.0)
    # sanity: holding 2 units, a 10/unit drop to the stop loses exactly 20 (=1%)
    assert units * (2.0 * 5.0) == pytest.approx(20.0)


def test_position_units_zero_atr_is_zero():
    assert position_units(2000.0, 1.0, 0.0, 2.0) == 0.0
    assert position_units(2000.0, 1.0, -1.0, 2.0) == 0.0
