# S4 — Intraday Opening-Range Breakout (Cost-Viability-First Test Spec)

_Draft 2026-05-24 · SIMULATED — no real money · status: PRE-TEST (not built, not validated)_

> **Reading note.** Every S1/S3 figure referenced here is real. Every S4 figure is a
> **target or threshold to test**, never a result. S4 has no data, no backtest, no trades.
>
> **This spec is deliberately structured to fail cheaply.** The most likely honest
> outcome is that intraday trading costs exceed any breakout edge at ~£2k on Kraken.
> If so, we want to know in ~1 day of cost modelling — BEFORE building a strategy —
> not after. The killer question comes first. Everything else is gated behind it.

## Why this experiment exists (and why it's different from S1/S3)

S1 (live) and S3 (retired) are both **daily-bar** systems. Neither is actually *present*
in the market intraday. The one untested question in the whole CTS project is therefore:
**does crypto contain an _intraday_ edge — the kind GTS captures in equities via the
session open — and does it survive our gates net of cost?**

This is genuinely different from S3. S3 tried to force *more frequency out of the daily
trend edge* (and failed — all 7 gates, 0.71 corr to S1). S4 tests a **different kind of
edge on a different timeframe**. It is not "make S1 trade more." It is "is there an
intraday edge at all."

It runs through the **identical discipline** as everything else: validate → pre-registered
gates → paper → trade only if it passes. Same pipeline. New question.

## The honest expectation, stated up front

- This will **not** produce "a winning trade per day." It is a 30–50% win-rate breakout
  family, like all the others. It would produce *more trades*, most individual ones
  losing, with the edge (if any) in aggregate. Losing days are guaranteed.
- The dominant risk is **not** signal quality — it's **cost**. Intraday = many trades =
  fees + slippage become the primary P&L driver. At ~£2k on Kraken's books, this is
  exactly where a gross edge goes net-negative. **Cost is the experiment.**

---

# PHASE 0 — The Killer Question (do this FIRST, build nothing)

> **Gate-0: Can ANY plausible intraday breakout edge clear Kraken costs at ~£2k, net,
> out-of-sample? If no → STOP. Log it. No strategy gets built.**

This phase is a cost-and-frequency feasibility model, not a strategy. It answers whether
the experiment is even worth running before a line of strategy code is written.

### 0.1 — Get real intraday data for a small, liquid probe set
- **Bars:** hourly to start (cheaper, sufficient to estimate frequency and cost drag);
  only drop to 15m/5m if hourly looks viable.
- **Probe set:** the handful of genuinely liquid Kraken USD pairs (BTC, ETH, SOL, and
  ~2–3 others that clear a high intraday-volume bar). NOT the full S1 universe — thin
  alts are hopeless intraday and we don't need them to answer the cost question.
- **Window:** enough history to span at least one risk-on and one chop/risk-off stretch
  (intraday cost drag is worst in chop — the same place S1 bleeds).

### 0.2 — Model the cost drag honestly
- **Fees:** Kraken taker fee per side, applied every entry and every exit. Intraday means
  this compounds fast — model it explicitly per round-trip.
- **Slippage:** ADV-proxy as in the S3 spec, BUT scaled to *intraday* volume, not daily —
  intraday liquidity is a fraction of daily, so the proxy must use intraday bar volume.
- **Spread:** at intraday frequency the bid-ask spread itself is a real per-trade cost —
  include it (daily-bar systems can ignore it; intraday cannot).
- **The 2× sensitivity is built in from the start:** report base and 2× cost. An intraday
  edge that only survives optimistic costs is dead on arrival.

### 0.3 — Estimate realistic trade frequency
- A daily-reset ORB produces at most ~1 signal per instrument per day, fewer after a
  regime/volume filter. Across the probe set, estimate trades/week realistically.
- This sets the cost denominator: frequency × round-trip cost = the hurdle any gross
  edge must clear.

### 0.4 — Gate-0 verdict
Compute the **break-even gross edge per trade** required to overcome modelled costs at
realistic frequency, base and 2×. Then sanity-check against what an ORB breakout
plausibly captures intraday in crypto (from the data, not from hope).

- **If the required gross edge exceeds what's plausibly there → STOP.** Log in
  `EXPERIMENTS.md` as "S4 cost-infeasible at £2k/Kraken intraday" — a real, valuable
  finding, same category as S3's retire. **Do not proceed to Phase 1.**
- **If there's plausible headroom → proceed to Phase 1.** (Headroom, not proof — Phase 1
  still has to actually demonstrate the edge.)

**Most likely outcome: Gate-0 stops us. That's the experiment working, cheaply.**

---

# PHASE 1 — Strategy build (ONLY if Gate-0 passes)

