"""S3 daily cross-sectional rotation engine (separate from S1's breakout engine).

Each day: rank the eligible universe by the risk-adjusted momentum signal, hold a
DYNAMIC top-N (<= eligible-after-caps), max per-segment cap, with a hysteresis buffer
(keep a held name if still within top N+buffer). Regime-off -> cash. Equal-weight to a
deployment cap; net of taker fee + ADV-proxy slippage on turnover. No lookahead:
weights for day t are formed from the signal at the PRIOR close.

Outputs the equity curve + daily returns (rigorous, nets actual turnover cost),
per-name round-trip trades (for PF), held history, turnover, and a vol profile of held
names vs the universe median (to flag low-vol-majors hugging, which would lift S1↔S3
correlation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from cts.s3.cost import CostModel
from cts.s3.ranking import realized_vol, risk_adjusted_momentum
from cts.s3.universe import S3Universe
from cts.strategy.regime import regime_on


@dataclass(frozen=True)
class S3Params:
    lookback_days: int = 90
    skip_days: int = 7
    vol_window_days: int = 90
    max_slots: int = 6
    segment_cap: int = 2          # 0 = no cap
    hysteresis_buffer: int = 3
    total_deployment_pct: float = 100.0
    max_position_pct: float = 34.0
    regime_ma_short: int = 50
    regime_ma_long: int = 100


@dataclass
class S3Result:
    equity_curve: pd.Series
    daily_returns: pd.Series
    trades: List[dict]
    held_history: Dict[pd.Timestamp, List[str]]
    turnover: pd.Series
    vol_profile: Dict
    meta: Dict = field(default_factory=dict)


def _select(ranked: List[str], rank_idx: Dict[str, int], prev_held: List[str],
            seg_of, n_slots: int, cap: int, buffer: int) -> List[str]:
    target: List[str] = []
    seg_count: Dict[str, int] = {}

    def can_add(s: str) -> bool:
        return not cap or seg_count.get(seg_of(s), 0) < cap

    # 1) keep prior holds still near the top (hysteresis), respecting caps
    for s in prev_held:
        if len(target) >= n_slots:
            break
        if s in rank_idx and rank_idx[s] < n_slots + buffer and can_add(s):
            target.append(s)
            seg_count[seg_of(s)] = seg_count.get(seg_of(s), 0) + 1
    # 2) fill remaining slots from the top of the ranking
    for s in ranked:
        if len(target) >= n_slots:
            break
        if s in target or not can_add(s):
            continue
        target.append(s)
        seg_count[seg_of(s)] = seg_count.get(seg_of(s), 0) + 1
    return target


def run_s3(panel: Dict[str, pd.DataFrame], btc_close: pd.Series, universe: S3Universe,
           params: S3Params, cost: CostModel, start_equity_usd: float,
           start: pd.Timestamp, end: pd.Timestamp) -> S3Result:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    all_dates = pd.DatetimeIndex(sorted(set().union(*[df.index for df in panel.values()])))
    dates = all_dates[(all_dates >= start) & (all_dates <= end)]
    if len(dates) < 2:
        empty = pd.Series(dtype="float64")
        return S3Result(empty, empty, [], {}, empty, {})

    close_wide = pd.DataFrame({s: df["close"] for s, df in panel.items()}).reindex(dates).ffill()
    ret_wide = close_wide.pct_change()
    sig_wide = pd.DataFrame(
        {s: risk_adjusted_momentum(df["close"], params.lookback_days, params.skip_days, params.vol_window_days)
         for s, df in panel.items()}).reindex(dates)
    rv_wide = pd.DataFrame({s: realized_vol(df["close"], 30) for s, df in panel.items()}).reindex(dates)
    regime = regime_on(btc_close, params.regime_ma_short, params.regime_ma_long).reindex(dates, fill_value=False).astype(bool)
    elig_frame = universe.eligible_frame(dates)   # precomputed (dates x coins) bool

    deployment = params.total_deployment_pct / 100.0
    max_pos = params.max_position_pct / 100.0
    equity = float(start_equity_usd)
    prev_w: Dict[str, float] = {}
    prev_held: List[str] = []
    open_pos: Dict[str, dict] = {}        # name -> {entry_date, entry_close}
    rt_cost = 2.0 * (cost.taker_pct / 100.0 + cost.slippage_base_bps * cost.slippage_mult / 1e4)

    equity_curve, turnover_s, held_hist = {}, {}, {}
    trades: List[dict] = []
    held_vol_samples, univ_vol_samples, majors_share = [], [], []

    for i, t in enumerate(dates):
        if i == 0:
            equity_curve[t] = equity
            continue
        prev = dates[i - 1]

        # --- form target from PRIOR close (no lookahead) ---
        target_names: List[str] = []
        if bool(regime.loc[prev]):
            erow = elig_frame.loc[prev]
            elig = [s for s in erow.index if bool(erow[s])]
            sig_row = sig_wide.loc[prev]
            ranked = sorted((s for s in elig if pd.notna(sig_row.get(s))),
                            key=lambda s: sig_row[s], reverse=True)
            rank_idx = {s: j for j, s in enumerate(ranked)}
            n_slots = min(params.max_slots, len(ranked))
            target_names = _select(ranked, rank_idx, prev_held, universe.segment,
                                   n_slots, params.segment_cap, params.hysteresis_buffer)
        w_each = min(deployment / len(target_names), max_pos) if target_names else 0.0
        target = {s: w_each for s in target_names}

        # --- turnover + cost at the rebalance ---
        cost_t = 0.0
        for s in set(prev_w) | set(target):
            dw = target.get(s, 0.0) - prev_w.get(s, 0.0)
            if abs(dw) < 1e-9:
                continue
            cost_t += cost.trade_cost(abs(dw) * equity, universe.adv_at(s, prev))
        turnover_s[t] = sum(abs(target.get(s, 0.0) - prev_w.get(s, 0.0)) for s in set(prev_w) | set(target))

        # --- round-trip trade log (entries/exits) ---
        for s in target_names:
            if s not in open_pos:
                open_pos[s] = {"entry_date": prev, "entry_close": float(close_wide.at[prev, s])}
        for s in list(open_pos):
            if s not in target_names:
                ep = open_pos.pop(s)
                ec = float(close_wide.at[prev, s])
                gross = ec / ep["entry_close"] - 1.0 if ep["entry_close"] else 0.0
                trades.append({"symbol": universe.metas[s].base, "entry_date": ep["entry_date"].date().isoformat(),
                               "exit_date": prev.date().isoformat(), "gross_return": gross,
                               "net_return": gross - rt_cost})

        # --- day P&L (hold target over close[prev]->close[t]) ---
        gross_ret = sum(w * ret_wide.at[t, s] for s, w in target.items()
                        if s in ret_wide.columns and pd.notna(ret_wide.at[t, s]))
        equity = equity * (1.0 + gross_ret) - cost_t
        equity_curve[t] = equity
        held_hist[t] = target_names

        # --- vol profile sample ---
        if target_names:
            hv = [rv_wide.at[t, s] for s in target_names if pd.notna(rv_wide.at[t, s])]
            uv = rv_wide.loc[t, elig].dropna()   # `elig` set above (target_names non-empty => regime on)
            if hv:
                held_vol_samples.append(float(np.median(hv)))
            if len(uv):
                univ_vol_samples.append(float(uv.median()))
            majors_share.append(sum(1 for s in target_names if universe.segment(s) == "majors") / len(target_names))

        prev_w, prev_held = target, target_names

    eq = pd.Series(equity_curve).sort_index()
    held_med = float(np.median(held_vol_samples)) if held_vol_samples else float("nan")
    univ_med = float(np.median(univ_vol_samples)) if univ_vol_samples else float("nan")
    vol_profile = {
        "held_median_realized_vol": held_med,
        "universe_median_realized_vol": univ_med,
        "held_vs_universe_vol_ratio": (held_med / univ_med) if univ_med else float("nan"),
        "avg_majors_share_of_book": float(np.mean(majors_share)) if majors_share else 0.0,
        # flag: book is persistently lower-vol than the universe AND majors-heavy -> S1 overlap risk
        "low_vol_majors_hug": bool(univ_med and held_med < 0.85 * univ_med
                                   and (np.mean(majors_share) if majors_share else 0) > 0.34),
    }
    return S3Result(eq, eq.pct_change().dropna(), trades, held_hist,
                    pd.Series(turnover_s).sort_index(), vol_profile,
                    meta={"n_dates": len(dates), "n_trades": len(trades)})
