# CTS Phase 1 — FINDINGS

_Generated 2026-05-22T23:10:08.279750+00:00 · data source: coinapi · window 2018-04-01 → 2026-05-21_

## VERDICT: **NO-GO** for Phase 2

> ✅ Data adapter reports survivorship-clean coverage (delisted symbols included).

### Does the edge survive — plain answer

**Not proven — promising on the surface, but it fails the robustness and statistical-power bar.** On the starting parameters the headline §9 metrics actually look strong (see per-system tables: profit factor, drawdown and Sharpe all pass, and the system correctly sits in cash during bear markets). The verdict is still NO-GO because the result is not trustworthy:
- **S1**: headline PF/DD/Sharpe pass; **only 23 trades in 8y** (underpowered — a PF on ~20 trades is not statistically reliable); **universe-fragile**: subsample median PF 0.99 (drop 1/3 of coins and the edge ≈ breakeven — it rides on a few names); bleeds in chop (positions opened in bull bleed as the regime turns).
- **S2**: headline PF/DD/Sharpe pass; **only 19 trades in 8y** (underpowered — a PF on ~20 trades is not statistically reliable); **universe-fragile**: subsample median PF 0.69 (drop 1/3 of coins and the edge ≈ breakeven — it rides on a few names); bleeds in chop (positions opened in bull bleed as the regime turns).

The per-fold table makes the concentration explicit: almost all of the profit comes from a **single bull window (2020-10 → 2021-04)** on 2 trades; most other folds are flat or slightly negative. That is the classic shape of an edge that is real in one regime but too thin and too concentrated to bet infrastructure on.

Per the spec, a clean **NO-GO here is a successful Phase-1 outcome** — it stops the project cheaply before any machine is built. The signal is interesting enough that ONE revisit could be justified (see reasoning), but not a Phase 2 commitment as specified.

### Universe & assumptions

- Symbols actually traded: **54** · BTC (regime): `KRAKEN_SPOT_BTC_USD` · rebalances: 425.
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
| Profit factor | 4.08 | > 1.5 | ✅ |
| Max drawdown | -15.2% | > -25% | ✅ |
| Sharpe | 0.58 | > 0 | ✅ |
| Total return | 50.2% | — | |
| CAGR | 5.1% | — | |
| Win rate | 39.1% | — | |
| Avg win / avg loss | 6.35 | — | |
| Expectancy / trade (USD) | 55.39 | — | |
| Trade count | 23 | >= 30 | ⚠️ |
| Exposure (time in market) | 22.3% | — | |

**Benchmark — buy & hold BTC (same window):** return 1038.8%, max DD -76.7%, Sharpe 0.79.

**Regime decomposition** (must preserve capital + stay in cash during bear/chop):

| Regime | % of period | Return | Max DD | Exposure | Trades | Trade P&L |
|---|---|---|---|---|---|---|
| bull | 43.3% | 70.2% | -11.3% | 48.0% | 23 | 1274.04 |
| bear | 38.4% | -0.5% | -0.5% | 0.3% | 0 | 0.00 |
| chop | 18.3% | -11.4% | -11.4% | 7.8% | 0 | 0.00 |

Bear behaviour ✅ controlled; chop behaviour ❌ NOT controlled.

**Robustness — profit factor distribution** (a real edge survives off the exact peak):

| Source | Median | Mean | Min | P25 | P75 | Max |
|---|---|---|---|---|---|---|
| Universe subsample (2/3, 5 seeds) | 0.99 | 2.95 | 0.00 | 0.66 | 5.88 | 7.21 |
| Parameter neighbourhood (84 sets) | 2.42 | 2.94 | 1.25 | 1.96 | 3.68 | 5.81 |

