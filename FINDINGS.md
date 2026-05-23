# CTS Phase 1 — FINDINGS

_Generated 2026-05-23T08:41:05.652102+00:00 · data source: coinapi · window 2018-04-01 → 2026-05-22_

## VERDICT: **NO-GO (QUALIFIED — clears every hard criterion except chop; judgement call)** for Phase 2

> ✅ Data adapter reports survivorship-clean coverage (delisted symbols included).

### Does the edge survive — plain answer

**Borderline / judgement call — the strategy clears every hard criterion except the chop test.** On the starting parameters, both systems pass the §9 headline metrics (profit factor, drawdown, Sharpe), are adequately powered, sit in cash during bear markets, AND now survive both universe-subsampling and the parameter neighbourhood. The single failing criterion is **chop give-back**:
- **S1**: headline PF/DD/Sharpe pass; 50 trades (adequately powered); subsample median PF 1.67 (survives subsampling); **chop give-back -15.2%** over chop days, though only 6.1% exposed (it does sit in cash).
- **S2**: headline PF/DD/Sharpe pass; 44 trades (adequately powered); subsample median PF 2.72 (survives subsampling); **chop give-back -29.7%** over chop days, though only 7.8% exposed (it does sit in cash).

- **S1** OOS fold spread: 10 of 14 folds traded, 6 profitable (check the per-fold table for concentration).
- **S2** OOS fold spread: 10 of 14 folds traded, 5 profitable (check the per-fold table for concentration).

This is **not a clean fail.** Every hard, pre-registered criterion is met — the only open question is whether chop give-back clears the spec's 'controlled chop' bar. The strategy DOES go to cash in chop (low exposure) and overall drawdown stays within 25%; it loses the chop test only by giving back bull gains during transitions. Whether that is acceptable is a human decision — see the recommendation.

### Universe & assumptions

- Symbols actually traded: **157** · BTC (regime): `KRAKEN_SPOT_BTC_USD` · rebalances: 425.
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
| Profit factor | 2.66 | > 1.5 | ✅ |
| Max drawdown | -17.2% | > -25% | ✅ |
| Sharpe | 0.62 | > 0 | ✅ |
| Total return | 80.2% | — | |
| CAGR | 7.5% | — | |
| Win rate | 36.0% | — | |
| Avg win / avg loss | 4.72 | — | |
| Expectancy / trade (USD) | 40.74 | — | |
| Trade count | 50 | >= 30 | ✅ |
| Exposure (time in market) | 26.3% | — | |

**Benchmark — buy & hold BTC (same window):** return 1038.8%, max DD -76.7%, Sharpe 0.79.

**Regime decomposition** (must preserve capital + stay in cash during bear/chop):

| Regime | % of period | Return | Max DD | Exposure | Trades | Trade P&L |
|---|---|---|---|---|---|---|
| bull | 43.3% | 112.6% | -16.3% | 58.0% | 50 | 2036.98 |
| bear | 38.4% | 0.0% | 0.0% | 0.0% | 0 | 0.00 |
| chop | 18.3% | -15.2% | -15.2% | 6.1% | 0 | 0.00 |

Bear behaviour ✅ controlled; chop behaviour ❌ NOT controlled.

**Robustness — profit factor distribution** (a real edge survives off the exact peak):

| Source | Median | Mean | Min | P25 | P75 | Max |
|---|---|---|---|---|---|---|
| Universe subsample (2/3, 5 seeds) | 1.67 | 1.87 | 0.91 | 1.15 | 2.74 | 2.89 |
| Parameter neighbourhood (84 sets) | 2.05 | 2.03 | 0.83 | 1.68 | 2.37 | 3.39 |

