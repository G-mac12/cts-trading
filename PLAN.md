# CTS Phase 1 — Backtest Harness Plan

**Status:** Draft for approval. **Nothing has been built yet** (per spec §14 / Step 0: "prove the edge before building the machine"). This document is the planning deliverable. It also flags two places where real-world data coverage differs from the spec's literal assumptions — which is why I'm surfacing it before writing code.

**The one question Phase 1 answers:** does a daily Donchian/Turtle momentum edge survive *survivorship-clean, after-fee, walk-forward, out-of-sample* testing on a Kraken-tradable spot universe? A clean "no" is a successful outcome — it kills the project cheaply.

---

## 0. Hard constraints carried into the build

- **GTS isolation:** new standalone repo (`G-mac12/cts-trading`). No read/write/import of anything GTS (repo, Supabase, droplets). Verified: this directory shares nothing with GTS.
- **Backtest only.** No live-order, paper, or execution code. No Kraken *trading* endpoints. Market-data / historical reads only.
- **Key safety.** `.gitignore` is committed as the *first* file, before any secret exists. Secrets live in `.env` (git-ignored), loaded at runtime. `.env.example` (committed) documents the variable names only.
- **No Kraken trade/withdraw key.** If a Kraken key with TRADE or WITHDRAW permission is provided, I refuse it and stop. **Note:** Phase 1 most likely needs *no Kraken key at all* — the backtest data comes from a data vendor (CoinAPI / CryptoCompare), not Kraken's API. See §1.
- **No LLM in the backtest path.** Every signal, score, size, exit, and metric is deterministic Python. Zero inference anywhere in the strategy/backtest code.
- **UTC throughout.** Daily candles anchored 00:00 UTC.

---

## 1. Data coverage reality check (READ THIS — it changes a spec assumption)

The validity of the entire gate rests on the data being **survivorship-clean**. I researched the two sources the spec names. Two findings matter:

### Finding A — "survivorship-clean" splits into two different problems
1. **Coin survivorship** — coins that died entirely (LUNA, FTT, many alts). ~58% of all listed tokens since 2013 are now "dead." Omitting them inflates backtested returns by an estimated 200–400%.
2. **Exchange-listing survivorship** — coins/pairs that *Kraken specifically delisted* (incl. UK-FCA-driven delistings 2023–2024) but that still trade elsewhere. The faithful question is "what could a UK personal Kraken account have actually traded on date T," which is stricter than "what coins existed on date T."

A backtest can be clean on (1) and still biased on (2).

| Source | Coin survivorship (dead coins) | Kraken point-in-time listing incl. delisted pairs | Cost for a hobby project |
|---|---|---|---|
| **CoinAPI** | Yes | **Yes** — `/v1/symbols/{exchange}/history` enumerates every symbol ever on KRAKEN incl. delisted, each with `data_start`/`data_end`. This is the only source that cleanly reconstructs (2). | No recurring free tier; one-time **$25** signup credit (card required), then metered. Full multi-year ingest of ~50–200 symbols may need a small paid top-up. |
| **CryptoCompare / CoinDesk** | Yes (aggregate CCCAGG includes dead coins) | **Partial / uncertain** — strong aggregate coverage, but no documented per-exchange "delisted-symbol history with end-date" enumeration. Reconstructing Kraken's *listing timeline* (incl. pairs Kraken dropped) is murky. | Genuinely free monthly call allowance; cheapest for this scale. |
| **Kraken downloadable OHLCVT CSVs** | No | **No — survivorship-BIASED.** Free, clean daily candles, but only for *currently-listed* pairs; delisted pairs' files are removed. | Free. |

**Recommendation:** use **CoinAPI** as the primary adapter for the gate, because it is the only one that reconstructs the point-in-time Kraken universe *including delisted pairs* with explicit end-dates — exactly what §9 demands. Build the adapter pluggable so CryptoCompare / Kraken-CSV can be swapped in for cross-checks. If you'd rather avoid CoinAPI's cost, we *can* run on CryptoCompare or Kraken-CSV, but then **FINDINGS.md will mark the result PROVISIONAL on survivorship** and say so loudly.

