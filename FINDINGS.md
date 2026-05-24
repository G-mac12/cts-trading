# CTS Phase 1 — FINDINGS

_Generated 2026-05-24T19:45:02.626366+00:00 · data source: coinapi · window 2018-04-01 → 2026-05-23_

## VERDICT: **NO-GO** for Phase 2

> **The verdict is CONDITIONAL — read this with the drawdown gate.** _(Manual addendum,
> 2026-05-24; every table below is the generator's, unedited. A bare re-run of
> `scripts/run_backtest.py` reprints only the bare mechanical verdict and drops this block.)_
>
> - **Mechanical output, stated plainly:** at the live **0.6% risk** sizing, max drawdown
>   **−25.6%** fails the §9 `< 25%` gate **by 0.6pp → mechanical NO-GO.** (Profit factor 2.23
>   and Sharpe 0.71 both pass; drawdown is the **sole** failing sub-metric, and the edge
>   survives subsampling — median PF 1.99 — and the parameter neighbourhood — median 2.37.)
> - **The dependency (not an excuse):** the §9 drawdown gate is **sizing-dependent**, and
>   per-position risk is **edge-neutral** — the audit shows PF/Sharpe ~flat across 0.4–1.0%
>   while only return & drawdown scale (`S1_ROBUSTNESS.md` §5). So the verdict is
>   **CONDITIONAL on the still-parked decision (b):**
>     - at **0.6% risk** → DD **−25.6%** → **fails** by 0.6pp (this run);
>     - at **0.4% risk** → DD **≈−19%** → **passes** (return ≈+72% vs +117%).
>     - **Same edge, different dial.**
> - **(b) is NOT resolved here to rescue the verdict.** It is decided cold, separately, on
>   its own terms — never to flip a gate. Until then the verdict stays **explicitly
>   conditional** and S1 continues at 0.6%.
> - **This is not "the gate is wrong."** The gate is respected; its output simply **depends
>   on an input not yet set.**
>
> **Why these numbers differ from the earlier 2.56 / −20.5%:** re-baselined to the
> **complete 341-coin cache**. The earlier 157-coin ingest had missed ~36 legitimately
> ≥$1M-eligible names (2023–25 alts: ARB, ONDO, TIA, SUI, ENA, AERO…) that S1 *would* have
> traded live; including them (most stopped out in 2024–25 chop) makes the honest numbers
> **softer**. This corrects a measurement — it does not change the system. Full resolution:
> `S1_ROBUSTNESS.md` §5b.

> ✅ Data adapter reports survivorship-clean coverage (delisted symbols included).

### Does the edge survive — plain answer

On out-of-sample, after-fee data, the starting parameters **did not clear the §9 headline bar** (profit factor / drawdown / Sharpe). NO-GO. Per system:
- **S1**: headline PF/DD/Sharpe FAIL; 129 trades (adequately powered); subsample median PF 1.99 (survives subsampling); **chop give-back -26.2%** over chop days, though only 21.4% exposed (it does sit in cash).

- **S1** OOS fold spread: 12 of 14 folds traded, 5 profitable (check the per-fold table for concentration).

Per the spec, a clean **NO-GO here is a successful Phase-1 outcome** — it stops the project cheaply before any machine is built.

### Universe & assumptions

- Symbols actually traded: **341** · BTC (regime): `KRAKEN_SPOT_BTC_USD` · rebalances: 425.
- Fees: Kraken Pro **taker on entry**; exits taker by default (maker only where a resting limit genuinely earns it). Round-trip ≈ 0.8% before slippage.
- Slippage: explicit per-side assumption (see config); stress band reported via neighbourhood.
- Execution: signals on daily close; entries/Donchian-exits at NEXT open; stops intrabar (stop wins ties). Daily candles (Phase 1 resolution).
- Equity: £2,000 simulation balance converted to USD at a fixed rate (no real money).
- max_spread filter NOT enforced: daily OHLCV feeds carry no reliable spread data.
- Residual gap (any source): no vendor encodes UK-specific Kraken availability, so the universe is 'Kraken global' as a proxy for what a UK account could trade.

## Per-system results

### System S1 — Donchian entry N=20, exit N=10

**Headline (starting parameters, out-of-sample, after fees)**