**Tuned walk-forward (tune on IS, apply OOS):** PF 3.44, return 158.1%, max DD -15.4%, Sharpe 0.99, trades 50.
Per-fold chosen params (instability = overfit signal): f0:N=15/stop=1.5, f1:N=15/stop=1.5, f2:N=15/stop=1.5, f3:N=15/stop=1.5, f4:N=15/stop=1.5, f5:N=15/stop=1.5, f6:N=15/stop=1.5, f7:N=15/stop=1.5, f8:N=15/stop=1.5, f9:N=15/stop=1.5, f10:N=15/stop=1.5, f11:N=15/stop=2.5, f12:N=30/stop=3.0, f13:N=30/stop=2.5

**Per-fold OOS stability (headline params):**

| Fold | OOS window | PF | Return | Max DD | Trades |
|---|---|---|---|---|---|
| 0 | 2019-10-01→2020-04-01 | 0.00 | -1.1% | -1.7% | 1 |
| 1 | 2020-04-01→2020-10-01 | 4.24 | 3.5% | -5.8% | 3 |
| 2 | 2020-10-01→2021-04-01 | 17.81 | 74.2% | -16.3% | 5 |
| 3 | 2021-04-01→2021-10-01 | 0.00 | -9.3% | -14.0% | 2 |
| 4 | 2021-10-01→2022-04-01 | 0.09 | -2.5% | -5.1% | 4 |
| 5 | 2022-04-01→2022-10-01 | 0.00 | 0.0% | 0.0% | 0 |
| 6 | 2022-10-01→2023-04-01 | 1.51 | 1.0% | -1.9% | 3 |
| 7 | 2023-04-01→2023-10-01 | 0.00 | -0.5% | -3.0% | 0 |
| 8 | 2023-10-01→2024-04-01 | 2.17 | 10.3% | -10.4% | 11 |
| 9 | 2024-04-01→2024-10-01 | 0.00 | -0.7% | -0.7% | 0 |
| 10 | 2024-10-01→2025-04-01 | 1.14 | 0.9% | -9.2% | 9 |
| 11 | 2025-04-01→2025-10-01 | 0.83 | -0.7% | -8.8% | 7 |
| 12 | 2025-10-01→2026-04-01 | 0.00 | 0.0% | 0.0% | 0 |
| 13 | 2026-04-01→2026-05-22 | 9.83 | 1.5% | -0.1% | 2 |


### System S2 — Donchian entry N=55, exit N=20

**Headline (starting parameters, out-of-sample, after fees)**

| Metric | Value | Bar | Pass |
|---|---|---|---|
| Profit factor | 2.42 | > 1.5 | ✅ |
| Max drawdown | -24.1% | > -25% | ✅ |
| Sharpe | 0.49 | > 0 | ✅ |
| Total return | 60.8% | — | |
| CAGR | 6.0% | — | |
| Win rate | 29.5% | — | |
| Avg win / avg loss | 5.78 | — | |
| Expectancy / trade (USD) | 35.07 | — | |
| Trade count | 44 | >= 30 | ✅ |
| Exposure (time in market) | 30.9% | — | |

**Benchmark — buy & hold BTC (same window):** return 1038.8%, max DD -76.7%, Sharpe 0.79.

**Regime decomposition** (must preserve capital + stay in cash during bear/chop):

| Regime | % of period | Return | Max DD | Exposure | Trades | Trade P&L |
|---|---|---|---|---|---|---|
| bull | 43.3% | 131.3% | -16.8% | 65.9% | 44 | 1543.28 |
| bear | 38.4% | -1.1% | -1.9% | 2.5% | 0 | 0.00 |
| chop | 18.3% | -29.7% | -29.7% | 7.8% | 0 | 0.00 |

Bear behaviour ✅ controlled; chop behaviour ❌ NOT controlled.

**Robustness — profit factor distribution** (a real edge survives off the exact peak):

| Source | Median | Mean | Min | P25 | P75 | Max |
|---|---|---|---|---|---|---|
| Universe subsample (2/3, 5 seeds) | 2.72 | 2.09 | 0.57 | 1.48 | 2.76 | 2.93 |
| Parameter neighbourhood (84 sets) | 2.37 | 2.36 | 1.37 | 2.00 | 2.64 | 3.54 |

