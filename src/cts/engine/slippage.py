"""Slippage model — explicit, conservative, configurable (§9).

Assumption: each fill executes ``per_side_pct`` worse than the reference price
(buys fill higher, sells fill lower). A flat per-side percentage is deliberately
simple and pessimistic for large-cap, liquid names; it is reported as a stated
assumption and stress-tested across a sensitivity band (0.05 / 0.15 / 0.30%).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlippageModel:
    per_side_pct: float = 0.15

    def buy_price(self, ref_price: float) -> float:
        return ref_price * (1.0 + self.per_side_pct / 100.0)

    def sell_price(self, ref_price: float) -> float:
        return ref_price * (1.0 - self.per_side_pct / 100.0)
