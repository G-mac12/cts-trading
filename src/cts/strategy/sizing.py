"""ATR/Turtle position sizing (§3.1).

Units = (Equity * Risk%) / (ATR-based stop distance), where stop distance =
atr_stop_mult * ATR. Risk per position is 1% of equity by default. The stop is
volatility-scaled (2*ATR below entry), never a fixed cash amount.
"""
from __future__ import annotations


def stop_price(entry_price: float, atr_value: float, atr_stop_mult: float = 2.0) -> float:
    """Initial hard stop: ``atr_stop_mult`` * ATR below entry (long-only)."""
    return entry_price - atr_stop_mult * atr_value


def position_units(
    equity: float,
    risk_per_position_pct: float,
    atr_value: float,
    atr_stop_mult: float = 2.0,
) -> float:
    """Number of units so that hitting the stop loses ~risk_per_position_pct of equity.

    Returns 0.0 if ATR is non-positive (cannot size a risk-defined position).
    Note: fees/slippage make the realised stop loss slightly larger than the
    nominal 1%; that drag shows up in the backtest P&L, not in this sizing rule.
    """
    if atr_value <= 0 or equity <= 0:
        return 0.0
    risk_amount = equity * (risk_per_position_pct / 100.0)
    stop_distance = atr_stop_mult * atr_value
    return risk_amount / stop_distance
