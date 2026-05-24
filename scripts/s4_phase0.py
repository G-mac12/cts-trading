#!/usr/bin/env python
"""S4 PHASE 0 — the killer question (cost-viability), read-only, builds no strategy.

Can a plausible daily-reset Opening-Range Breakout on the liquid probe set clear Kraken
intraday costs at ~£2k, NET, base AND 2x cost? We simulate a SENSIBLE ORB purely to
measure (a) realistic trade frequency and (b) the gross per-trade capture actually in the
data, then compare against the modelled round-trip cost hurdle (fees + spread + intraday
slippage). This is a feasibility model, NOT the gated harness — no walk-forward/bootstrap
yet; those are Phase 1/2 and only happen if Gate-0 shows headroom.

Pre-registered ORB defaults (sensible starting values, not tuned):
  opening range = first 4 UTC hours (00:00–03:00); entries on hourly CLOSE 04:00–22:00;
  filters = close > OR-high AND close > session VWAP AND RVOL >= 1.5; regime = S1's daily
  BTC risk-on (50/100); exit = intraday 1.5*ATR(14) stop OR end-of-session (23:00) flat;
  one entry per instrument per day. Long-only spot.

Cost model (intraday, base and 2x):
  fees   = Kraken Pro taker 0.40% per side  -> 0.80% round trip
  spread = per-name full-spread round trip (BTC 2bp / ETH 3bp / SOL 8bp, conservative)
  slip   = S3 ADV-proxy but on INTRADAY (hourly) bar volume, both sides
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from cts.config import ROOT
from cts.data.cache import Cache
from cts.s3.cost import CostModel
from cts.safety import backtest_only_notice
from cts.strategy.regime import regime_on

SOURCE_INTRADAY = "coinapi_intraday"
SOURCE_DAILY = "coinapi"
PERIOD = "1HRS"
PROBE = {"BTC": "KRAKEN_SPOT_BTC_USD", "ETH": "KRAKEN_SPOT_ETH_USD", "SOL": "KRAKEN_SPOT_SOL_USD"}
BTC_DAILY = "KRAKEN_SPOT_BTC_USD"

# --- pre-registered ORB params ---
OR_HOURS = 4
ENTRY_FROM_H, ENTRY_TO_H = 4, 22
SESSION_END_H = 23
RVOL_MIN = 1.5
RVOL_WINDOW = 168          # trailing 7 days of hourly bars
ATR_WINDOW = 14
STOP_ATR = 1.5
REGIME_SHORT, REGIME_LONG = 50, 100

# --- cost assumptions ---
TAKER_PCT = 0.40           # per side
SPREAD_RT_BPS = {"BTC": 2.0, "ETH": 3.0, "SOL": 8.0}   # full spread, round trip
ORDER_USD = 400.0          # ~ one position from a £2k book (for slippage participation)


def atr(df: pd.DataFrame, window: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def simulate(name: str, df: pd.DataFrame, regime_daily: pd.Series, cost: CostModel) -> list:
    df = df.sort_index()
    df = df[(df.index >= regime_daily.index.min()) & (df.index <= regime_daily.index.max() + pd.Timedelta(days=1))]
    df = df.copy()
    df["atr"] = atr(df, ATR_WINDOW)
    df["rvol_base"] = df["volume"].rolling(RVOL_WINDOW, min_periods=RVOL_WINDOW).mean()
    spread_rt = SPREAD_RT_BPS[name] / 1e4
    fee_rt = 2.0 * TAKER_PCT / 100.0

    trades = []
    for d, rows in df.groupby(df.index.date, sort=True):
        h = rows.index.hour
        or_bars = rows[h < OR_HOURS]
        if len(or_bars) < OR_HOURS:
            continue
        rd = regime_daily.get(pd.Timestamp(d, tz="UTC"))
        if rd is None or not bool(rd):
            continue
        or_high = or_bars["high"].max()
        tp = (rows["high"] + rows["low"] + rows["close"]) / 3.0
        vwap = (tp * rows["volume"]).cumsum() / rows["volume"].cumsum()
        sess = rows[(h >= ENTRY_FROM_H)]
        entered = False
        for t, r in sess.iterrows():
            if t.hour > ENTRY_TO_H:
                break
            if (r["close"] > or_high and r["close"] > vwap.loc[t]
                    and r["rvol_base"] > 0 and (r["volume"] / r["rvol_base"]) >= RVOL_MIN
                    and pd.notna(r["atr"]) and r["atr"] > 0):
                entry = float(r["close"])
                stop = entry - STOP_ATR * float(r["atr"])
                after = rows[rows.index > t]
                exit_px, reason = None, "eod"
                for t2, r2 in after.iterrows():
                    if r2["low"] <= stop:
                        exit_px, reason = stop, "stop"
                        break
                    if t2.hour >= SESSION_END_H:
                        exit_px, reason = float(r2["close"]), "eod"
                        break
                if exit_px is None:
                    exit_px = float(after["close"].iloc[-1]) if len(after) else entry
                gross = exit_px / entry - 1.0
                bar_usd = entry * float(r["volume"])
                slip_rt = 2.0 * (cost.trade_cost(ORDER_USD, bar_usd) / ORDER_USD)
                cost_rt = fee_rt + spread_rt + slip_rt
                trades.append({"name": name, "day": str(d), "gross": gross,
                               "cost_rt": cost_rt, "reason": reason})
                entered = True
                break
        _ = entered
    return trades


def pf(nets: np.ndarray) -> float:
    g = nets[nets > 0].sum()
    l = -nets[nets < 0].sum()
    return float(g / l) if l > 0 else (float("inf") if g > 0 else 0.0)


def main() -> None:
    print(backtest_only_notice())
    cache = Cache(ROOT / "data" / "cache")
    # CostModel here models SLIPPAGE ONLY (fees + spread added explicitly below). Use the
    # S3 ADV-proxy form (base half-spread 5bps + 10*%-of-ADV impact), with ADV = the
    # INTRADAY hourly bar $volume (spec 0.2: scale the proxy to intraday liquidity).
    cost = CostModel(taker_pct=0.0, slippage_base_bps=5.0, slippage_impact_coef=10.0)

    btc_daily = cache.read(SOURCE_DAILY, BTC_DAILY, "1DAY")["close"]
    regime = regime_on(btc_daily, REGIME_SHORT, REGIME_LONG)

    all_trades = []
    per_name = {}
    for name, sid in PROBE.items():
        if not cache.has(SOURCE_INTRADAY, sid, PERIOD):
            print(f"  !! missing intraday cache for {name} ({sid}) — run scripts/s4_ingest_intraday.py")
            return
        df = cache.read(SOURCE_INTRADAY, sid, PERIOD)
        tr = simulate(name, df, regime, cost)
        per_name[name] = tr
        all_trades.extend(tr)

    years = (btc_daily.index.max() - btc_daily.index.min()).days / 365.25
    span_days = (max(t["day"] for t in all_trades) if all_trades else "-",
                 min(t["day"] for t in all_trades) if all_trades else "-")

    print(f"\n===== S4 PHASE 0 — ORB cost-viability (probe BTC/ETH/SOL, hourly) =====")
    print(f"regime-on days only · OR=first {OR_HOURS}h · RVOL>={RVOL_MIN} · stop {STOP_ATR}xATR · "
          f"exit EOD/stop\n")
    print(f"  {'name':>5} {'trades':>7} {'tr/yr':>6} {'win%':>6} {'mean_gross':>11} "
          f"{'cost_rt':>8} {'mean_net':>9} {'netPF':>6} {'netPF_2x':>9}")

    def block(name, trades):
        if not trades:
            print(f"  {name:>5} {'0':>7} — no signals")
            return None
        gross = np.array([t["gross"] for t in trades])
        crt = np.array([t["cost_rt"] for t in trades])
        net = gross - crt
        net2x = gross - 2.0 * crt
        n = len(trades)
        intraday_years = years  # probe spans ~the daily window
        row = dict(n=n, tr_yr=n / max(intraday_years, 1e-9), win=float((gross > 0).mean()),
                   mean_gross=float(gross.mean()), cost_rt=float(crt.mean()),
                   mean_net=float(net.mean()), pf=pf(net), pf2x=pf(net2x),
                   breakeven=float(crt.mean()))
        print(f"  {name:>5} {n:>7} {row['tr_yr']:>6.0f} {row['win']*100:>5.0f}% "
              f"{row['mean_gross']*100:>10.3f}% {row['cost_rt']*100:>7.3f}% "
              f"{row['mean_net']*100:>8.3f}% {row['pf']:>6.2f} {row['pf2x']:>9.2f}")
        return row

    for name in PROBE:
        block(name, per_name[name])
    pooled = block("POOL", all_trades)

    print("\n----- Gate-0 reasoning -----")
    if pooled:
        be = pooled["breakeven"] * 100
        mg = pooled["mean_gross"] * 100
        print(f"  break-even gross edge required per trade (base cost): {be:.3f}%")
        print(f"  mean gross capture actually in the data:               {mg:.3f}%")
        print(f"  -> headroom (mean_gross - cost): {mg - be:+.3f}%  | net PF base {pooled['pf']:.2f}, 2x {pooled['pf2x']:.2f}")
        headroom = pooled["mean_net"] > 0 and pooled["pf"] > 1.0 and pooled["pf2x"] > 1.0
        verdict = "PROCEED to Phase 1 (headroom exists — NOT proof)" if headroom else \
                  "STOP — S4 cost-infeasible at £2k/Kraken intraday (log in EXPERIMENTS.md)"
        print(f"\n>>> GATE-0: {verdict} <<<")


if __name__ == "__main__":
    main()
