"""Event-driven daily backtest loop (§9).

Execution model (stated plainly; conservative on purpose):
  * Signals are computed on the daily CLOSE of day t.
  * Breakout ENTRIES and Donchian EXITS execute at the NEXT day's OPEN (+slippage,
    +fee). No same-bar lookahead. If the next bar is missing (gap/delist), the
    order is carried forward to the next available bar.
  * STOPS are intrabar: if a day's LOW <= stop, the position exits that same day.
    Fill = the stop level, or the day's OPEN if it gapped through the stop (worse).
    On any day a stop and a queued Donchian exit both apply, the STOP wins (worst-
    case tie-break).
  * Position size uses the ATR known at SIGNAL time (close of t). Stop = entry fill
    - atr_stop_mult * ATR_signal. Notional is capped so total deployed never exceeds
    max_deployed_pct and never exceeds available cash (incl. fee).
  * Open positions at the end of the window are force-closed at the last close
    (reason 'end-of-test') so trade statistics are complete.

One system (n_entry/n_exit) per run; System 1 and System 2 are run separately.
Deterministic: no randomness anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from cts.engine.fees import FeeModel
from cts.engine.portfolio import Portfolio, Position, Trade
from cts.engine.slippage import SlippageModel
from cts.indicators import atr as atr_ind
from cts.strategy.exits import donchian_exit_signal
from cts.strategy.regime import regime_on
from cts.strategy.signals import breakout_signal
from cts.strategy.sizing import position_units

_MIN_NOTIONAL = 1.0  # USD; below this an entry is not worth opening


@dataclass(frozen=True)
class StrategyParams:
    n_entry: int
    n_exit: int
    atr_period: int = 14
    atr_stop_mult: float = 2.0
    rvol_period: int = 20
    rvol_min: float = 1.5
    risk_per_position_pct: float = 1.0
    regime_ma_short: int = 50
    regime_ma_long: int = 100


@dataclass
class BacktestResult:
    system: str
    equity_curve: pd.Series
    trades: List[Trade]
    start: pd.Timestamp
    end: pd.Timestamp
    params: StrategyParams
    meta: Dict = field(default_factory=dict)

    @property
    def daily_returns(self) -> pd.Series:
        return self.equity_curve.pct_change().dropna()


def _build_features(panel: Dict[str, pd.DataFrame], dates: pd.DatetimeIndex, p: StrategyParams) -> Dict[str, pd.DataFrame]:
    feat: Dict[str, pd.DataFrame] = {}
    for sym, df in panel.items():
        entry_sig = breakout_signal(df, p.n_entry, p.rvol_period, p.rvol_min)
        exit_sig = donchian_exit_signal(df, p.n_exit)
        atr_s = atr_ind(df["high"], df["low"], df["close"], p.atr_period)
        f = pd.DataFrame(
            {"open": df["open"], "high": df["high"], "low": df["low"], "close": df["close"], "atr": atr_s}
        ).reindex(dates)
        # reindex bool signals with fill_value=False (avoids NaN->object downcast warning)
        f["entry_sig"] = entry_sig.reindex(dates, fill_value=False).astype(bool)
        f["exit_sig"] = exit_sig.reindex(dates, fill_value=False).astype(bool)
        feat[sym] = f
    return feat


def _top_tier_walker(schedule, dates: pd.DatetimeIndex) -> Dict[pd.Timestamp, List[str]]:
    """Map each trading date to the top-tier set from the most recent rebalance <= t."""
    rbs = sorted(schedule.rebalance_dates)
    out: Dict[pd.Timestamp, List[str]] = {}
    current: List[str] = []
    j = 0
    for t in dates:
        while j < len(rbs) and rbs[j] <= t:
            current = schedule.top_tier_by_date.get(rbs[j], [])
            j += 1
        out[t] = current
    return out


def run_backtest(
    panel: Dict[str, pd.DataFrame],
    btc_close: pd.Series,
    schedule,
    params: StrategyParams,
    fee_model: FeeModel,
    slippage: SlippageModel,
    start_equity_usd: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    max_positions: int = 5,
    max_deployed_pct: float = 50.0,
    system_name: str = "S1",
) -> BacktestResult:
    start = pd.Timestamp(start);  end = pd.Timestamp(end)
    # union trading calendar within [start, end]
    all_dates = pd.DatetimeIndex(sorted(set().union(*[df.index for df in panel.values()]))) if panel else pd.DatetimeIndex([])
    dates = all_dates[(all_dates >= start) & (all_dates <= end)]
    if len(dates) == 0:
        empty = pd.Series(dtype="float64")
        return BacktestResult(system_name, empty, [], start, end, params)

    feat = _build_features(panel, dates, params)
    close_wide = pd.DataFrame({s: df["close"] for s, df in panel.items()}).reindex(dates).ffill()
    regime = regime_on(btc_close, params.regime_ma_short, params.regime_ma_long).reindex(dates).fillna(False)
    top_for_t = _top_tier_walker(schedule, dates)

    pf = Portfolio(start_equity_usd)
    pending_entries: List[dict] = []
    pending_exits: set = set()
    fee_factor = 1.0 + fee_model.taker_pct / 100.0
    equity_curve: Dict[pd.Timestamp, float] = {}

    for t in dates:
        mtm = close_wide.loc[t].to_dict()

        # 1) STOPS — intrabar, highest priority
        for sym in list(pf.positions):
            f = feat[sym]
            if t not in f.index:
                continue
            low_t, open_t = f.at[t, "low"], f.at[t, "open"]
            if pd.isna(low_t):
                continue
            pos = pf.positions[sym]
            if low_t <= pos.stop:
                ref = open_t if (not pd.isna(open_t) and open_t < pos.stop) else pos.stop
                exit_price = slippage.sell_price(ref)
                fee = fee_model.exit_fee(pos.units * exit_price, is_stop=True)
                pf.close(sym, t, exit_price, fee, "stop")
                pending_exits.discard(sym)

        # 2) queued Donchian exits at this open
        for sym in list(pending_exits):
            if sym not in pf.positions:
                pending_exits.discard(sym); continue
            open_t = feat[sym].at[t, "open"] if t in feat[sym].index else np.nan
            if pd.isna(open_t):
                continue  # carry forward
            pos = pf.positions[sym]
            exit_price = slippage.sell_price(open_t)
            fee = fee_model.exit_fee(pos.units * exit_price, is_stop=False)
            pf.close(sym, t, exit_price, fee, "donchian")
            pending_exits.discard(sym)

        # 3) queued entries at this open
        still: List[dict] = []
        for order in pending_entries:
            sym = order["symbol"]
            if sym in pf.positions:
                continue
            open_t = feat[sym].at[t, "open"] if t in feat[sym].index else np.nan
            if pd.isna(open_t):
                still.append(order); continue  # carry forward until it trades
            if len(pf.positions) >= max_positions:
                continue  # capacity gone before this order filled -> drop
            equity = pf.equity(mtm)
            deployed = pf.deployed_value(mtm)
            remaining = max(0.0, max_deployed_pct / 100.0 * equity - deployed)
            atr_sig = order["atr"]
            entry_price = slippage.buy_price(open_t)
            risk_notional = position_units(equity, params.risk_per_position_pct, atr_sig, params.atr_stop_mult) * entry_price
            notional = min(risk_notional, remaining, pf.cash / fee_factor)
            if notional <= _MIN_NOTIONAL:
                continue
            units = notional / entry_price
            stop = entry_price - params.atr_stop_mult * atr_sig
            pf.open(Position(sym, system_name, t, entry_price, units, stop, fee_model.entry_fee(notional)))
        pending_entries = still

        # 4) end-of-day signals at close[t]
        for sym, pos in pf.positions.items():
            f = feat[sym]
            if t in f.index and bool(f.at[t, "exit_sig"]):
                pending_exits.add(sym)
        if bool(regime.loc[t]):
            for sym in top_for_t.get(t, []):
                if sym in pf.positions or sym not in feat:
                    continue
                f = feat[sym]
                if t not in f.index:
                    continue
                a = f.at[t, "atr"]
                if bool(f.at[t, "entry_sig"]) and not pd.isna(a) and a > 0:
                    pending_entries.append({"symbol": sym, "system": system_name, "atr": float(a)})

        equity_curve[t] = pf.equity(mtm)

    # force-close survivors at the last close for complete trade stats
    last_t = dates[-1]
    last_prices = close_wide.loc[last_t].to_dict()
    for sym in list(pf.positions):
        pos = pf.positions[sym]
        px = last_prices.get(sym, pos.entry_price)
        exit_price = slippage.sell_price(px)
        fee = fee_model.exit_fee(pos.units * exit_price, is_stop=False)
        pf.close(sym, last_t, exit_price, fee, "end-of-test")
    equity_curve[last_t] = pf.equity(last_prices)

    return BacktestResult(
        system=system_name,
        equity_curve=pd.Series(equity_curve).sort_index(),
        trades=pf.trades,
        start=start, end=end, params=params,
        meta={"n_dates": len(dates), "survivorship_clean": schedule is not None},
    )