**Even CoinAPI has a residual gap:** no generic vendor encodes *UK-specific* Kraken availability. So "tradable on Kraken (global)" is achievable; "tradable on Kraken *by a UK retail user*" is an approximation. This will be stated as an explicit assumption in FINDINGS.md.

### Finding B — the spec's "tick/second-level only" (§9) conflicts with a daily strategy
The strategy (§3) is a **daily** Donchian breakout on candles anchored 00:00 UTC. Daily entries/exits are decided on daily closes. **Daily OHLCV is the correct and sufficient resolution** for this gate; tick data for the whole universe over years is enormous, costly, and adds nothing to a daily-close breakout. Task A itself specifies "daily OHLCV."

**Plan:** Phase 1 backtests on **daily candles**. The "tick-level" requirement properly belongs to the Phase 3 *paper-fill realism* layer (modelling intrabar slippage/partial fills), not the daily backtest. This is the coverage difference that triggers "show PLAN before building." Flagging it; proceeding on daily unless you object.

**Intrabar stop ambiguity (honest caveat):** with daily candles we can't see whether the 2×ATR stop or the day's high was hit first within a bar. Convention used: **stops checked against the daily low; if both a new entry trigger and a stop would fire same-day, the stop wins (conservative).** Documented, not hidden.

---

## 2. Module structure

```
cts-trading/
  .gitignore                 # committed FIRST
  .env.example               # variable names only, committed
  README.md
  PLAN.md  FINDINGS.md
  pyproject.toml
  config/
    universe.yml             # §4 eligibility thresholds
    backtest.yml             # fees, slippage, equity, fold sizes, params
  src/cts/
    config.py                # load yaml + .env
    data/
      adapter.py             # abstract DataAdapter (survivorship-aware interface)
      coinapi.py             # CoinAPI implementation (primary)
      cryptocompare.py       # CryptoCompare/CoinDesk implementation
      kraken_csv.py          # Kraken flat-file loader (biased; cross-check only)
      cache.py               # local parquet cache + manifest (reproducibility)
      universe.py            # §4 filters + point-in-time universe + exclusion log
    indicators.py            # donchian, atr, rvol, ma, returns  (pure)
    strategy/
      regime.py              # BTC regime filter (§3.3)
      ranking.py             # cross-sectional 30d momentum, 7d rebalance (§3.2)
      signals.py             # entry rule (break + RVOL + regime + xs gate)
      sizing.py              # ATR sizing, 1% risk, 2×ATR stop (§3.1)
      exits.py               # 10/20-day low exit OR stop (§3.1)
    engine/
      fees.py                # Kraken Pro taker/maker model (§3.5)
      slippage.py            # configurable conservative slippage
      portfolio.py           # cash, positions, constraints (5 max, 50% deployed)
      backtest.py            # event-driven daily loop
      walkforward.py         # fold generation, IS/OOS orchestration
    metrics/
      performance.py         # PF, return, CAGR, maxDD, Sharpe, win rate, payoff, count
      regime_decomp.py       # bull/bear/chop attribution
      robustness.py          # subsample seeds + param-neighbourhood distribution
      benchmark.py           # buy & hold BTC
    reporting/findings.py    # assemble FINDINGS.md from results
  tests/
    fixtures/                # hand-computed CSVs
    test_indicators.py  test_signals.py  test_sizing.py
    test_exits.py  test_regime.py  test_ranking.py  test_fees.py
    test_walkforward.py  test_engine_smoke.py
  scripts/
    build_universe.py        # construct point-in-time universe + exclusion log
    ingest.py                # pull + cache OHLCV
    run_backtest.py          # run walk-forward, emit metrics + FINDINGS.md
```

