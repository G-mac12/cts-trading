#!/usr/bin/env python
"""S3-D/E — the gate. Walk-forward (held-out OOS), net-of-cost, bootstrap CIs on the
effective sample, deployment sized on IS, hysteresis/cap sweep, 2x-slippage check, and
the S3<->S1 equity-correlation check. Thresholds are LOCKED here BEFORE the run; the
verdict is PASS or RETIRE — no loosening after seeing results.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from cts.config import ROOT, backtest_config, load_yaml, universe_config
from cts.data.cache import Cache
from cts.data.universe import build_schedule
from cts.engine.backtest import run_backtest
from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel
from cts.metrics.performance import max_drawdown, sharpe as sharpe_series, total_return
from cts.pipeline import _params, find_btc, load_cached, make_rebalance_dates
from cts.s3.bootstrap import (avg_pairwise_corr, ci, effective_n, maxdd_stat, pf_stat,
                              sharpe_stat, stationary_bootstrap)
from cts.s3.cost import CostModel
from cts.s3.rotation import S3Params, run_s3
from cts.s3.universe import S3Universe
from cts.safety import backtest_only_notice

# ---- GATE THRESHOLDS (locked before running) ----
GATE = {"min_net_pf": 1.3, "min_sharpe": 0.78, "max_dd": 0.25,
        "min_pf_lower_ci": 1.0, "max_s1_corr": 0.60}
IS = ("2019-01-01", "2022-12-31")
OOS = ("2023-01-01", "2026-12-31")


def _pf(trades):
    r = np.array([t["net_return"] for t in trades], dtype="float64")
    return pf_stat(r), r


def _make_params(cfg, **over):
    p = S3Params(
        lookback_days=cfg["signal"]["lookback_days"], skip_days=cfg["signal"]["skip_days"],
        vol_window_days=cfg["signal"]["vol_window_days"], max_slots=cfg["portfolio"]["max_slots"],
        segment_cap=cfg["portfolio"]["segment_cap"], hysteresis_buffer=cfg["portfolio"]["hysteresis_buffer"],
        total_deployment_pct=cfg["portfolio"]["total_deployment_pct"],
        max_position_pct=cfg["portfolio"]["max_position_pct"],
        regime_ma_short=cfg["regime"]["ma_short"], regime_ma_long=cfg["regime"]["ma_long"])
    return replace(p, **over)


def main() -> None:
    print(backtest_only_notice())
    cfg = load_yaml("s3.yml")
    panel, metas, _ = load_cached(Cache(ROOT / "data" / "cache"), "coinapi")
    btc = panel[find_btc(metas)]["close"]
    uni = S3Universe(panel, metas, cfg["universe"])
    cost = CostModel(taker_pct=cfg["cost"]["taker_pct"], slippage_base_bps=cfg["cost"]["slippage_base_bps"],
                     slippage_impact_coef=cfg["cost"]["slippage_impact_coef"])
    eq = float(cfg["equity"]["start_gbp"]) * float(cfg["equity"]["gbp_usd_rate"])
    is_a, is_b = pd.Timestamp(IS[0], tz="UTC"), pd.Timestamp(IS[1], tz="UTC")
    oos_a = pd.Timestamp(OOS[0], tz="UTC")
    oos_b = max(df.index.max() for df in panel.values())

    # 1) size deployment on IS so IS maxDD ~ 25% (edge-neutral; PF/Sharpe are scale-invariant)
    is_run = run_s3(panel, btc, uni, _make_params(cfg, total_deployment_pct=100.0), cost, eq, is_a, is_b)
    is_dd = abs(max_drawdown(is_run.equity_curve)) or 1.0
    deployment = float(np.clip(GATE["max_dd"] / is_dd * 100.0, 10.0, 100.0))
    print(f"\nIS maxDD @100% = {is_dd*100:.1f}%  ->  deployment sized to {deployment:.0f}% (to target 25% DD)")

    # 2) OOS run at sized deployment, default params
    params = _make_params(cfg, total_deployment_pct=deployment)
    oos = run_s3(panel, btc, uni, params, cost, eq, oos_a, oos_b)
    pf, trade_rets = _pf(oos.trades)
    dr = oos.daily_returns.to_numpy()
    oos_sharpe = sharpe_series(oos.daily_returns)
    oos_dd = max_drawdown(oos.equity_curve)
    oos_ret = total_return(oos.equity_curve)

    # 3) bootstrap CIs (stationary, preserves autocorrelation)
    pf_dist = stationary_bootstrap(trade_rets, pf_stat, n_boot=1000, mean_block=5)
    sh_dist = stationary_bootstrap(dr, sharpe_stat, n_boot=1000, mean_block=10)
    dd_dist = stationary_bootstrap(dr, maxdd_stat, n_boot=1000, mean_block=10)
    pf_lo, pf_hi = ci(pf_dist); sh_lo, sh_hi = ci(sh_dist); dd_lo, dd_hi = ci(dd_dist)

    # 4) effective sample: rho-bar of held names' OOS daily returns -> N_eff
    held = sorted({s for names in oos.held_history.values() for s in names})
    rets_df = pd.DataFrame({s: panel[s]["close"] for s in held}).loc[oos_a:oos_b].pct_change().dropna(how="all")
    rho_bar = avg_pairwise_corr(rets_df)
    n_eff = effective_n(len(oos.trades), rho_bar)

    # 5) 2x slippage on the same config
    oos_2x = run_s3(panel, btc, uni, params, replace(cost, slippage_mult=2.0), eq, oos_a, oos_b)
    pf_2x, _ = _pf(oos_2x.trades)

    # 6) sweep hysteresis buffer x segment cap (OOS net PF distribution)
    sweep = []
    for buf in (0, 3, 6):
        for cap in (2, 3, 0):
            r = run_s3(panel, btc, uni, replace(params, hysteresis_buffer=buf, segment_cap=cap), cost, eq, oos_a, oos_b)
            sweep.append(_pf(r.trades)[0])
    sweep = [s for s in sweep if np.isfinite(s)]
    sweep_med = float(np.median(sweep)) if sweep else 0.0

    # 7) S3<->S1 equity correlation over OOS (S1 run on the same data)
    cfg_u, cfg_bt = universe_config(), backtest_config()
    cfg_s = cfg_bt["strategy"]
    sys1 = cfg_s["systems"]["system1"]
    s1 = run_backtest(panel, btc, build_schedule(panel, metas, cfg_u, cfg_s, make_rebalance_dates(panel, cfg_u, cfg_s)),
                      _params(cfg_s, int(sys1["donchian_entry"]), int(sys1["donchian_exit"])),
                      FeeModel(taker_pct=cfg_bt["fees"]["taker_pct"], maker_pct=cfg_bt["fees"]["maker_pct"],
                               exit_uses_maker=cfg_bt["fees"]["exit_uses_maker"]),
                      SlippageModel(per_side_pct=cfg_bt["slippage"]["per_side_pct"]),
                      eq, oos_a, oos_b, int(cfg_bt["portfolio"]["max_concurrent_positions"]),
                      float(cfg_bt["portfolio"]["max_deployed_pct"]), "S1")
    s1_dr = s1.equity_curve.pct_change()
    join = pd.concat([oos.daily_returns.rename("s3"), s1_dr.rename("s1")], axis=1).dropna()
    s1_corr = float(join["s3"].corr(join["s1"])) if len(join) > 5 else float("nan")

    # ---- verdict ----
    vp = oos.vol_profile
    checks = {
        "net OOS PF >= 1.3": pf >= GATE["min_net_pf"],
        "net OOS Sharpe >= 0.78": oos_sharpe >= GATE["min_sharpe"],
        "OOS maxDD <= -25%": oos_dd > -GATE["max_dd"],
        "lower-CI net PF > 1.0": (pf_lo > GATE["min_pf_lower_ci"]) if np.isfinite(pf_lo) else False,
        "S3<->S1 corr < 0.6": (s1_corr < GATE["max_s1_corr"]) if np.isfinite(s1_corr) else False,
        "survives 2x slippage (PF>=1.3)": pf_2x >= GATE["min_net_pf"],
        "sweep median PF >= 1.3": sweep_med >= GATE["min_net_pf"],
    }
    verdict = "PASS" if all(checks.values()) else "RETIRE"

    print(f"\n===== S3 GATE — OOS {oos_a.date()}..{oos_b.date()} (deployment {deployment:.0f}%) =====")
    print(f"trades={len(oos.trades)}  N_eff={n_eff:.1f} (rho_bar={rho_bar:.2f})  return={oos_ret*100:.0f}%")
    print(f"net PF        {pf:.2f}   CI[{pf_lo:.2f}, {pf_hi:.2f}]   (2x slippage PF {pf_2x:.2f})")
    print(f"Sharpe        {oos_sharpe:.2f}   CI[{sh_lo:.2f}, {sh_hi:.2f}]")
    print(f"max DD        {oos_dd*100:.1f}%  CI[{dd_lo*100:.1f}%, {dd_hi*100:.1f}%]")
    print(f"sweep PF      median {sweep_med:.2f}  (n={len(sweep)} buffer x cap combos)")
    print(f"S3<->S1 corr  {s1_corr:.2f}")
    print(f"vol profile   held/universe vol {vp['held_vs_universe_vol_ratio']:.2f}, "
          f"majors {vp['avg_majors_share_of_book']*100:.0f}%, low-vol-majors-hug {vp['low_vol_majors_hug']}")
    print("-" * 60)
    for k, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}]  {k}")
    print(f"\n>>> VERDICT: {verdict} <<<\n")


if __name__ == "__main__":
    main()
