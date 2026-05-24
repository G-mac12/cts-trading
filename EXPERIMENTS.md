# CTS — Pre-registered experiments

Design changes tried AFTER the Phase 1 gate. Each is **pre-registered** (success/
kill criteria fixed in git *before* the run) and tested once on out-of-sample,
after-fee, survivorship-clean data. Failures are kept here as evidence, not deleted.

---

## E1 — Eligibility filter $50M → $10M (broader universe) · 2026-05-23 · **PASSED (qualified)**

The original §50M filter starved Kraken's thin USD/USDT cross-section to ~20 trades
(fragile, NO-GO). Single lever changed to $10M. Result: S1 PF 2.66 / DD −17% /
Sharpe 0.62 / 50 trades / subsample median PF 1.67; S2 PF 2.42 / DD −24% / 0.49 /
44 trades / 2.72. Pre-registered kill criteria (clear §9, subsample median ≥ 1.5,
≥ 30 trades) were NOT triggered → the edge survived. Mechanical verdict still
"NO-GO (QUALIFIED)" purely on chop give-back. This $10M universe is now the baseline.
See `FINDINGS.md`.

---

## E2 — Pullback-in-uptrend entry (frequency boost) · 2026-05-23 · **FAILED → reverted**

Goal: raise trade frequency from ~6–8/yr by adding a second entry (buy when price
> 50d MA and close crosses back above the 10d MA), same edge family, same multi-day
holds so the fee floor still works.

Pre-registered criteria (for ≥ 1 system, +pullback must): (a) clear §9 (PF > 1.5,
DD < 25%, Sharpe > 0); (b) subsample median PF ≥ 1.5; (c) raise trades ≥ 1.5×.

| variant | trades | PF | ret | maxDD | Sharpe | subsample median PF |
|---|---|---|---|---|---|---|
| S1 breakout-only | 50 | 2.66 | +80% | −17.2% | 0.62 | 1.67 |
| S1 +pullback | 103 | 1.62 | +72% | **−29.1%** | 0.51 | **1.33** |
| S2 breakout-only | 44 | 2.42 | +61% | −24.1% | 0.49 | 2.72 |
| S2 +pullback | 82 | 1.90 | +98% | **−32.9%** | 0.57 | 1.72 |

Verdict: trade count rose ~2× (c met), **but both variants bust the 25% drawdown
limit (a failed)**, profit factor fell, and S1 lost robustness (b failed). Neither
system met all criteria → **reverted to breakout-only** (the `pullback_entry` flag
remains in the engine, off by default). No MA-period tuning attempted — that would
be the overfitting trap.

**Takeaway:** on Kraken spot, the extra trades come from more marginal setups that
worsen drawdown and dilute the edge. Frequency and risk-control trade off directly
here — which reinforces that the slow, selective breakout system is close to
constraint-optimal for this venue/instrument.

---

## E3 — Account-appropriate liquidity floor + risk re-size · 2026-05-23 · **PASSED for S1**

Insight: the institutional $50M/$10M volume filter is mis-set for a £2k account —
a £200 position is invisible even in a $1M/day coin. Lowering the floor is the
Turtle "more markets" lever (breadth), done correctly for the account size.

Sweep on the same 157-coin panel (no new data):

| filter | sys | trades | PF | ret | maxDD | Sharpe | subsample median PF |
|---|---|---|---|---|---|---|---|
| $50M | S1 | 23 | 4.08 | +50% | −15.2% | 0.58 | 0.54 |
| $50M | S2 | 19 | 4.19 | +48% | −19.2% | 0.50 | 1.14 |
| $10M | S1 | 50 | 2.66 | +80% | −17.2% | 0.62 | 1.67 |
| $10M | S2 | 44 | 2.42 | +61% | −24.1% | 0.49 | 2.72 |
| $1M | S1 | 108 | 2.46 | +213% | −31.2% | 0.81 | 2.39 |
| $1M | S2 | 90 | 2.23 | +148% | −38.9% | 0.65 | 2.10 |

