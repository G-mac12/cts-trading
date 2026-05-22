#!/usr/bin/env python
"""Build the point-in-time universe from cached data and write the exclusion log
(who was in/out each rebalance and why). Diagnostic; run_backtest builds its own
schedule too.

  python scripts/build_universe.py
"""
from __future__ import annotations

from cts.config import ROOT, backtest_config, universe_config
from cts.data.cache import Cache
from cts.data.universe import build_schedule
from cts.pipeline import load_cached, make_rebalance_dates


def main() -> None:
    cache = Cache(ROOT / "data" / "cache")
    panel, metas, manifest = load_cached(cache, manifest_source())
    cfg_u, cfg_s = universe_config(), backtest_config()["strategy"]
    rebalance_dates = make_rebalance_dates(panel, cfg_u, cfg_s)
    sched = build_schedule(panel, metas, cfg_u, cfg_s, rebalance_dates)

    out = ROOT / "data" / "universe_log.csv"
    sched.log.to_csv(out, index=False)
    n_incl = (sched.log["status"] == "included").sum()
    n_excl = (sched.log["status"] == "excluded").sum()
    print(f"Rebalances: {len(rebalance_dates)} | log rows: {len(sched.log)} "
          f"(included {n_incl}, excluded {n_excl})")
    print("Exclusion reasons:")
    print(sched.log[sched.log["status"] == "excluded"]["reason"].value_counts().to_string())
    for note in sched.notes:
        print(f"NOTE: {note}")
    print(f"Wrote {out}")


def manifest_source() -> str:
    # default source name used by the CoinAPI adapter
    return "coinapi"


if __name__ == "__main__":
    main()