**Tuned walk-forward (tune on IS, apply OOS):** PF 3.29, return 38.4%, max DD -9.4%, Sharpe 0.70, trades 22.
Per-fold chosen params (instability = overfit signal): f0:N=15/stop=3.0, f1:N=15/stop=3.0, f2:N=15/stop=3.0, f3:N=15/stop=3.0, f4:N=15/stop=1.5, f5:N=15/stop=1.5, f6:N=15/stop=3.0, f7:N=15/stop=1.5, f8:N=15/stop=1.5, f9:N=15/stop=2.0, f10:N=25/stop=3.0, f11:N=25/stop=2.0, f12:N=25/stop=2.0, f13:N=15/stop=2.0

**Per-fold OOS stability (headline params):**

| Fold | OOS window | PF | Return | Max DD | Trades |
|---|---|---|---|---|---|
| 0 | 2019-10-01→2020-04-01 | 0.00 | 0.0% | 0.0% | 0 |
| 1 | 2020-04-01→2020-10-01 | 0.00 | 0.0% | 0.0% | 0 |
| 2 | 2020-10-01→2021-04-01 | 50.25 | 53.4% | -9.3% | 2 |
| 3 | 2021-04-01→2021-10-01 | 0.00 | -9.8% | -13.2% | 3 |
| 4 | 2021-10-01→2022-04-01 | 0.16 | -0.9% | -3.4% | 2 |
| 5 | 2022-04-01→2022-10-01 | 0.00 | 0.0% | 0.0% | 0 |
| 6 | 2022-10-01→2023-04-01 | 0.68 | -0.5% | -1.7% | 2 |
| 7 | 2023-04-01→2023-10-01 | 0.00 | 0.1% | -1.7% | 0 |
| 8 | 2023-10-01→2024-04-01 | 31.09 | 7.8% | -7.1% | 4 |
| 9 | 2024-04-01→2024-10-01 | 0.00 | -0.2% | -1.0% | 1 |
| 10 | 2024-10-01→2025-04-01 | 7.39 | 7.1% | -6.2% | 3 |
| 11 | 2025-04-01→2025-10-01 | 0.14 | -2.5% | -4.7% | 4 |
| 12 | 2025-10-01→2026-04-01 | 0.00 | 0.0% | 0.0% | 0 |
| 13 | 2026-04-01→2026-05-21 | 0.00 | 0.0% | 0.0% | 0 |

> ⚠️ **Fragility warning:** the headline metrics pass, but universe subsample median PF 0.99 (< 1.5 — the edge does not survive dropping a third of the coins; it rides on a few specific names). Treat the headline PF as optimistic — effectively a fail on robustness.


### System S2 — Donchian entry N=55, exit N=20

**Headline (starting parameters, out-of-sample, after fees)**

| Metric | Value | Bar | Pass |
|---|---|---|---|
| Profit factor | 4.19 | > 1.5 | ✅ |
| Max drawdown | -19.2% | > -25% | ✅ |
| Sharpe | 0.50 | > 0 | ✅ |
| Total return | 47.8% | — | |
| CAGR | 4.9% | — | |
| Win rate | 36.8% | — | |
| Avg win / avg loss | 7.19 | — | |
| Expectancy / trade (USD) | 63.89 | — | |
| Trade count | 19 | >= 30 | ⚠️ |
| Exposure (time in market) | 24.5% | — | |

**Benchmark — buy & hold BTC (same window):** return 1038.8%, max DD -76.7%, Sharpe 0.79.

**Regime decomposition** (must preserve capital + stay in cash during bear/chop):

| Regime | % of period | Return | Max DD | Exposure | Trades | Trade P&L |
|---|---|---|---|---|---|---|
| bull | 43.3% | 85.2% | -11.7% | 48.3% | 19 | 1213.85 |
| bear | 38.4% | -3.1% | -3.9% | 5.2% | 0 | 0.00 |
| chop | 18.3% | -17.6% | -17.6% | 8.7% | 0 | 0.00 |

Bear behaviour ✅ controlled; chop behaviour ❌ NOT controlled.

**Robustness — profit factor distribution** (a real edge survives off the exact peak):

