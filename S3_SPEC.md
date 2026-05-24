# S3 — Daily-Cadence Cross-Sectional Momentum (Design Spec)

_Draft 2026-05-24 · SIMULATED — no real money · status: PRE-BACKTEST (not yet validated)_

> **Reading note.** Every S1 figure below is real (from backtest, after fees, out-of-sample).
> Every S3 figure is a **target to validate**, not a result. S3 has no trades and no backtest yet.

## Purpose

S3 is a separate track that runs **alongside** S1, not a modification of it. S1 stays exactly as
it is — the selective, high-conviction overlay (profit factor 2.56 · max DD -20.5% · Sharpe 0.78 ·
117 trades). S3's job is the thing S1 structurally can't do: produce a trade most days, by ranking a
broad universe and rotating into what fits, rather than waiting for a rare absolute trigger. "Fit"
in S3 is **relative ranking**, not a rare setup — that is what makes daily cadence honest instead of
a loosened filter.

This spec covers only the two levers that decide whether S3 is **testable**: the **universe** and the
**bar size**. Entry/exit ranking logic, regime gating, and sizing rules come in a follow-up once S1's
exact entry logic is in the repo.

## The one idea this whole spec serves

> **Validation volume comes from _width × history × turnover_ in the backtest.**
> **Live cadence comes from _width × turnover_.**
> **Neither ever comes from lowering the entry bar.**

That single sentence resolves the "14/year is too few to test" problem. You do not wait years in
paper to build a sample — you generate it from breadth and history in the backtest, then resample it
for confidence intervals. Paper-forward only *confirms* the backtest; it is not the sample.

---

## Lever 1 — Universe

Two different jobs, often confused, are both done by the universe:

- **Breadth → sample size & turnover** (how many trades you get).
- **Correlation → _validity_ of that sample** (how many of those trades are actually independent bets).

These pull in opposite directions, and the math below shows why you can't fix the second by doing
more of the first.

### Effective vs nominal sample size

For an (approximately) equicorrelated basket, the number of *independent* bets is:

```
N_eff  ≈  N / (1 + (N − 1) · ρ̄)
```

where `N` = number of names held/ranked and `ρ̄` = average pairwise correlation.

| Nominal N | ρ̄ = 0.75 | ρ̄ = 0.50 | ρ̄ = 0.30 |
|-----------|-----------|-----------|-----------|
| 30        | ~1.3      | ~1.9      | ~3.1      |
| 40        | ~1.3      | ~2.0      | ~3.2      |

Read the rows, then read the columns:

- **Adding names at the same correlation does almost nothing** (30 → 40 at ρ̄ = 0.5 moves N_eff
  from ~1.9 to ~2.0). More correlated alts ≠ more diversification.
- **Lowering ρ̄ is the only real lever for independence** (0.75 → 0.30 nearly triples N_eff).

Your current watchlist — ZEC, XMR, DOGE, TRX, INJ, LUNA, AKT, ONDO, TON, VVV, USELESS — is almost
entirely alts and memes that co-move with BTC, so its ρ̄ in a risk-off flush is plausibly ~0.7–0.8.
A daily rotation across it could *look* busy and still be ~1–2 independent bets, all of which a single
RISK-OFF move hits at once. **Size S3 for independent bets, not ticker count.**

### Universe construction rules

1. **Segment for lower ρ̄.** Deliberately span buckets with different drivers so the average pairwise
   correlation falls: large-cap majors (also the regime benchmark), L1s, DeFi, RWA/infra, privacy,
   memes. Target: pull ρ̄ from ~0.75 toward ~0.5. (Truly uncorrelated is unrealistic in crypto — the
   honest goal is *reduced*, not *removed*.)
2. **Per-segment position cap.** No more than _k_ of the held top-N slots from one segment, so the book
   can't quietly become "six memes." This is what actually protects drawdown.
3. **Liquidity floor.** Minimum 30-day average dollar volume (start strict, e.g. ≥ $50–100M/day) on a
   tier-1 venue. This filters the thin names (VVV, USELESS-type tickers) where backtested edge dies in
   slippage — and is the instrument-level answer to "is this even tradeable volume."
4. **Listing-age minimum.** Require enough history to rank on (e.g. ≥ 12 months) — and see survivorship
   note below.
5. **Rule-based, dynamic membership.** Define inclusion as *rules* re-evaluated periodically (liquidity
   + age + venue), not a frozen ticker list. Crypto universes churn.
6. **Target universe size: ~20–40 names, hold top ~5–8.** Big enough for sample and turnover, small
   enough to stay liquid and keep the ranking meaningful.

### Survivorship — the backtest killer

The backtest universe **must be reconstructed point-in-time** and **must include coins that later
died**. The original LUNA collapse is the textbook case: a backtest built only from coins alive today
silently deletes the worst outcomes and manufactures a fantasy edge. If S3's backtest can't include
dead/delisted names at their historical weights, its numbers are not trustworthy — full stop.

