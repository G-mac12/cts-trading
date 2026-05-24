#!/usr/bin/env python
"""S3 full-period backtest SMOKE (read-only, no orders). Confirms the engine runs on
real survivorship-clean data and gives an early read + the 2x-slippage sensitivity +
the vol profile. This is NOT the gated verdict — walk-forward split + bootstrap CIs +
gate-or-retire come in S3-D/E. No metric here is a pass/fail.
"""
from __future__ import annotations

from dataclasses import replace

import pandas as pd

from cts.config import ROOT, backtest_config, load_yaml
from cts.data.cache import Cache
from cts.metrics.performance import cagr, max_drawdown, sharpe, total_return
from cts.pipeline import find_btc, load_cached
from cts.s3.cost import CostModel
from cts.s3.rotation import S3Params, run_s3
from cts.s3.universe import S3Universe
from cts.safety import backtest_only_notice


def _pf(trades):
    pos = sum(t["net_return"] for t in trades if t["net_return"] > 0)
    neg = -sum(t["net_return"] for t in trades if t["net_return"] < 0)
    return (pos / neg) if neg else float("inf")


def main() -> None:
    print(backtest_only_notice())
    cfg = load_yaml("s3.yml")
    panel, metas, _ = load_cached(Cache(ROOT / "data" / "cache"), "coinapi")
    btc = panel[find_btc(metas)]["close"]
    uni = S3Universe(panel, metas, cfg["universe"])
    params = S3Params(
        lookback_days=cfg["signal"]["lookback_days"], skip_days=cfg["signal"]["skip_days"],
        vol_window_days=cfg["signal"]["vol_window_days"], max_slots=cfg["portfolio"]["max_slots"],
        segment_cap=cfg["portfolio"]["segment_cap"], hysteresis_buffer=cfg["portfolio"]["hysteresis_buffer"],
        total_deployment_pct=cfg["portfolio"]["total_deployment_pct"],
        max_position_pct=cfg["portfolio"]["max_position_pct"],
        regime_ma_short=cfg["regime"]["ma_short"], regime_ma_long=cfg["regime"]["ma_long"])
    cost = CostModel(taker_pct=cfg["cost"]["taker_pct"], slippage_base_bps=cfg["cost"]["slippage_base_bps"],
                     slippage_impact_coef=cfg["cost"]["slippage_impact_coef"])
    eq = float(cfg["equity"]["start_gbp"]) * float(cfg["equity"]["gbp_usd_rate"])
    start = pd.Timestamp("2019-01-01", tz="UTC")
    end = max(df.index.max() for df in panel.values())

    print(f"\nS3 SMOKE (full-period, NOT gated) — {len(panel)} coins, {start.date()}..{end.date()}\n")
    print(f"{'variant':<16}{'trades':>8}{'ret%':>9}{'CAGR%':>8}{'maxDD%':>9}{'Sharpe':>8}{'PF':>7}{'avgHeld':>9}")
    for label, mult in [("base cost", 1.0), ("2x slippage", 2.0)]:
        c = replace(cost, slippage_mult=mult)
        r = run_s3(panel, btc, uni, params, c, eq, start, end)
        held_sizes = [len(h) for h in r.held_history.values() if h]
        avg_held = sum(held_sizes) / len(held_sizes) if held_sizes else 0
        pf = _pf(r.trades)
        pfs = "inf" if pf == float("inf") else f"{pf:.2f}"
        print(f"{label:<16}{len(r.trades):>8}{total_return(r.equity_curve)*100:>8.0f}%"
              f"{cagr(r.equity_curve)*100:>7.1f}%{max_drawdown(r.equity_curve)*100:>8.1f}%"
              f"{sharpe(r.daily_returns):>8.2f}{pfs:>7}{avg_held:>9.1f}")
        if mult == 1.0:
            vp = r.vol_profile
            print(f"\nvol profile: held median realized vol {vp['held_median_realized_vol']:.4f} vs "
                  f"universe {vp['universe_median_realized_vol']:.4f} "
                  f"(ratio {vp['held_vs_universe_vol_ratio']:.2f}); "
                  f"avg majors share of book {vp['avg_majors_share_of_book']*100:.0f}%; "
                  f"LOW-VOL-MAJORS-HUG FLAG = {vp['low_vol_majors_hug']}\n")


if __name__ == "__main__":
    main()
