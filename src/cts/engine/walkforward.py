"""Walk-forward orchestration (§9) — the anti-overfitting core.

Two modes:
  * FIXED (headline): the spec's starting parameters, never fitted to the data, run
    over the full history. Because the parameters were chosen a priori, the whole
    result is already out-of-sample w.r.t. parameter selection. We additionally
    slice it per OOS fold to show stability across time.
  * TUNED: for each fold, evaluate candidates on the IN-SAMPLE window only, freeze
    the best, then apply it to the IMMEDIATELY FOLLOWING out-of-sample window.
    Equity compounds across OOS folds; positions reset at fold boundaries. The
    per-fold chosen parameters are returned so instability (a red flag) is visible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import pandas as pd
from dateutil.relativedelta import relativedelta

from cts.engine.backtest import BacktestResult, StrategyParams, run_backtest
from cts.engine.fees import FeeModel
from cts.engine.portfolio import Trade
from cts.engine.slippage import SlippageModel


@dataclass(frozen=True)
class Fold:
    index: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp


def generate_folds(
    data_start: pd.Timestamp,
    data_end: pd.Timestamp,
    is_months: int,
    oos_months: int,
    step_months: int,
) -> List[Fold]:
    folds: List[Fold] = []
    is_start = pd.Timestamp(data_start)
    data_end = pd.Timestamp(data_end)
    i = 0
    while True:
        is_end = is_start + relativedelta(months=is_months)
        oos_start = is_end
        if oos_start >= data_end:
            break
        oos_end = min(oos_start + relativedelta(months=oos_months), data_end)
        folds.append(Fold(i, is_start, is_end, oos_start, oos_end))
        i += 1
        is_start = is_start + relativedelta(months=step_months)
        if oos_end >= data_end:
            break
    return folds


def run_fixed(
    panel, btc_close, schedule, params: StrategyParams, *,
    fee_model: FeeModel, slippage: SlippageModel, start_equity_usd: float,
    start: pd.Timestamp, end: pd.Timestamp, max_positions: int, max_deployed_pct: float,
    system_name: str,
) -> BacktestResult:
    return run_backtest(
        panel, btc_close, schedule, params, fee_model, slippage, start_equity_usd,
        start, end, max_positions, max_deployed_pct, system_name,
    )


def run_tuned(
    panel, btc_close, schedule, candidates: List[StrategyParams], folds: List[Fold], *,
    objective: Callable[[BacktestResult], float],
    fee_model: FeeModel, slippage: SlippageModel, start_equity_usd: float,
    max_positions: int, max_deployed_pct: float, system_name: str,
) -> Dict:
    equity_pieces: List[pd.Series] = []
    all_trades: List[Trade] = []
    chosen: List[Tuple[Fold, StrategyParams, float]] = []
    equity = float(start_equity_usd)

    for fold in folds:
        best_params, best_score = candidates[0], float("-inf")
        for cand in candidates:
            r_is = run_backtest(
                panel, btc_close, schedule, cand, fee_model, slippage, start_equity_usd,
                fold.is_start, fold.is_end, max_positions, max_deployed_pct, system_name,
            )
            score = objective(r_is)
            if score > best_score:
                best_score, best_params = score, cand

        r_oos = run_backtest(
            panel, btc_close, schedule, best_params, fee_model, slippage, equity,
            fold.oos_start, fold.oos_end, max_positions, max_deployed_pct, system_name,
        )
        if len(r_oos.equity_curve):
            equity = float(r_oos.equity_curve.iloc[-1])
            equity_pieces.append(r_oos.equity_curve)
        all_trades.extend(r_oos.trades)
        chosen.append((fold, best_params, best_score))

    stitched = pd.Series(dtype="float64")
    if equity_pieces:
        stitched = pd.concat(equity_pieces).sort_index()
        stitched = stitched[~stitched.index.duplicated(keep="last")]
    return {"equity": stitched, "trades": all_trades, "chosen": chosen}