---

## Lever 2 — Bar size

Bar size sets the clock: how often S3 looks, ranks, and can rotate. It's the second source of
sample volume (history measured in bars) and the main driver of cost and infrastructure needs.

| Bar | Decisions/day | Sample from same history | Cost pressure | Infra needed | Verdict |
|-----|---------------|--------------------------|---------------|--------------|---------|
| **Daily** | 1 | High (long history, low noise) | Low | None beyond current daily CI | **Start here** |
| **4h** | 6 | Higher (6× ranking obs) | Medium | Bot runs intraday on closed bars | Phase 2 |
| **1h / intraday** | 24+ | Highest | High (slippage + funding) | Live execution, real slippage model | Premature |

**Recommendation: daily bars first.** It maps directly onto the daily GitHub Actions cadence you
already run, needs no new infrastructure, keeps costs in a range where the edge can survive them, and
the lower noise makes the backtest more honest. Graduate to 4h only if the daily version passes its
gate and you want more ranking resolution — and treat 1h/intraday as a separate future project with
its own execution and slippage work, not a config change.

A nuance worth keeping straight: a faster bar gives you **more ranking observations and finer entry
timing**, but it does **not** automatically give more trades unless you also shorten holding periods.
Trade count is set by `slots × (period / avg-hold)`, not by bar size alone.

---

## Worked example — does this actually generate testable volume?

Illustrative, daily bars, to show the arithmetic (not a forecast):

```
Universe:        30 names
History:         ~3 years ≈ 1,095 daily bars (crypto trades 365d/yr)
Held slots:      top 6
Avg holding:     ~10 days
```

**Backtest (validation) volume**

```
nominal position-trades ≈ slots × (days / avg-hold)
                        ≈ 6 × (1,095 / 10)
                        ≈ ~660 nominal trades
```

~660 nominal vs S1's 117 — and produced from breadth + history, **without waiting and without
loosening anything.** But apply the validity discount: at ρ̄ ≈ 0.6 those 660 are a *small fraction*
that many independent observations, and overlapping holding periods reduce it further. So the rule is:
**report nominal N for activity, but gate on effective-N-adjusted confidence intervals** (next section).

**Live cadence**

```
entries/day ≈ slots / avg-hold ≈ 6 / 10 ≈ 0.6/day ≈ ~200/yr
```

That's the "turn it on and it's trading" feel you want — achieved through width and turnover, not by
firing on weaker signals.

---

## Real volume vs fake volume (cost + OOS)

A backtested trade only counts as real if it survives:

- **Net-of-cost accounting.** Model taker fee (~0.04–0.10% typical), slippage as a function of order
  size vs book depth (this is where the liquidity floor pays off), and **funding** if any leg is a
  perp. A high-frequency edge that's positive gross and negative net is the most common way these
  systems lie.
- **Out-of-sample / walk-forward only.** S1's OOS PF is credible *because* it's simple. S3 has more
  moving parts and a much higher overfitting risk, so it must be judged on walk-forward / held-out
  data, never on the fitted sample.
- **Resampled confidence intervals.** Block / stationary bootstrap the trade-return distribution
  (preserve autocorrelation) and Monte-Carlo the equity path. Report PF, Sharpe and max-DD as
  *intervals*, computed on the **effective** sample, not point estimates on the nominal one.

---

## Gate-or-retire criteria (set BEFORE running)

Same discipline that retired S2 and passed E3. Decide the bar first, then run — no moving it after
seeing results. Proposed defaults (you set the final numbers):

- **Net OOS profit factor** ≥ 1.3 (healthy for higher-frequency; do **not** expect S1's 2.56).
- **Net OOS Sharpe** ≥ S1's 0.78 — S3's case for existing is that breadth *raises* risk-adjusted
  return; if it can't beat S1's Sharpe net of cost, it isn't earning its slot.
- **Max drawdown** within an explicit bound (e.g. ≤ -25%), measured on the correlation-realistic
  (not idealised-independent) equity path.
- **Lower CI bound** of net PF from the bootstrap stays **> 1.0**. If the confidence interval on the
  *effective* sample crosses break-even, the apparent edge is noise → **retire**.

Pass → promote to paper alongside S1 on the dashboard. Fail any → retire and log in `EXPERIMENTS.md`,
exactly like S2.

---

## Open questions before locking the design

1. **S1's exact entry logic** — needed to make S3's ranking complementary rather than overlapping
   (drop `SYSTEM_OVERVIEW.md` / `FINDINGS.md` in and I'll align them).
2. **Spot or perps?** Decides the cost model (funding) and which watchlist names are even reachable.
3. **Which venue(s)?** Sets the real fee/slippage/depth numbers and the liquidity floor.
4. **Final universe size and per-segment caps** — the two numbers that most move effective-N.
