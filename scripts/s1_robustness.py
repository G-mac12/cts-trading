#!/usr/bin/env python
"""S1 robustness audit on the EXISTING backtest — read-only, S1 UNTOUCHED.

After S3 fell into the in-sample trap (a +705% full-period smoke that was really one
2021 bull, gone out-of-sample), the honest question is whether S1 has a milder version
of the same disease. This script answers two things, with REAL numbers from the tested
engine — it changes nothing about the live system, the config, or the paper run:

  1) CONCENTRATION — does the edge live in a single year or a single regime?
     * per-calendar-year: return, net P&L, profit factor, trade count, share of profit
     * "drop the single best year" PF: if the edge collapses to ~1.0 without its best
       year, it is concentrated/fragile (the S3 failure mode)
     * per-regime decomposition (bull/bear/chop), reusing the §9 regime decomposer

  2) PLATEAU vs PEAK — is S1 a robust plateau or a fragile knife-edge across its key
     parameters?
     * Donchian breakout length (Turtle-proportional entry/exit pairs around 20/10)
     * Rebalance cadence (5/7/10/14 days) — rebuilds the point-in-time schedule
     * Risk-per-position sizing (0.4/0.6/0.8/1.0%) — to CONFIRM sizing is edge-neutral
       (PF/Sharpe ~flat while return & drawdown scale), i.e. risk control, not tuning

Everything runs net of Kraken-Pro fees + slippage on the survivorship-clean cache.
"""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pandas as pd

from cts.config import ROOT, backtest_config, universe_config
from cts.data.cache import Cache
from cts.data.universe import build_schedule
from cts.engine.backtest import run_backtest
from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel
from cts.metrics.performance import (max_drawdown, metrics_summary, profit_factor,
                                     sharpe, total_return)
from cts.metrics.regime_decomp import classify_regime, decompose
from cts.pipeline import _params, find_btc, load_cached, make_rebalance_dates
from cts.safety import backtest_only_notice


def _common(cfg_bt):
    fees = FeeModel(taker_pct=cfg_bt["fees"]["taker_pct"], maker_pct=cfg_bt["fees"]["maker_pct"],
                    exit_uses_maker=cfg_bt["fees"]["exit_uses_maker"])
    slip = SlippageModel(per_side_pct=cfg_bt["slippage"]["per_side_pct"])
    eq = float(cfg_bt["equity"]["start_gbp"]) * float(cfg_bt["equity"]["gbp_usd_rate"])
    return dict(fee_model=fees, slippage=slip, start_equity_usd=eq,
                max_positions=int(cfg_bt["portfolio"]["max_concurrent_positions"]),
                max_deployed_pct=float(cfg_bt["portfolio"]["max_deployed_pct"]),
                system_name="S1")


def year_breakdown(equity: pd.Series, trades) -> list:
    rows = []
    total_net = sum(t.net_pnl for t in trades) or float("nan")
    years = sorted({t.entry_date.year for t in trades})
    for y in years:
        a = pd.Timestamp(f"{y}-01-01", tz="UTC")
        b = pd.Timestamp(f"{y}-12-31 23:59:59", tz="UTC")
        eq_y = equity[(equity.index >= a) & (equity.index <= b)]
        yr = [t for t in trades if t.entry_date.year == y]
        net = sum(t.net_pnl for t in yr)
        rows.append({
            "year": y,
            "trades": len(yr),
            "net_pnl": round(net, 1),
            "share_of_total_pnl": round(net / total_net, 3) if total_net and np.isfinite(total_net) else None,
            "return_in_year": round(total_return(eq_y), 4) if len(eq_y) > 1 else 0.0,
            "profit_factor": round(profit_factor(yr), 3),
        })
    return rows


def drop_best_year(trades) -> dict:
    """PF with the single most-profitable calendar year removed."""
    years = sorted({t.entry_date.year for t in trades})
    by_year = {y: sum(t.net_pnl for t in trades if t.entry_date.year == y) for y in years}
    best = max(by_year, key=by_year.get) if by_year else None
    rest = [t for t in trades if t.entry_date.year != best]
    return {
        "best_year": best,
        "best_year_net_pnl": round(by_year[best], 1) if best is not None else None,
        "pf_all": round(profit_factor(trades), 3),
        "pf_excluding_best_year": round(profit_factor(rest), 3) if rest else None,
        "trades_excluding_best_year": len(rest),
    }


