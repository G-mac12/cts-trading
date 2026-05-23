#!/usr/bin/env python
"""Pre-registered one-shot test: does adding the pullback-in-uptrend entry earn its
place? Compares breakout-only vs +pullback for S1 and S2 on the existing universe.
Reports trade count, headline metrics, and universe-subsample median PF (robustness).
Backtest only — no orders."""
from __future__ import annotations

from dataclasses import replace

from cts.config import ROOT, backtest_config, universe_config
from cts.data.cache import Cache
from cts.data.universe import build_schedule
from cts.engine.backtest import run_backtest
from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel
from cts.metrics.performance import metrics_summary, profit_factor
from cts.metrics.robustness import distribution, subsample_symbols
from cts.pipeline import _params, find_btc, load_cached, make_rebalance_dates
from cts.safety import backtest_only_notice


def main() -> None:
    print(backtest_only_notice())
    cfg_u, cfg_bt = universe_config(), backtest_config()
    cfg_s = cfg_bt["strategy"]
    panel, metas, _ = load_cached(Cache(ROOT / "data" / "cache"), "coinapi")
    btc = panel[find_btc(metas)]["close"]
    rb = make_rebalance_dates(panel, cfg_u, cfg_s)
    sched = build_schedule(panel, metas, cfg_u, cfg_s, rb)
    start, end = rb[0], max(d.index.max() for d in panel.values())
    fees = FeeModel(taker_pct=cfg_bt["fees"]["taker_pct"], maker_pct=cfg_bt["fees"]["maker_pct"],
                    exit_uses_maker=cfg_bt["fees"]["exit_uses_maker"])
    slip = SlippageModel(per_side_pct=cfg_bt["slippage"]["per_side_pct"])
    eq = float(cfg_bt["equity"]["start_gbp"]) * float(cfg_bt["equity"]["gbp_usd_rate"])
    maxpos = int(cfg_bt["portfolio"]["max_concurrent_positions"])
    maxdep = float(cfg_bt["portfolio"]["max_deployed_pct"])
    rob = cfg_bt["robustness"]

    def run_variant(label, p):
        r = run_backtest(panel, btc, sched, p, fees, slip, eq, start, end, maxpos, maxdep, label)
        m = metrics_summary(r.equity_curve, r.trades)
        subs = []
        for seed in rob["subsample_seeds"]:
            subset = subsample_symbols(list(panel.keys()), rob["subsample_frac"], seed)
            sp = {s: panel[s] for s in subset}
            sm = {s: metas[s] for s in subset}
            ss = build_schedule(sp, sm, cfg_u, cfg_s, rb)
            rr = run_backtest(sp, btc, ss, p, fees, slip, eq, start, end, maxpos, maxdep, label)
            subs.append(profit_factor(rr.trades))
        return m, distribution(subs)["median"]

    variants = {}
    for sysname, sysdef in cfg_s["systems"].items():
        lab = "S1" if sysname == "system1" else "S2"
        base = _params(cfg_s, int(sysdef["donchian_entry"]), int(sysdef["donchian_exit"]))
        variants[f"{lab} breakout-only"] = base
        variants[f"{lab} +pullback"] = replace(base, pullback_entry=True)

    print(f"\nWindow {start.date()}..{end.date()} | {len(panel)} coins\n")
    print(f"{'variant':<20}{'trades':>8}{'PF':>7}{'ret%':>8}{'maxDD%':>8}{'Sharpe':>8}{'subPFmed':>10}")
    print("-" * 69)
    for lab, p in variants.items():
        m, subm = run_variant(lab, p)
        pf = m["profit_factor"]
        pfs = "inf" if pf == float("inf") else f"{pf:.2f}"
        print(f"{lab:<20}{int(m['trade_count']):>8}{pfs:>7}{m['total_return']*100:>7.0f}%"
              f"{m['max_drawdown']*100:>7.1f}%{m['sharpe']:>8.2f}{subm:>10.2f}")


if __name__ == "__main__":
    main()
