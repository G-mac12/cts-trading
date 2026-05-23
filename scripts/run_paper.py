#!/usr/bin/env python
"""Lean local paper-trader. SIMULATED ONLY — no real orders.

  python scripts/run_paper.py            # run on current cached data
  python scripts/run_paper.py --update   # pull new daily candles first, then run

Run it daily (manually or via cron) to grow the forward track record.
"""
from __future__ import annotations

import argparse
from datetime import date

from cts.config import ROOT
from cts.data.cache import Cache
from cts.paper.report import render_paper
from cts.paper.runner import PAPER_DIR, run_paper
from cts.pipeline import update_cache
from cts.safety import backtest_only_notice


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="incrementally pull new candles before running")
    ap.add_argument("--as-of", default=None, help="evaluate as of this YYYY-MM-DD (default: latest candle)")
    args = ap.parse_args()

    print(backtest_only_notice())
    if args.update:
        from cts.pipeline import get_coinapi_adapter
        n = update_cache(get_coinapi_adapter(), Cache(ROOT / "data" / "cache"), "coinapi", date.today())
        print(f"Updated {n} active symbols with fresh candles.")

    report = run_paper(as_of=args.as_of)
    md = render_paper(report)
    (PAPER_DIR / "PAPER_STATUS.md").write_text(md)
    print("\n" + md)
    print(f"\nWrote {PAPER_DIR / 'PAPER_STATUS.md'}, paper_snapshot.json, paper_runs.csv")


if __name__ == "__main__":
    main()