At $1M the edge IMPROVES on every quality axis (≈2× trades, PF strong, Sharpe up,
robustness up) — only max drawdown busts 25%. Drawdown is a risk-sizing dial
(orthogonal to the edge), so a pre-registered sizing fix: risk/position 1% → 0.6%.

| filter | sys | risk% | trades | PF | ret | maxDD | Sharpe | subsample median PF |
|---|---|---|---|---|---|---|---|---|
| $1M | S1 | 0.6% | 117 | 2.56 | +131% | **−20.5%** | 0.78 | 2.16 |
| $1M | S2 | 0.6% | 95 | 2.29 | +90% | −32.0% | 0.59 | 2.14 |

**Verdict:** **S1 @ $1M / 0.6% risk PASSES** all criteria — 117 trades (2.3× the $10M
baseline), PF 2.56, max DD −20.5% (< 25%), Sharpe 0.78, robust (subsample 2.16).
**S2 fails** — even re-sized its drawdown stays at −32% (slow 20d exit holds losers
too long in the broader universe). Adopt **S1** as the realigned baseline; retire S2
to comparison-only. No further risk-tuning (0.6% was pre-registered).

**Why this is risk management, not curve-fitting:** scaling per-position risk scales
the equity curve's amplitude (return and drawdown together) but leaves PF, Sharpe,
win-rate and subsample robustness ~invariant — it cannot manufacture an edge, only
size one. Confirmed: PF/Sharpe/subsample barely move from 1% → 0.6%.

---

## S3 — Daily cross-sectional momentum rotation · 2026-05-24 · **FAILED → RETIRED**

A separate parallel track (NOT a change to S1): rank a broad segmented universe daily
by risk-adjusted relative strength (90d return/vol, skip-7) and rotate into a dynamic
top-6 (max 2/segment, hysteresis buffer), regime-gated to cash, equal-weight, net of
Kraken-Pro taker + ADV-proxy slippage. Universe: $1M floor, ~30 names, 7 segments,
survivorship-clean incl. delisted. Spec: `S3_SPEC.md`. Gate locked in code before the
run (`scripts/s3_gate.py`): net OOS PF ≥ 1.3 · Sharpe ≥ 0.78 · maxDD ≤ −25% · lower-CI
net PF > 1.0 · S3↔S1 correlation < 0.6 · survive 2× slippage · sweep-robust.

**Full-period SMOKE (in-sample, NOT the verdict):** +705%, PF 2.23 — looked great.

**Held-out OOS (2023-01 → 2026-05; deployment sized to 45% on IS to target 25% DD):**

| metric | value | bar | pass |
|---|---|---|---|
| trades | 306 — but **N_eff ≈ 1.9** (ρ̄ 0.52) | — | — |
| net PF | 1.27, **CI [0.70, 2.13]** | ≥1.3 / lower-CI>1.0 | ❌ / ❌ |
| Sharpe | 0.21, CI [−0.73, 1.12] | ≥0.78 | ❌ |
| max DD | **−30.4%** | ≤−25% | ❌ |
| 2× slippage PF | 1.24 | ≥1.3 | ❌ |
| sweep median PF | 1.22 (9 combos) | ≥1.3 | ❌ |
| **S3↔S1 corr** | **0.71** | <0.6 | ❌ |

**Verdict: RETIRE (failed all 7).** Why, honestly:
- The smoke's +705% was **in-sample**, dominated by the 2021 bull. Out-of-sample, net of
  cost and honestly sized, the edge is weak and noisy.
- **Lower CI of net PF = 0.70 (< 1.0)** — the spec's explicit "apparent edge is noise"
  retire trigger.
- **N_eff ≈ 1.9**: 306 nominal trades are ~2 independent bets (ρ̄ 0.52) → the CIs are huge.
- **S3↔S1 correlation 0.71** — even though S3 does NOT hold the same names (majors only
  24%, held/universe vol ratio 1.08, low-vol-majors-hug FALSE), its equity co-moves with
  S1 because crypto correlates in risk-on/off. So S3 adds cost + drawdown without adding
  diversification.