Mirrors S3's structure so it reuses the tested harness where possible. **S1 untouched.**

### 1.1 — Signal (ORB, long-only spot)
- **Reference open:** 00:00 UTC daily candle (standard crypto ORB anchor for 24/7).
- **Opening range:** define an early-session window (e.g. first N hours) high/low.
- **Entry:** price closes *above* the opening-range high (long only — down-leg is exit to
  stable/cash, never short, per spot-only/FCA constraint).
- **Confirmation:** RVOL ≥ ~1.5 on the break and a *close* beyond the range (not a wick) —
  the same confirmation family GTS/S1 already use, to filter false breaks.
- **Intraday anchor:** longs only above VWAP (standard ORB filter).
- **Differentiation check:** S4 must not collapse into "S1 on a faster clock." Measure
  realized correlation to S1 (gate in Phase 2). Intraday timeframe *should* make it
  structurally different, but verify, don't assume — that's the lesson from S3's 0.71.

### 1.2 — Exit / sizing
- **Stop:** intraday ATR-based (range-defined), tight per ORB convention.
- **Exit:** end-of-session flat, OR opposite-side break, OR stop — define one rule set and
  pre-register it; don't leave exit discretionary.
- **Sizing:** small % risk per trade, spot, no leverage, no funding leg.
- **Regime gate:** reuse S1's BTC risk-on filter — no intraday longs when the daily regime
  is risk-off. (Intraday chop in a risk-off tape is where this strategy would die; gate it.)

### 1.3 — Reuse / new
- **Reuse:** fee model (extended for spread + intraday slippage), portfolio accounting,
  walk-forward fold generator, bootstrap-CI / effective-N module, paper/dashboard/CI
  conventions.
- **New:** intraday data ingest + cache, ORB signal module, intraday event loop (the
  engine currently steps daily — intraday stepping is the main new build), session/VWAP
  logic.

---

# PHASE 2 — Gates (pre-registered, set in code BEFORE running)

Same discipline that retired S3 and S2. Decide thresholds first; never move them after
seeing results.

- **Net OOS profit factor** ≥ 1.3 (do NOT expect S1's 2.23; higher-frequency edges are
  thinner per trade).
- **Net OOS Sharpe** ≥ 0.71 (must at least match S1 net of cost, or it isn't earning a
  slot).
- **Max drawdown** within an explicit bound (set it before running, e.g. ≤ -25%).
- **Lower-CI bound of net PF > 1.0** on the **effective** (correlation-adjusted) sample.
  Intraday gives more *nominal* trades, but if they cluster in the same few liquid names
  they're not independent — effective-N still governs.
- **Net survives 2× cost** (PF still ≥ 1.3 at 2× fees+slippage+spread). This is the
  decisive one for an intraday system.
- **S4↔S1 equity correlation < 0.6** — the gate that caught S3. If S4 is just a faster,
  busier clone of S1's exposure, it adds cost and drawdown without diversification.

Pass ALL → promote to paper alongside S1 on the dashboard (Phase 3).
Fail ANY → retire, log in `EXPERIMENTS.md`, exactly like S3. No loosening to rescue.

---

# PHASE 3 — Paper + dashboard (ONLY if all gates pass)

- Wire S4 into the daily/intraday CI as a separate paper variant.
- Dashboard panel alongside S1 and the retired S3 reference.
- **Shared-cache discipline:** S4's intraday ingest must NOT alter what S1 sees in the
  live cron — same rule enforced during the S3 broad ingest. S1's daily universe and
  behaviour stay identical.
- **S1 remains untouched at 0.6%, daily, throughout all phases.**

---

# Constraints that don't bend

- **Spot-only, Kraken, no leverage, no perps, no funding** (FCA retail + project rule).
- **Survivorship-clean, point-in-time** universe and data, including any delisted probes.
- **Net-of-cost, out-of-sample only.** Gross/in-sample numbers are not evidence (the S3
  +705% smoke and S1's survivorship-optimistic 2.56 are the cautionary cases).
- **S4 will not earn daily.** It trades more; it still has losing days, weeks, and
  drawdowns. "More trades" ≠ "daily profit" — that distinction is non-negotiable.

# Open questions before Phase 0

1. **Intraday data source + cost** — does the current data provider give intraday Kraken
   OHLCV+volume, and at what credit cost? (Phase 0 needs this; it's the long pole.)
2. **Probe set size** — 3 names (BTC/ETH/SOL) to answer the cost question minimally, or
   ~5–6 for a slightly broader read? More = more credits.
3. **Bar granularity to start** — hourly (recommended, cheaper) vs straight to 15m.
4. **Opening-range window length** — first 1h / 2h / 4h after 00:00 UTC? (A Phase-1
   parameter to sweep, but pick a sensible default to start.)
