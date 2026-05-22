# CTS — Phase 1 Backtest Harness

A **go/no-go gate**, not a trading bot. Phase 1 answers one question honestly:

> Does a daily Donchian/Turtle momentum edge survive **survivorship-clean, after-fee,
> walk-forward, out-of-sample** testing on a Kraken-tradable spot crypto universe?

A clean "no" is a successful outcome — it stops the project cheaply before any
infrastructure is built. See [`PLAN.md`](PLAN.md) for the design and
[`FINDINGS.md`](FINDINGS.md) (produced after the run) for the verdict.

## Hard rules baked into this repo
- **Backtest only.** No live-order / paper / execution code. No Kraken trading endpoints.
- **No LLM in the backtest path.** Every signal, score, size, exit, metric is deterministic.
- **Secrets in `.env`** (git-ignored). Phase 1 needs only a data-vendor key, **no Kraken key**.
  Any Kraken key with trade/withdraw scope is refused by the code.
- **Independent of GTS** — shares no code, repo, DB, or infra.
- **UTC throughout**, daily candles anchored 00:00 UTC.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .            # so `python scripts/...` can import cts
cp .env.example .env        # then add COINAPI_KEY
pytest                      # run the unit tests (no key needed)
```

## Run (needs COINAPI_KEY)
```bash
python scripts/build_universe.py   # point-in-time Kraken universe + exclusion log
python scripts/ingest.py           # cache daily OHLCV locally (reproducible)
python scripts/run_backtest.py     # walk-forward OOS run -> writes FINDINGS.md
```

## Layout
`src/cts/data` data adapters + cache + universe · `src/cts/strategy` deterministic
signal/regime/ranking/sizing/exit functions · `src/cts/engine` fees, slippage,
portfolio, daily loop, walk-forward · `src/cts/metrics` performance, regime
decomposition, robustness, benchmark · `tests/` unit tests with hand-computed fixtures.
