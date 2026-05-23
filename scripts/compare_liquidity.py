#!/usr/bin/env python
"""Pre-registered: does an account-appropriate eligibility floor raise trade
frequency without breaking quality? For a £2k account, £200 positions are invisible
even in a $1M/day coin, so the institutional $50M filter is mis-set. Tests
$50M / $10M / $1M on the SAME ingested panel for S1 and S2. Backtest only.

Adopt $1M only if (pre-registered): it raises trades vs $10M AND still clears §9
(PF>1.5, DD<25%, Sharpe>0) AND stays robust (subsample median PF >= 1.5)."""
from __future__ import annotations

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

FILTERS = [50_000_000, 10_000_000, 1_000_000]


def main() -> None:
    print(backtest_only_notice())
    cfg_u0, cfg_bt = universe_config(), backtest_config()
    cfg_s = cfg_bt["strategy"]
    panel, metas, _ = load_cached(Cache(ROOT / "data" / "cache"), "coinapi")
    btc = panel[find_btc(metas)]["close"]
    end = max(d.index.max() for d in panel.values())
    fees = FeeModel(taker_pct=cfg_bt["fees"]["taker_pct"], maker_pct=cfg_bt["fees"]["maker_pct"],
                    exit_uses_maker=cfg_bt["fees"]["exit_uses_maker"])
    slip = SlippageModel(per_side_pct=cfg_bt["slippage"]["per_side_pct"])
    eq = float(cfg_bt["equity"]["start_gbp"]) * float(cfg_bt["equity"]["gbp_usd_rate"])
    maxpos = int(cfg_bt["portfolio"]["max_concurrent_positions"])
    maxdep = float(cfg_bt["portfolio"]["max_deployed_pct"])
    rob = cfg_bt["robustness"]

    print(f"\n{len(panel)} coins ingested | window to {end.date()}\n")
    print(f"{'filter':>8}{'sys':>4}{'trades':>8}{'PF':>7}{'ret%':>7}{'maxDD%':>8}{'Sharpe':>8}{'subPFmed':>10}")
    print("-" * 60)
    for flt in FILTERS:
        cfg_u = dict(cfg_u0)
        cfg_u["min_24h_usd_volume"] = flt
        rb = make_rebalance_dates(panel, cfg_u, cfg_s)
        sched = build_schedule(panel, metas, cfg_u, cfg_s, rb)
        start = rb[0]
        for sysname, sysdef in cfg_s["systems"].items():
            lab = "S1" if sysname == "system1" else "S2"
            p = _params(cfg_s, int(sysdef["donchian_entry"]), int(sysdef["donchian_exit"]))
            r = run_backtest(panel, btc, sched, p, fees, slip, eq, start, end, maxpos, maxdep, lab)
            m = metrics_summary(r.equity_curve, r.trades)
            subs = []
            for seed in rob["subsample_seeds"]:
                subset = subsample_symbols(list(panel.keys()), rob["subsample_frac"], seed)
                sp = {s: panel[s] for s in subset}
                sm = {s: metas[s] for s in subset}
                ss = build_schedule(sp, sm, cfg_u, cfg_s, rb)
                rr = run_backtest(sp, btc, ss, p, fees, slip, eq, start, end, maxpos, maxdep, lab)
                subs.append(profit_factor(rr.trades))
            pf = m["profit_factor"]
            pfs = "inf" if pf == float("inf") else f"{pf:.2f}"
            print(f"${flt/1e6:>6.0f}M{lab:>4}{int(m['trade_count']):>8}{pfs:>7}"
                  f"{m['total_return']*100:>6.0f}%{m['max_drawdown']*100:>7.1f}%{m['sharpe']:>8.2f}"
                  f"{distribution(subs)['median']:>10.2f}")


if __name__ == "__main__":
    main()
