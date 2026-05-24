#!/usr/bin/env python
"""S4 Phase-0 intraday ingest — BTC/ETH/SOL hourly, isolated from S1's daily cache.

Writes to a SEPARATE cache source dir (`data/cache/coinapi_intraday/`) with a `1HRS`
granularity suffix, so it cannot touch what S1 reads (`data/cache/coinapi/*__1DAY`).
Resume-safe: a symbol already cached is not re-fetched (no double credit spend).

Approved scope: BTC/ETH/SOL · 1HRS · 2022-01-01 → 2026-05-24 (~1,160 credits est.).
Read-only market data; no Kraken/trading endpoints.
"""
from __future__ import annotations

from datetime import date

from cts.config import ROOT, get_secret
from cts.data.cache import Cache
from cts.data.coinapi import CoinAPIAdapter
from cts.safety import backtest_only_notice

SOURCE = "coinapi_intraday"
PERIOD = "1HRS"
START = date(2022, 1, 1)
END = date(2026, 5, 24)
PROBE = ["KRAKEN_SPOT_BTC_USD", "KRAKEN_SPOT_ETH_USD", "KRAKEN_SPOT_SOL_USD"]


def main() -> None:
    print(backtest_only_notice())
    cache = Cache(ROOT / "data" / "cache")
    adapter = CoinAPIAdapter(get_secret("COINAPI_KEY"), exchange="KRAKEN")

    summary = []
    for sid in PROBE:
        if cache.has(SOURCE, sid, PERIOD):
            df = cache.read(SOURCE, sid, PERIOD)
            print(f"  [cached] {sid:24} bars={len(df)}  (skipped — no spend)")
            summary.append({"symbol_id": sid, "bars": len(df), "cached": True})
            continue
        before = adapter.total_request_cost
        df = adapter.intraday_ohlcv(sid, START, END, PERIOD)
        spent = adapter.total_request_cost - before
        if df.empty:
            print(f"  [EMPTY]  {sid:24} — no data returned")
            summary.append({"symbol_id": sid, "bars": 0, "credits": spent})
            continue
        cache.write(SOURCE, sid, df, PERIOD)
        print(f"  [pulled] {sid:24} bars={len(df):6}  credits={spent:4}  "
              f"[{df.index.min()} .. {df.index.max()}]")
        summary.append({"symbol_id": sid, "bars": len(df), "credits": spent,
                        "start": str(df.index.min()), "end": str(df.index.max())})

    cache.write_manifest(SOURCE, {
        "source": SOURCE, "period_id": PERIOD, "survivorship_clean": True,
        "exchange": "KRAKEN", "range": [START, END], "probe_set": PROBE,
        "request_cost_credits": adapter.total_request_cost, "symbols": summary,
        "note": "S4 Phase-0 intraday probe; isolated from S1 daily cache (coinapi/*__1DAY).",
    })
    print(f"\nTotal credits spent this run: {adapter.total_request_cost}")
    print(f"Wrote cache + manifest under data/cache/{SOURCE}/")


if __name__ == "__main__":
    main()
