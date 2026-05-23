#!/usr/bin/env python
"""Ingest survivorship-clean daily OHLCV for the Kraken universe into the local
cache. Read-only market data. Needs COINAPI_KEY in .env.

  python scripts/ingest.py --start 2017-01-01 --end 2026-05-22
"""
from __future__ import annotations

import argparse
from datetime import date, datetime

from cts.config import ROOT
from cts.data.cache import Cache
from cts.pipeline import get_coinapi_adapter, ingest
from cts.safety import backtest_only_notice


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=_d, default=_d("2018-01-01"))
    ap.add_argument("--end", type=_d, default=date.today())
    ap.add_argument("--max-symbols", type=int, default=None,
                    help="cap symbols pulled (saves CoinAPI credits while testing)")
    ap.add_argument("--min-volume", type=float, default=0.0,
                    help="optional absolute USD volume floor for ACTIVE coins (delisted always kept)")
    ap.add_argument("--top-n", type=int, default=120,
                    help="ingest the top-N active coins by volume RANK (robust to time-of-day)")
    ap.add_argument("--refresh", action="store_true",
                    help="re-pull even if cached (default: resume from cache, no re-spend)")
    args = ap.parse_args()

    print(backtest_only_notice())
    adapter = get_coinapi_adapter()
    cache = Cache(ROOT / "data" / "cache")
    print(f"Ingesting {adapter.source_name} {args.start}..{args.end} "
          f"(survivorship_clean={adapter.survivorship_clean}, active_top_n={args.top_n})")
    panel, metas = ingest(adapter, cache, args.start, args.end, max_symbols=args.max_symbols,
                          min_recent_volume_usd=args.min_volume, active_top_n=args.top_n, refresh=args.refresh)
    n_delisted = sum(1 for m in metas.values() if not m.is_active)
    print(f"Pulled {len(panel)} symbols ({n_delisted} delisted) into {cache.root}.")
    print(f"CoinAPI credits spent this run: {getattr(adapter, 'total_request_cost', 'n/a')}")
    if panel:
        spans = [(s, df.index.min().date(), df.index.max().date(), len(df)) for s, df in list(panel.items())[:12]]
        for s, a, b, n in spans:
            print(f"  {s}: {a}..{b} ({n} bars)")
        if len(panel) > 12:
            print(f"  ... and {len(panel) - 12} more")


if __name__ == "__main__":
    main()
