#!/usr/bin/env python
"""S3 step B — point-in-time universe scan (CHECKPOINT, read-only, no trading).

Answers Q3/Q4: how many Kraken USD/USDT spot names clear a RANGE of liquidity floors
at several point-in-time dates (survivorship-aware), plus a first-pass segment
breakdown. £200 (~$254) order is shown as a fraction of each floor's ADV.

Does NOT set the floor or touch S1 — it produces the table to decide from.
"""
from __future__ import annotations

import pandas as pd

import yaml

from cts.config import CONFIG_DIR, ROOT, backtest_config
from cts.data.cache import Cache
from cts.pipeline import load_cached

_SEG_CFG = yaml.safe_load((CONFIG_DIR / "s3_segments.yml").read_text())
SEGMENTS = _SEG_CFG["segments"]
BASE_TO_SEG = {b.upper(): seg for seg, bs in SEGMENTS.items() for b in bs}
EXCLUDE = {b.upper() for b in _SEG_CFG.get("exclude", [])}

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
            if metas[s].base.upper() in EXCLUDE:        # fiat/stable/commodity — not S3 universe
                continue
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

    # segment breakdown at the $1M floor (latest)
    names = latest_by_floor[1e6]
    seg_counts: dict = {}
    for s in names:
        seg = BASE_TO_SEG.get(metas[s].base.upper(), "other")
        seg_counts[seg] = seg_counts.get(seg, 0) + 1
    print(f"Segment breakdown at $1M floor (latest, {len(names)} names): "
          + ", ".join(f"{k}={v}" for k, v in sorted(seg_counts.items())))

    # union of every base that EVER clears $1M across the snapshots, and which are unclassified
    union_bases = set()
    for d in SNAPSHOTS:
        for s in count_at(d, 1e6):
            union_bases.add(metas[s].base.upper())
    unclassified = sorted(b for b in union_bases if b not in BASE_TO_SEG)
    print(f"\nEligible bases ever clearing $1M across snapshots: {len(union_bases)}")
    print(f"UNCLASSIFIED ({len(unclassified)}, {100*len(unclassified)/max(len(union_bases),1):.0f}%): "
          + (", ".join(unclassified) if unclassified else "none — 100% classified"))


if __name__ == "__main__":
    main()
