#!/usr/bin/env python
"""Read-only diagnostic — resolve the 2.56 (157-coin) vs 2.23 (341-coin) baseline.

The question: does the broader 341-coin cache make S1 trade names BELOW its live $1M
point-in-time liquidity floor (a non-traded superset → 157 baseline stands), or does it
just make the >=$1M universe more COMPLETE (extra names are live-legitimate → discuss)?

Decisive facts this prints (changes NOTHING — pure measurement):
  * S1's backtest schedule applies the $1M PIT filter, so every name S1 TRADES has, by
    construction, cleared $1M point-in-time. We verify that and show each traded name's
    peak point-in-time liquidity, so "sub-$1M" can be checked directly.
  * How many cache names NEVER clear $1M PIT across the FULL window (the genuine
    non-traded superset) vs how many are ever-eligible (S1's real live universe).
  * Which names/trades drive the extra drawdown, with their PIT liquidity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from cts.config import ROOT, backtest_config, universe_config
from cts.data.cache import Cache
from cts.data.universe import (build_schedule, dollar_volume,
                               static_exclusion_reason)
from cts.engine.backtest import run_backtest
from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel
from cts.pipeline import _params, find_btc, load_cached, make_rebalance_dates
from cts.safety import backtest_only_notice

FLOOR = 1_000_000.0
LIQ_WINDOW = 7


def main() -> None:
    print(backtest_only_notice())
    cfg_u, cfg_bt = universe_config(), backtest_config()
    cfg_s = cfg_bt["strategy"]
    sys1 = cfg_s["systems"]["system1"]
    panel, metas, manifest = load_cached(Cache(ROOT / "data" / "cache"), "coinapi")
    btc = panel[find_btc(metas)]["close"]

    base = _params(cfg_s, int(sys1["donchian_entry"]), int(sys1["donchian_exit"]))
    fees = FeeModel(taker_pct=cfg_bt["fees"]["taker_pct"], maker_pct=cfg_bt["fees"]["maker_pct"],
                    exit_uses_maker=cfg_bt["fees"]["exit_uses_maker"])
    slip = SlippageModel(per_side_pct=cfg_bt["slippage"]["per_side_pct"])
    eq = float(cfg_bt["equity"]["start_gbp"]) * float(cfg_bt["equity"]["gbp_usd_rate"])
    common = dict(fee_model=fees, slippage=slip, start_equity_usd=eq,
                  max_positions=int(cfg_bt["portfolio"]["max_concurrent_positions"]),
                  max_deployed_pct=float(cfg_bt["portfolio"]["max_deployed_pct"]), system_name="S1")

    rebalance = make_rebalance_dates(panel, cfg_u, cfg_s)
    sched = build_schedule(panel, metas, cfg_u, cfg_s, rebalance)
    full_start, full_end = rebalance[0], max(df.index.max() for df in panel.values())

    # peak point-in-time liquidity (max over the whole window of the trailing 7d median $vol)
    peak_pit = {}
    for sid, df in panel.items():
        med = dollar_volume(df).rolling(LIQ_WINDOW, min_periods=LIQ_WINDOW).median()
        peak_pit[sid] = float(med.max()) if med.notna().any() else 0.0

    non_excluded = [sid for sid in panel if static_exclusion_reason(metas[sid], cfg_u) is None]
    ever_elig = set().union(*sched.eligible_by_date.values()) if sched.eligible_by_date else set()
    ever_top = set().union(*sched.top_tier_by_date.values()) if sched.top_tier_by_date else set()

    head = run_backtest(panel, btc, sched, base, start=full_start, end=full_end, **common)
    traded = {t.symbol for t in head.trades}

    # names that COULD never enter the live universe (never cleared $1M PIT) = non-traded superset
    never_cleared = [sid for sid in non_excluded if peak_pit[sid] < FLOOR]
    cleared = [sid for sid in non_excluded if peak_pit[sid] >= FLOOR]

    print(f"\nCache window {full_start.date()}..{full_end.date()}  (survivorship_clean={manifest.get('survivorship_clean')})")
    print("\n===== universe completeness (live $1M point-in-time filter) =====")
    print(f"  cache names (after static exclusions): {len(non_excluded)}  (raw cache {len(panel)})")
    print(f"  ever cleared $1M PIT (peak trailing-7d-median >= $1M): {len(cleared)}")
    print(f"  NEVER cleared $1M PIT  (non-traded superset):          {len(never_cleared)}")
    print(f"  ever ELIGIBLE point-in-time (>= $1M AND >=90d history): {len(ever_elig)}")
    print(f"  ever TOP-TIER (eligible & top momentum):                {len(ever_top)}")
    print(f"  distinct names S1 actually TRADED:                      {len(traded)}")

    # sanity: is any TRADED name below the $1M floor?
    traded_below = [sid for sid in traded if peak_pit[sid] < FLOOR]
    print(f"\n  traded names whose peak PIT liquidity is BELOW $1M: {len(traded_below)}")
    if traded_below:
        for sid in traded_below:
            print(f"    !! {metas[sid].base:>8}  peak PIT ${peak_pit[sid]/1e6:.2f}M  (would NOT be in live universe)")
    else:
        print("    -> none. Every name S1 traded cleared $1M point-in-time = S1's live filter.")

    # traded names by net P&L, with PIT liquidity (most marginal liquidity first)
    by_name = {}
    for t in head.trades:
        d = by_name.setdefault(t.symbol, {"n": 0, "net": 0.0})
        d["n"] += 1; d["net"] += t.net_pnl
    print("\n===== traded names (sorted by peak PIT liquidity, most marginal first) =====")
    print(f"  {'base':>8} {'trades':>7} {'net_pnl':>10} {'peak_PIT_$vol':>14}")
    for sid in sorted(traded, key=lambda s: peak_pit[s]):
        d = by_name[sid]
        print(f"  {metas[sid].base:>8} {d['n']:>7} {d['net']:>10.1f} {peak_pit[sid]/1e6:>12.2f}M")

    # biggest losers (what drives the extra drawdown), with PIT liquidity
    losers = sorted(head.trades, key=lambda t: t.net_pnl)[:10]
    print("\n===== 10 biggest losing trades (drawdown drivers) =====")
    print(f"  {'base':>8} {'entry':>11} {'exit':>11} {'net_pnl':>9} {'reason':>11} {'peak_PIT_$vol':>13}")
    for t in losers:
        print(f"  {metas[t.symbol].base:>8} {str(t.entry_date.date()):>11} {str(t.exit_date.date()):>11} "
              f"{t.net_pnl:>9.1f} {t.exit_reason:>11} {peak_pit[t.symbol]/1e6:>11.2f}M")


if __name__ == "__main__":
    main()