def summarise(res) -> dict:
    m = metrics_summary(res.equity_curve, res.trades)
    return {"trades": int(m["trade_count"]), "pf": round(m["profit_factor"], 3),
            "return": round(m["total_return"], 4), "maxDD": round(m["max_drawdown"], 4),
            "sharpe": round(m["sharpe"], 3)}


def main() -> None:
    print(backtest_only_notice())
    cfg_u, cfg_bt = universe_config(), backtest_config()
    cfg_s = cfg_bt["strategy"]
    sys1 = cfg_s["systems"]["system1"]
    panel, metas, manifest = load_cached(Cache(ROOT / "data" / "cache"), "coinapi")
    btc = panel[find_btc(metas)]["close"]
    common = _common(cfg_bt)
    base = _params(cfg_s, int(sys1["donchian_entry"]), int(sys1["donchian_exit"]))

    rebalance = make_rebalance_dates(panel, cfg_u, cfg_s)
    sched = build_schedule(panel, metas, cfg_u, cfg_s, rebalance)
    full_start = rebalance[0]
    full_end = max(df.index.max() for df in panel.values())

    print(f"\nUniverse: {len(panel)} coins  window {full_start.date()}..{full_end.date()}  "
          f"survivorship_clean={manifest.get('survivorship_clean')}")

    # ---- headline S1 (chosen params, full window) ----
    head = run_backtest(panel, btc, sched, base, start=full_start, end=full_end, **common)
    hsum = summarise(head)
    print("\n===== HEADLINE S1 (donchian 20/10, risk 0.6%, rebalance 7d) =====")
    print(f"  trades={hsum['trades']}  PF={hsum['pf']}  return={hsum['return']*100:.0f}%  "
          f"maxDD={hsum['maxDD']*100:.1f}%  Sharpe={hsum['sharpe']}")

    # ---- 1a) per-year concentration ----
    yb = year_breakdown(head.equity_curve, head.trades)
    print("\n----- per-year breakdown -----")
    print(f"  {'year':>5} {'trades':>7} {'net_pnl':>10} {'share':>7} {'yr_ret':>8} {'PF':>6}")
    for r in yb:
        sh = "n/a" if r["share_of_total_pnl"] is None else f"{r['share_of_total_pnl']*100:5.0f}%"
        print(f"  {r['year']:>5} {r['trades']:>7} {r['net_pnl']:>10.1f} {sh:>7} "
              f"{r['return_in_year']*100:7.0f}% {r['profit_factor']:>6.2f}")

    dby = drop_best_year(head.trades)
    print("\n----- concentration: drop the single best year -----")
    print(f"  best year = {dby['best_year']} (net ${dby['best_year_net_pnl']})")
    print(f"  PF all = {dby['pf_all']}   PF excluding best year = {dby['pf_excluding_best_year']} "
          f"(on {dby['trades_excluding_best_year']} trades)")

    # ---- 1b) per-regime decomposition ----
    labels = classify_regime(btc, cfg_bt["regime_decomp"]["ma_short"], cfg_bt["regime_decomp"]["ma_long"])
    reg = decompose(head.equity_curve, head.trades, labels)
    print("\n----- per-regime decomposition (independent BTC classification) -----")
    print(f"  {'regime':>6} {'%period':>8} {'exposure':>9} {'comp_ret':>9} {'maxDD':>8} {'trades':>7} {'net_pnl':>9}")
    for lab in ("bull", "bear", "chop"):
        d = reg[lab]
        print(f"  {lab:>6} {d['pct_of_period']*100:7.0f}% {d['exposure']*100:8.0f}% "
              f"{d['compounded_return']*100:8.0f}% {d['max_drawdown']*100:7.1f}% "
              f"{int(d['trades_entered']):>7} {d['trades_net_pnl']:>9.1f}")

    # ---- 2a) Donchian breakout length sweep (Turtle-proportional entry/exit) ----
    don_pairs = [(10, 5), (15, 7), (20, 10), (25, 12), (30, 15), (40, 20), (55, 27)]
    print("\n===== PLATEAU vs PEAK =====")
    print("\n----- Donchian length sweep (exit = entry//2) -----")
    print(f"  {'entry/exit':>11} {'trades':>7} {'PF':>6} {'return':>8} {'maxDD':>8} {'Sharpe':>7}")
    don_rows = []
    for ne, nx in don_pairs:
        r = run_backtest(panel, btc, sched, replace(base, n_entry=ne, n_exit=nx),
                         start=full_start, end=full_end, **common)
        s = summarise(r); s["entry"], s["exit"] = ne, nx; don_rows.append(s)
        mark = "  <- chosen" if (ne, nx) == (20, 10) else ""
        print(f"  {f'{ne}/{nx}':>11} {s['trades']:>7} {s['pf']:>6.2f} {s['return']*100:7.0f}% "
              f"{s['maxDD']*100:7.1f}% {s['sharpe']:>7.2f}{mark}")

    # ---- 2b) rebalance cadence sweep (rebuilds the point-in-time schedule) ----
    print("\n----- rebalance cadence sweep -----")
    print(f"  {'days':>5} {'rebals':>7} {'trades':>7} {'PF':>6} {'return':>8} {'maxDD':>8} {'Sharpe':>7}")
    reb_rows = []
    for days in (5, 7, 10, 14):
        cfg_s_d = dict(cfg_s); cfg_s_d["xs_rebalance_days"] = days
        rdates = make_rebalance_dates(panel, cfg_u, cfg_s_d)
        sched_d = build_schedule(panel, metas, cfg_u, cfg_s_d, rdates)
        r = run_backtest(panel, btc, sched_d, base, start=rdates[0], end=full_end, **common)
        s = summarise(r); s["days"] = days; s["rebals"] = len(rdates); reb_rows.append(s)
        mark = "  <- chosen" if days == 7 else ""
        print(f"  {days:>5} {len(rdates):>7} {s['trades']:>7} {s['pf']:>6.2f} {s['return']*100:7.0f}% "
              f"{s['maxDD']*100:7.1f}% {s['sharpe']:>7.2f}{mark}")

    # ---- 2c) risk sizing sweep (expect PF/Sharpe ~flat, return/DD scale = edge-neutral) ----
    print("\n----- risk-per-position sweep (edge-neutrality check) -----")
    print(f"  {'risk%':>6} {'trades':>7} {'PF':>6} {'return':>8} {'maxDD':>8} {'Sharpe':>7}")
    risk_rows = []
    for rk in (0.4, 0.6, 0.8, 1.0):
        r = run_backtest(panel, btc, sched, replace(base, risk_per_position_pct=rk),
                         start=full_start, end=full_end, **common)
        s = summarise(r); s["risk"] = rk; risk_rows.append(s)
        mark = "  <- chosen" if rk == 0.6 else ""
        print(f"  {rk:>6.1f} {s['trades']:>7} {s['pf']:>6.2f} {s['return']*100:7.0f}% "
              f"{s['maxDD']*100:7.1f}% {s['sharpe']:>7.2f}{mark}")

    # ---- plateau read-outs ----
    don_pf = [r["pf"] for r in don_rows]
    reb_pf = [r["pf"] for r in reb_rows]
    risk_pf = [r["pf"] for r in risk_rows]
    risk_sh = [r["sharpe"] for r in risk_rows]
    print("\n----- plateau read-outs -----")
    print(f"  Donchian PF:  min {min(don_pf):.2f}  median {np.median(don_pf):.2f}  max {max(don_pf):.2f}")
    print(f"  rebalance PF: min {min(reb_pf):.2f}  median {np.median(reb_pf):.2f}  max {max(reb_pf):.2f}")
    print(f"  risk PF spread {max(risk_pf)-min(risk_pf):.2f}  |  Sharpe spread {max(risk_sh)-min(risk_sh):.2f}"
          f"  (small => sizing is edge-neutral)")

    out = {
        "window": [full_start.date().isoformat(), full_end.date().isoformat()],
        "universe_coins": len(panel),
        "headline": hsum,
        "per_year": yb,
        "drop_best_year": dby,
        "per_regime": reg,
        "donchian_sweep": don_rows,
        "rebalance_sweep": reb_rows,
        "risk_sweep": risk_rows,
    }
    dest = ROOT / "data" / "s1_robustness.json"
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
