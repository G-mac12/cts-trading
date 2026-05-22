"""Portfolio accounting + constraints (§10): <=5 concurrent positions,
<=50% deployed, idle capital in cash (zero return). One position per symbol."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class Position:
    symbol: str
    system: str
    entry_date: pd.Timestamp
    entry_price: float       # fill price incl. slippage
    units: float
    stop: float
    entry_fee: float


@dataclass
class Trade:
    symbol: str
    system: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    units: float
    entry_fee: float
    exit_fee: float
    gross_pnl: float
    net_pnl: float
    return_pct: float
    exit_reason: str
    bars_held: int


class Portfolio:
    def __init__(self, cash: float):
        self.cash = float(cash)
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []

    def deployed_value(self, prices: Dict[str, float]) -> float:
        return sum(p.units * prices.get(s, p.entry_price) for s, p in self.positions.items())

    def equity(self, prices: Dict[str, float]) -> float:
        return self.cash + self.deployed_value(prices)

    def open(self, pos: Position) -> None:
        cost = pos.units * pos.entry_price
        self.cash -= cost + pos.entry_fee
        self.positions[pos.symbol] = pos

    def close(self, symbol: str, exit_date: pd.Timestamp, exit_price: float,
              exit_fee: float, reason: str) -> Trade:
        pos = self.positions.pop(symbol)
        proceeds = pos.units * exit_price
        self.cash += proceeds - exit_fee
        gross = (exit_price - pos.entry_price) * pos.units
        net = gross - pos.entry_fee - exit_fee
        cost_basis = pos.entry_price * pos.units
        trade = Trade(
            symbol=symbol, system=pos.system, entry_date=pos.entry_date, exit_date=exit_date,
            entry_price=pos.entry_price, exit_price=exit_price, units=pos.units,
            entry_fee=pos.entry_fee, exit_fee=exit_fee, gross_pnl=gross, net_pnl=net,
            return_pct=(net / cost_basis) if cost_basis else 0.0, exit_reason=reason,
            bars_held=int((exit_date - pos.entry_date).days),
        )
        self.trades.append(trade)
        return trade
