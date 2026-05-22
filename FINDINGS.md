# CTS Phase 1 — FINDINGS

> **STATUS: PENDING DATA INGEST.** This file is a placeholder. The harness is
> built and fully unit-tested, but the real verdict cannot be produced until
> survivorship-clean Kraken data is ingested. It is generated automatically by:
>
> ```bash
> cp .env.example .env        # add COINAPI_KEY
> python scripts/ingest.py    # pull survivorship-clean daily OHLCV into the cache
> python scripts/run_backtest.py   # walk-forward OOS run -> overwrites this file
> ```
>
> The generated report will state, in plain language: whether the daily
> Donchian/Turtle momentum edge survives out-of-sample, after-fee, walk-forward
> testing; the headline metrics; the bull/bear/chop regime breakdown; the
> robustness picture (universe subsamples + parameter neighbourhood); every
> assumption (slippage, fee tier, data coverage, survivorship gaps); and an
> explicit **GO / NO-GO** recommendation for Phase 2.
>
> If the data source cannot certify survivorship-cleanliness, the report will
> carry a loud PROVISIONAL banner and treat all numbers as optimistic.

_No backtest has been run yet, so there is no verdict to report._