| Source | Median | Mean | Min | P25 | P75 | Max |
|---|---|---|---|---|---|---|
| Universe subsample (2/3, 5 seeds) | 0.69 | 2.51 | 0.00 | 0.67 | 5.11 | 6.07 |
| Parameter neighbourhood (84 sets) | 2.66 | 2.74 | 1.05 | 1.84 | 3.48 | 4.69 |

**Tuned walk-forward (tune on IS, apply OOS):** PF 3.55, return 46.0%, max DD -9.7%, Sharpe 0.70, trades 22.
Per-fold chosen params (instability = overfit signal): f0:N=15/stop=3.0, f1:N=15/stop=3.0, f2:N=15/stop=3.0, f3:N=15/stop=3.0, f4:N=15/stop=2.0, f5:N=15/stop=2.0, f6:N=15/stop=1.5, f7:N=15/stop=1.5, f8:N=15/stop=1.5, f9:N=15/stop=2.0, f10:N=25/stop=2.0, f11:N=25/stop=2.0, f12:N=25/stop=2.0, f13:N=15/stop=2.0

**Per-fold OOS stability (headline params):**

| Fold | OOS window | PF | Return | Max DD | Trades |
|---|---|---|---|---|---|
| 0 | 2019-10-01→2020-04-01 | 0.00 | 0.0% | 0.0% | 0 |
| 1 | 2020-04-01→2020-10-01 | 0.00 | 0.0% | 0.0% | 0 |
| 2 | 2020-10-01→2021-04-01 | 111.84 | 54.0% | -9.3% | 2 |
| 3 | 2021-04-01→2021-10-01 | 0.00 | -13.4% | -17.1% | 2 |
| 4 | 2021-10-01→2022-04-01 | 0.16 | -0.9% | -3.4% | 2 |
| 5 | 2022-04-01→2022-10-01 | 0.00 | 0.0% | 0.0% | 0 |
| 6 | 2022-10-01→2023-04-01 | 0.00 | -1.1% | -1.4% | 1 |
| 7 | 2023-04-01→2023-10-01 | 0.00 | 0.0% | 0.0% | 0 |
| 8 | 2023-10-01→2024-04-01 | 11.83 | 24.7% | -6.8% | 3 |
| 9 | 2024-04-01→2024-10-01 | 0.00 | -8.9% | -9.6% | 0 |
| 10 | 2024-10-01→2025-04-01 | 4.97 | 5.1% | -7.8% | 3 |
| 11 | 2025-04-01→2025-10-01 | 0.14 | -3.1% | -4.7% | 4 |
| 12 | 2025-10-01→2026-04-01 | 0.00 | 0.0% | 0.0% | 0 |
| 13 | 2026-04-01→2026-05-21 | 0.00 | 0.0% | 0.0% | 0 |

> ⚠️ **Fragility warning:** the headline metrics pass, but universe subsample median PF 0.69 (< 1.5 — the edge does not survive dropping a third of the coins; it rides on a few specific names). Treat the headline PF as optimistic — effectively a fail on robustness.


## Recommendation & reasoning

**NO-GO.** Do not build Phase 2+ infrastructure on this edge as specified. The headline metrics are encouraging but the result is **underpowered** (~20 trades over 8 years) and **not robust** (the edge ≈ breakeven when a third of the universe is dropped, and is concentrated in a single bull window). That is not enough evidence to commit to building the machine.

**What would make a revisit worthwhile (one more look, not endless tuning):** the trade count is throttled by Kraken's thin USD/USDT liquidity under the spec's $50M filter — only ~17 active coins currently clear it, so the cross-section is tiny. A single, pre-registered re-run with a broader/longer universe (lower liquidity floor, more venues, or a longer history) would test whether the edge is real-but-starved or genuinely absent. If that re-run is also flat/fragile on out-of-sample data, **stop for good.** Decide the new parameters BEFORE looking at results, or this becomes the overfitting trap the gate exists to prevent.

_Anti-overfitting note: the headline uses the spec's starting parameters unchanged. Tuned walk-forward and parameter-neighbourhood results are reported as distributions, not peaks; any result that appears only under tuning is treated as a fail._
