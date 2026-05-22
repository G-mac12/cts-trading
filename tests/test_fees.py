from __future__ import annotations

import pytest

from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel


def test_entry_always_taker():
    fm = FeeModel(taker_pct=0.40, maker_pct=0.25, exit_uses_maker=False)
    assert fm.entry_fee(1000.0) == pytest.approx(4.0)  # 0.40%


def test_exit_taker_by_default():
    fm = FeeModel(exit_uses_maker=False)
    assert fm.exit_fee(1000.0, is_stop=True) == pytest.approx(4.0)
    assert fm.exit_fee(1000.0, is_stop=False) == pytest.approx(4.0)


def test_exit_maker_only_for_resting_donchian_when_enabled():
    fm = FeeModel(exit_uses_maker=True)
    # Donchian (non-stop) resting exit earns maker
    assert fm.exit_fee(1000.0, is_stop=False) == pytest.approx(2.5)  # 0.25%
    # a stop is a market exit -> still taker even when maker is enabled
    assert fm.exit_fee(1000.0, is_stop=True) == pytest.approx(4.0)


def test_round_trip_taker_is_about_80bps():
    fm = FeeModel()
    rt = fm.entry_fee(1000.0) + fm.exit_fee(1000.0, is_stop=True)
    assert rt == pytest.approx(8.0)  # 0.80% of 1000


def test_slippage_penalises_both_sides():
    sm = SlippageModel(per_side_pct=0.15)
    assert sm.buy_price(100.0) == pytest.approx(100.15)
    assert sm.sell_price(100.0) == pytest.approx(99.85)
