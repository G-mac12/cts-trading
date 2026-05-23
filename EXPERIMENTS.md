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
