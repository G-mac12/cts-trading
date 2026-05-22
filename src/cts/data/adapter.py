"""Pluggable data-adapter interface. The survivorship contract is part of the type:
an adapter that cannot enumerate delisted symbols must set
``survivorship_clean = False`` so the run is tagged PROVISIONAL in FINDINGS.md.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


class SurvivorshipNotGuaranteed(RuntimeError):
    """Raised/flagged when a source cannot guarantee delisted-symbol coverage."""


@dataclass(frozen=True)
class SymbolMeta:
    symbol_id: str          # vendor-native id, e.g. "KRAKEN_SPOT_BTC_USD"
    base: str               # e.g. "BTC"
    quote: str              # e.g. "USD"
    exchange: str           # "KRAKEN"
    data_start: date
    data_end: Optional[date]  # None = still active; a date = delisted then
    is_active: bool
    recent_volume_usd: float = 0.0  # vendor's current 1-day USD volume (ingest scoping only)


class DataAdapter(ABC):
    """Source of survivorship-clean daily OHLCV for a single exchange.

    survivorship_clean: True only if list_symbols() includes delisted symbols
    with honest data_end dates.
    """

    survivorship_clean: bool = False
    source_name: str = "abstract"

    @abstractmethod
    def list_symbols(self) -> List[SymbolMeta]:
        """All spot symbols ever tradable on the exchange, incl. delisted ones."""

    @abstractmethod
    def daily_ohlcv(self, symbol_id: str, start: date, end: date) -> pd.DataFrame:
        """UTC, 00:00-anchored daily OHLCV+volume for [start, end].

        Returns a DataFrame indexed by tz-aware UTC DatetimeIndex with columns
        exactly OHLCV_COLUMNS. ``volume`` is base-asset units traded.
        """