| Metric | Value | Bar | Pass |
|---|---|---|---|
| Profit factor | 2.23 | > 1.5 | ✅ |
| Max drawdown | -25.6% | > -25% | ❌ |
| Sharpe | 0.71 | > 0 | ✅ |
| Total return | 116.6% | — | |
| CAGR | 9.9% | — | |
| Win rate | 34.1% | — | |
| Avg win / avg loss | 4.31 | — | |
| Expectancy / trade (USD) | 22.95 | — | |
| Trade count | 129 | >= 30 | ✅ |
| Exposure (time in market) | 37.4% | — | |

**Benchmark — buy & hold BTC (same window):** return 1008.0%, max DD -76.7%, Sharpe 0.79.

**Regime decomposition** (must preserve capital + stay in cash during bear/chop):

| Regime | % of period | Return | Max DD | Exposure | Trades | Trade P&L |
|---|---|---|---|---|---|---|
| bull | 43.4% | 197.9% | -14.1% | 75.7% | 126 | 3057.27 |
| bear | 38.4% | -1.5% | -1.5% | 1.7% | 0 | 0.00 |
| chop | 18.3% | -26.2% | -26.3% | 21.4% | 3 | -96.33 |

Bear behaviour ✅ controlled; chop behaviour ❌ NOT controlled.

**Robustness — profit factor distribution** (a real edge survives off the exact peak):

| Source | Median | Mean | Min | P25 | P75 | Max |
|---|---|---|---|---|---|---|
| Universe subsample (2/3, 3 seeds) | 1.99 | 1.93 | 1.81 | 1.90 | 1.99 | 1.99 |
| Parameter neighbourhood (6 sets) | 2.37 | 2.37 | 2.08 | 2.25 | 2.49 | 2.67 |

**Tuned walk-forward (tune on IS, apply OOS):** PF 2.55, return 101.1%, max DD -22.4%, Sharpe 0.82, trades 116.
Per-fold chosen params (instability = overfit signal): f0:N=15/stop=2.0, f1:N=15/stop=2.0, f2:N=15/stop=2.5, f3:N=15/stop=2.0, f4:N=15/stop=2.5, f5:N=25/stop=2.5, f6:N=25/stop=2.5, f7:N=20/stop=2.5, f8:N=15/stop=2.5, f9:N=25/stop=2.5, f10:N=25/stop=2.5, f11:N=25/stop=2.5, f12:N=25/stop=2.5, f13:N=25/stop=2.5

**Per-fold OOS stability (headline params):**

| Fold | OOS window | PF | Return | Max DD | Trades |
|---|---|---|---|---|---|
| 0 | 2019-10-01→2020-04-01 | 0.00 | -0.2% | -1.6% | 1 |
| 1 | 2020-04-01→2020-10-01 | 1.34 | 1.0% | -8.2% | 7 |
| 2 | 2020-10-01→2021-04-01 | 128.00 | 96.0% | -14.1% | 5 |
| 3 | 2021-04-01→2021-10-01 | 0.12 | -8.6% | -17.3% | 15 |
| 4 | 2021-10-01→2022-04-01 | 0.09 | -5.1% | -8.2% | 14 |
| 5 | 2022-04-01→2022-10-01 | 0.00 | 0.0% | 0.0% | 0 |
| 6 | 2022-10-01→2023-04-01 | 0.40 | -1.6% | -4.2% | 10 |
| 7 | 2023-04-01→2023-10-01 | 0.00 | -4.1% | -6.5% | 5 |
| 8 | 2023-10-01→2024-04-01 | 2.32 | 22.0% | -13.8% | 27 |
| 9 | 2024-04-01→2024-10-01 | 0.62 | -5.8% | -6.0% | 7 |
| 10 | 2024-10-01→2025-04-01 | 3.92 | 10.4% | -9.0% | 10 |
| 11 | 2025-04-01→2025-10-01 | 1.79 | 3.9% | -9.8% | 17 |
| 12 | 2025-10-01→2026-04-01 | 0.00 | -0.9% | -1.0% | 0 |
| 13 | 2026-04-01→2026-05-23 | 0.00 | -3.1% | -3.1% | 5 |


## Recommendation & reasoning

**NO-GO.** Do not build Phase 2+ infrastructure on this edge as specified. 
Reasons: headline PF/DD/Sharpe do not clear the bar. A single PRE-REGISTERED revisit (decide the change before looking at results) is defensible; if it is also flat/fragile OOS, stop for good.

_Anti-overfitting note: the headline uses the spec's starting parameters unchanged. Tuned walk-forward and parameter-neighbourhood results are reported as distributions, not peaks; any result that appears only under tuning is treated as a fail._