Did **not** loosen any signal/threshold to rescue it. The S3 harness (`src/cts/s3/`,
`scripts/s3_*.py`) stays in the repo as a tested, **retired** reference — it is **not**
wired into the paper-trader or dashboard. S1 untouched throughout.

---

## S4 — Intraday Opening-Range Breakout · 2026-05-24 · **STOPPED at Gate-0 (cost-infeasible)**

A genuinely new question (not "make S1 trade more", which S3 already tested): is there an
*intraday* breakout edge in crypto, and does it survive Kraken costs at ~£2k? Spec:
`S4_ORB_SPEC.md`. The spec is built to **fail cheaply** — Phase 0 is a cost-viability KILL
GATE answered BEFORE any strategy is built. It stopped us, as predicted.

**Data (the long pole):** CoinAPI *does* serve intraday Kraken OHLCV. Pulled BTC/ETH/SOL
**hourly**, 2022-01-01→2026-05-23 (~38.3k bars each) into an **isolated** cache
(`data/cache/coinapi_intraday/`, `__1HRS`) — S1's daily cache untouched. Credit model
measured = ceil(bars/100)/request; spend **1,149 credits** (probe) + 5 calibration.

**Phase-0 model** (`scripts/s4_phase0.py`, read-only feasibility, NOT the gated harness):
a sensible daily-reset ORB — opening range = first 4 UTC hours, entry on hourly close above
the range high with RVOL≥1.5 and above session VWAP, S1's daily BTC regime gate, exit at
1.5×ATR stop or end-of-session. Cost = Kraken taker 0.40%/side (0.80% round trip) + per-name
spread (2–8 bps) + S3 ADV-proxy slippage on **intraday** bar volume; base and 2×.

| probe (pooled) | trades | tr/yr | win% | mean gross/trade | break-even (cost) | mean net/trade | net PF | net PF 2× |
|---|---|---|---|---|---|---|---|---|
| BTC/ETH/SOL hourly | 837 | ~100 | 39% | **0.112%** | **0.945%** | **−0.833%** | **0.38** | **0.15** |

**Gate-0 verdict: STOP — cost-infeasible at £2k/Kraken intraday.** The gross capture an ORB
actually delivers (~0.11%/trade; winners ~2.0%, but only 39% win) is ~**8× too small** to
clear the round-trip cost hurdle, which is dominated by the **0.80% taker fee floor**. Mean
net is negative on *every* parameterisation.

**Structural, not parameter-fragile** (sensitivity, same data, no rescue attempt):

| OR window × stop (taker 0.40%) | mean gross/trade | net PF |
|---|---|---|
| 2h/4h/6h × 1.0/1.5/2.0×ATR (9 combos) | 0.013% – 0.164% | 0.28 – 0.43 |
| best params @ **maker 0.25%** (optimistic) | 0.112% | 0.53 |

No opening-range/stop choice gets gross capture within an order of magnitude of the
0.80% fee floor; even optimistic maker fees leave net PF 0.53 (< 1.0). The conclusion is
structural to ~£2k on Kraken's lowest fee tier, not an artifact of tuning.

**Did NOT build Phase 1.** No ORB signal module, no intraday engine, no paper wiring — the
kill gate is the whole point. Kept as tested Phase-0 evidence: the intraday ingest
(`scripts/s4_ingest_intraday.py`, adapter `intraday_ohlcv`), the feasibility model
(`scripts/s4_phase0.py`), and the cached hourly probe data. Same discipline as S2/S3/
pullback: gate-or-stop, no loosening. **S1 untouched at 0.6%, daily, throughout.**

**Lesson:** the one untested edge family (intraday) is killed by the most mundane force
(fees), exactly where the spec predicted. At £2k on Kraken, round-tripping intraday costs
~0.8%+ while a breakout bar captures ~0.1% on average — the timeframe is cost-locked. Would
only reopen if (a) the fee tier dropped materially (much larger book) or (b) a
fundamentally higher-capture intraday signal were proposed — both separate, pre-registered
decisions.
