"""S3 net-cost model. Spot only (no funding). Per traded notional:
    cost = taker_fee + slippage(order$, ADV$)
slippage = (base_half_spread + impact_coef * %-of-ADV) basis points, × a sensitivity
multiplier. ADV (daily $ volume) is the depth proxy (we have no historical order book).
The S3-D sensitivity run re-runs everything at mult=2.0 to check the edge survives.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    taker_pct: float = 0.40
    slippage_base_bps: float = 5.0
    slippage_impact_coef: float = 10.0
    slippage_mult: float = 1.0

    def slippage_frac(self, order_usd: float, adv_usd: float) -> float:
        if adv_usd <= 0:
            return self.slippage_base_bps * self.slippage_mult / 1e4
        pct_of_adv = (order_usd / adv_usd) * 100.0
        bps = (self.slippage_base_bps + self.slippage_impact_coef * pct_of_adv) * self.slippage_mult
        return bps / 1e4

    def trade_cost(self, order_usd: float, adv_usd: float) -> float:
        """Total cost ($) to trade `order_usd` notional in a name with ADV `adv_usd`."""
        order_usd = abs(order_usd)
        return order_usd * (self.taker_pct / 100.0 + self.slippage_frac(order_usd, adv_usd))