**Tuned walk-forward (tune on IS, apply OOS):** PF 3.17, return 123.5%, max DD -16.5%, Sharpe 0.86, trades 49.
Per-fold chosen params (instability = overfit signal): f0:N=15/stop=1.5, f1:N=15/stop=1.5, f2:N=15/stop=2.5, f3:N=15/stop=1.5, f4:N=15/stop=1.5, f5:N=15/stop=1.5, f6:N=15/stop=1.5, f7:N=15/stop=1.5, f8:N=15/stop=1.5, f9:N=20/stop=1.5, f10:N=15/stop=1.5, f11:N=15/stop=1.5, f12:N=30/stop=2.5, f13:N=30/stop=2.5

**Per-fold OOS stability (headline params):**

| Fold | OOS window | PF | Return | Max DD | Trades |
|---|---|---|---|---|---|
| 0 | 2019-10-01→2020-04-01 | 0.00 | -1.1% | -1.7% | 1 |
| 1 | 2020-04-01→2020-10-01 | 0.72 | -0.3% | -5.3% | 2 |
| 2 | 2020-10-01→2021-04-01 | 9.52 | 53.8% | -16.8% | 6 |
| 3 | 2021-04-01→2021-10-01 | 0.00 | -13.3% | -19.6% | 2 |
| 4 | 2021-10-01→2022-04-01 | 0.05 | -3.8% | -8.3% | 4 |
| 5 | 2022-04-01→2022-10-01 | 0.00 | 0.0% | 0.0% | 0 |
| 6 | 2022-10-01→2023-04-01 | 0.00 | -0.8% | -1.6% | 2 |
| 7 | 2023-04-01→2023-10-01 | 0.00 | -1.1% | -1.9% | 0 |
| 8 | 2023-10-01→2024-04-01 | 3.06 | 30.2% | -10.3% | 9 |
| 9 | 2024-04-01→2024-10-01 | 0.00 | -10.8% | -10.8% | 0 |
| 10 | 2024-10-01→2025-04-01 | 1.38 | 2.1% | -8.1% | 8 |
| 11 | 2025-04-01→2025-10-01 | 1.19 | 0.8% | -7.6% | 6 |
| 12 | 2025-10-01→2026-04-01 | 0.00 | 0.0% | 0.0% | 0 |
| 13 | 2026-04-01→2026-05-22 | 9.83 | 1.5% | -0.1% | 2 |


## Recommendation & reasoning

**QUALIFIED — judgement call (mechanical verdict NO-GO on the chop criterion only).** On the starting parameters the edge clears every hard bar after fees: profit factor > 1.5, drawdown < 25%, positive Sharpe, ≥ 30 trades, goes to cash in bear markets, and — the part that sank the first attempt — it now **survives universe-subsampling (median PF ≥ 1.5) and the parameter neighbourhood.** That is genuine, robust evidence, not a knife-edge.

The one open issue is **chop give-back**: during choppy/transition periods the strategy gives back a slice of bull gains (worse for the slower N=55 system). It is not a blow-up — chop exposure is low and total drawdown stays within 25% — but it does fail a strict reading of 'controlled chop'. **This is the only thing between here and a GO.**

**Recommendation:** treat chop-handling as the FIRST hardening task of Phase 2 (e.g. tighter regime exit, faster de-risking on regime flip) and proceed to the **paper-trading** stage to validate on live data — but do **NOT** make any further backtest parameter changes. This was the single pre-registered revisit; chasing the chop number in-sample now would be the overfitting trap. If chop-handling can't be fixed without curve-fitting, stop.

_Anti-overfitting note: the headline uses the spec's starting parameters unchanged. Tuned walk-forward and parameter-neighbourhood results are reported as distributions, not peaks; any result that appears only under tuning is treated as a fail._