Language: **Python 3.11+**, pandas/numpy, pyarrow (parquet cache), pyyaml, requests, pytest. No heavy backtest framework — a transparent ~few-hundred-line event loop is more auditable for a gate whose whole purpose is trust.

---

## 3. Data adapter design

Abstract interface — the survivorship contract is enforced at the type level:

```python
@dataclass
class SymbolMeta:
    symbol_id: str          # vendor symbol
    base: str; quote: str   # e.g. ETH / USD
    exchange: str           # "KRAKEN"
    data_start: date
    data_end: date | None   # None = still active; a date = DELISTED then
    is_active: bool

class DataAdapter(ABC):
    def list_kraken_symbols(self) -> list[SymbolMeta]: ...
        # MUST include delisted symbols. If the source cannot, the adapter
        # raises SurvivorshipNotGuaranteed and the run is tagged PROVISIONAL.
    def daily_ohlcv(self, symbol: str, start: date, end: date) -> DataFrame: ...
        # UTC, 00:00-anchored OHLCV+volume, through the delist date.
```

- **Caching:** content-addressed parquet keyed by `(source, symbol, granularity)`; a `manifest.json` records source, pull timestamp, symbol count, and per-symbol date ranges. **Backtests read only from cache** → fully reproducible; re-running never silently changes inputs.
- **Universe log:** every rebalance writes included symbols *and* every excluded symbol with a reason code (`vol<50M`, `age<90d`, `stablecoin`, `wrapped`, `leveraged`, `quote≠USD/USDT`, `delisted-before-date`). This log is an explicit FINDINGS.md exhibit.

---

## 4. Eligibility filters (§4) — applied point-in-time, no lookahead

At each 7-day rebalance, using only data available *up to that date*:
- 24h USD volume ≥ **$50M** (rolling, trailing).
- ≥ **90 days** of clean history.
- Quote in **USD/USDT**.
- Exclude **stablecoins, wrapped, leveraged/ETP tokens** (maintained denylist + symbol heuristics, e.g. `*UP/*DOWN/*BULL/*BEAR`, `w*`/`*.b` wrapped patterns, USD-pegged list).
- Spread ≤ 0.3% **where available** (daily candle feeds usually lack reliable spread; if absent, this filter is logged as "not enforced — data unavailable," not silently skipped).
- Universe cap: top ~30–50 by eligibility.

**No-lookahead discipline is a first-class test target** — fixtures assert that a symbol's data after a rebalance date never influences that date's decisions.

---

## 5. Strategy logic (deterministic, §3) — pure functions, each unit-tested

- **Donchian entry:** close > prior N-day high. **System 1 N=20** and **System 2 N=55** run in parallel.
- **RVOL gate:** breakout-bar volume ≥ 1.5 × trailing 20-bar average.
- **Cross-sectional gate:** 30-day return rank, 7-day rebalance, top-tier only.
- **Regime master switch:** BTC > 100d MA **AND** 50d MA > 100d MA → risk-on. Risk-off = no new entries; open positions still managed by their exits; idle = cash.
- **ATR(14) sizing:** `units = (equity × 1%) / (2×ATR stop distance)`.
- **Stop:** 2×ATR below entry (volatility-scaled, not cash-fixed).
- **Exit:** close < 10-day low (S1) / 20-day low (S2), OR stop, whichever first. No pyramiding.
- **Portfolio:** ≤ 5 concurrent positions, ≤ 50% deployed, idle in cash (zero return).

**Starting parameters are run AS GIVEN first.** That headline OOS result is reported before any tuning. Each function gets hand-computed fixtures (e.g. a 25-bar series with a known Donchian break on a known day, a known ATR, a known stop level).

---

## 6. Backtest engine (§9)

