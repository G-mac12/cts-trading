"""Kraken Pro fee model (§3.5).

Entries cross the band to take liquidity -> TAKER fee (0.40% start tier).
Exits: a stop is a market exit -> TAKER. A Donchian exit MAY rest as a limit and
earn MAKER (0.25%) only when ``exit_uses_maker`` is explicitly enabled. The default
is conservative (exits also taker) so a maker assumption never flatters results.
Round trip at taker ~= 0.80% before slippage.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeeModel:
    taker_pct: float = 0.40
    maker_pct: float = 0.25
    exit_uses_maker: bool = False

    def entry_fee(self, notional: float) -> float:
        """Entry always pays taker (breakout crosses the band)."""
        return abs(notional) * (self.taker_pct / 100.0)

    def exit_fee(self, notional: float, is_stop: bool) -> float:
        """Stops pay taker (market). Donchian exits pay maker only if enabled."""
        if is_stop or not self.exit_uses_maker:
            pct = self.taker_pct
        else:
            pct = self.maker_pct
        return abs(notional) * (pct / 100.0)
