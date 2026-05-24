#!/usr/bin/env python
"""S3 step B — point-in-time universe scan (CHECKPOINT, read-only, no trading).

Answers Q3/Q4: how many Kraken USD/USDT spot names clear a RANGE of liquidity floors
at several point-in-time dates (survivorship-aware), plus a first-pass segment
breakdown. £200 (~$254) order is shown as a fraction of each floor's ADV.

Does NOT set the floor or touch S1 — it produces the table to decide from.
"""
from __future__ import annotations

import pandas as pd

from cts.config import ROOT, backtest_config
from cts.data.cache import Cache
from cts.pipeline import load_cached

# First-pass segment map (base asset -> segment). Refine later; unmapped = "other".
SEGMENTS = {
    "majors": ["BTC", "XBT", "ETH"],
    "L1": ["SOL", "ADA", "AVAX", "DOT", "NEAR", "ATOM", "ALGO", "APT", "SUI", "TON", "TRX",
            "FTM", "S", "SEI", "INJ", "TIA", "KAS", "ICP", "EGLD", "HBAR", "XLM", "LTC",
            "BCH", "ETC", "KAVA", "MINA", "FLOW", "EOS", "WAVES", "LUNA", "LUNA2", "ROSE", "CRO"],
    "DeFi": ["UNI", "AAVE", "MKR", "CRV", "COMP", "SNX", "LDO", "SUSHI", "GMX", "DYDX",
              "PENDLE", "JUP", "RUNE", "CAKE", "1INCH", "BAL", "YFI", "ENA", "AERO"],
    "RWA_infra": ["ONDO", "LINK", "FIL", "AR", "RNDR", "RENDER", "GRT", "THETA", "HNT", "AKT",
                   "FET", "TAO", "OCEAN", "IOTX", "ANKR", "STORJ", "QNT", "POL", "MATIC"],
    "privacy": ["XMR", "ZEC", "DASH", "SCRT"],
    "meme": ["DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "USELESS", "BANANAS31", "MEW",
              "POPCAT", "TURBO", "BRETT", "TRUMP", "FARTCOIN", "VVV"],
}
BASE_TO_SEG = {b: seg for seg, bs in SEGMENTS.items() for b in bs}

FLOORS = [0.5e6, 1e6, 2e6, 5e6, 10e6, 25e6, 50e6, 100e6]
SNAPSHOTS = ["2021-11-10", "2022-11-10", "2023-11-10", "2024-12-15", "2025-11-10", "2026-05-23"]
LISTING_AGE_DAYS = 365


def main() -> None:
    cfg_bt = backtest_config()
    gbp_usd = float(cfg_bt["equity"]["gbp_usd_rate"])
    order_usd = 200.0 * gbp_usd  # ~£200 order

    panel, metas, _ = load_cached(Cache(ROOT / "data" / "cache"), "coinapi")
    # 30-day average dollar volume per coin (close * base-volume), as a time series.
    adv = {s: (df["close"] * df["volume"]).rolling(30, min_periods=20).mean() for s, df in panel.items()}

    def count_at(date_str: str, floor: float):
        d = pd.Timestamp(date_str, tz="UTC")
        names = []
        for s, series in adv.items():
            s_upto = series[series.index <= d].dropna()
            if s_upto.empty:
                continue
            # alive + enough listing age at d
            first = panel[s].index.min()
            if (d - first).days < LISTING_AGE_DAYS:
                continue
            if (d - s_upto.index[-1]).days > 10:   # data ended (delisted) before d
                continue
            if s_upto.iloc[-1] >= floor:
                names.append(s)
        return names

    print(f"S3 universe scan — Kraken USD/USDT spot, {len(panel)} coins in cache "
          f"(survivorship-clean incl. delisted)\n")
    print("NAMES CLEARING EACH 30d-ADV FLOOR, POINT-IN-TIME (>=12mo listing age):\n")
    hdr = "floor".ljust(8) + "".join(d[:7].rjust(10) for d in SNAPSHOTS) + "  £200/ADV"
    print(hdr); print("-" * len(hdr))
    latest_by_floor = {}
    for f in FLOORS:
        counts = [len(count_at(d, f)) for d in SNAPSHOTS]
        latest_by_floor[f] = count_at(SNAPSHOTS[-1], f)
        frac = order_usd / f * 100
        print(f"${f/1e6:>5.1f}M".ljust(8) + "".join(str(c).rjust(10) for c in counts)
              + f"   {frac:.3f}%")

    print("\nNOTE: counts at older dates UNDERCOUNT true breadth — the cache is biased to "
          "coins liquid TODAY (+37 delisted). Recent columns are the reliable ones; for honest "
          "historical breadth we'd ingest more names (flag).\n")

    # segment breakdown at two candidate floors, latest date
    for f in (1e6, 5e6):
        names = latest_by_floor[f]
        seg_counts: dict = {}
        for s in names:
            seg = BASE_TO_SEG.get(metas[s].base, "other")
            seg_counts[seg] = seg_counts.get(seg, 0) + 1
        print(f"Segment breakdown at ${f/1e6:.0f}M floor (latest, {len(names)} names): "
              + ", ".join(f"{k}={v}" for k, v in sorted(seg_counts.items())))


if __name__ == "__main__":
    main()