- **Event-driven daily loop** over the survivorship-clean universe. Order each day: update indicators → check regime → manage exits on open positions → rank → check entries → apply portfolio constraints → mark-to-market equity.
- **Fees (§3.5):** entry = Kraken Pro **taker 0.40%** (breakouts cross the band). Exit = taker 0.40% by default; maker 0.25% modelled **only** for Donchian exits explicitly treated as resting limit orders — and reported as a separate, clearly-labelled variant so a maker assumption never flatters the headline. Round-trip ≈ 0.8% taker.
- **Slippage:** explicit, conservative, configurable. Default **0.15%/side**; sensitivity reported at 0.05% / 0.15% / 0.30%.
- **Equity:** start **£2,000**, converted to USD at a fixed, stated rate (simulation parameter; no FX path-dependence, no real money).

---

## 7. Walk-forward scheme (anti-overfitting — the core of the gate)

- **Rolling-origin walk-forward**, non-overlapping OOS so each OOS day is scored exactly once.
- Default: **IS = 18 months, OOS = 6 months, step = 6 months**, rolling (fixed-length IS). Adjustable once we see how much clean history exists per symbol; majors likely 2017/18→2026, many alts shorter.
- **Pass 1 (headline):** spec's starting parameters applied unchanged to every OOS fold. No tuning. This is *the* result.
- **Pass 2 (if tuning at all):** grid on the IS fold only → freeze → apply to the *next* OOS fold. Report the per-fold chosen parameters (instability across folds = overfit signal) and the stitched OOS curve.
- **Parameter-neighbourhood sweep reported as a DISTRIBUTION**, never the peak. A strategy that only works at one exact point is reported as overfit.
- **Statistical-power caveat up front:** the regime filter turns the system off in bear/chop, so OOS *trade count* may be small. Trade count is reported prominently; thin samples are called out as low-confidence rather than dressed up.

---

## 8. Metrics reported (OOS, after fees) — exactly this list

Per system (S1, S2) and combined:
- Profit factor, total return %, CAGR, max drawdown %, **Sharpe** (daily, annualised √365, rf=0), Sortino, win rate, avg-win/avg-loss (payoff), expectancy/trade, **trade count** (total + per fold), exposure % (time in market), avg concurrent positions.
- **Regime decomposition (pass/fail criterion):** PF / return / maxDD / exposure split into **bull / bear / chop**, where regime is classified independently from BTC's MA structure. The system must demonstrably go to cash and *preserve capital* in bear/chop, not merely profit in bull.
- **Robustness:** (a) universe subsampling — random 2/3, multiple seeds → distribution of PF/return/maxDD; (b) parameter-neighbourhood sweep → distribution.
- **Benchmark:** buy-&-hold BTC over identical OOS windows (return, maxDD, Sharpe) + strategy excess.

## 9. Acceptance bar (§9) — reported explicitly, pass or fail
PF > 1.5 after Pro fees · max DD < 25% · positive OOS Sharpe · capital-preserving bear/chop. FINDINGS.md states: (a) do the **starting** parameters clear it, and (b) does *anything* clear it only under suspiciously narrow tuning (= fail). Then an explicit **GO / NO-GO** for Phase 2 with reasoning.

## 10. Build order (after approval)
1. `git init` + **.gitignore** + `.env.example` + repo scaffold (no secrets).
2. Indicators + strategy pure functions **+ their unit tests** (no data dependency — can be done before any key).
3. Data adapter + cache + universe builder; ingest via the chosen source.
4. Engine (fees, slippage, portfolio, daily loop) + walk-forward + smoke test.
5. Metrics + robustness + benchmark.
6. Run; write **FINDINGS.md** honestly.

## 11. Decisions needed from you before I build
1. **Data source** (drives survivorship validity + cost) — see §1 recommendation (CoinAPI).
2. **Provide the relevant data-vendor API key** when ready (read-only by nature). Phase 1 likely needs **no Kraken key**; if you do supply one, it must be read-only/market-data (I refuse trade/withdraw).
3. **OK to backtest on daily candles** (not tick) for Phase 1 — see Finding B.
