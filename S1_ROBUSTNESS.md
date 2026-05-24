# S1 — Bounded Robustness Audit (existing backtest, S1 untouched)

**What this is.** A read-only audit of S1's *existing* backtest, run after S3 fell into the
in-sample trap, to ask honestly: **does S1 have a milder version of the same disease, and
is it a robust plateau or a fragile peak across its key parameters?** Nothing here changes
the live system, the config, or the paper run. Reproduce with `scripts/s1_robustness.py`
(raw JSON in `data/s1_robustness.json`).

**Bottom line, up front (honest):**
1. **Concentration fragility — CONFIRMED, moderate.** S1's *headline* edge is heavily
   carried by one year (2020 = **85%** of all net profit). **Drop the single best year and
   PF falls 2.23 → 1.20.** The edge is positive in most years but only *large* in big trend
   years. This is a milder, non-fatal cousin of the S3 trap — log it, don't paper over it.
2. **Regime profile is correct and safe.** Bear = cash (0 trades, ~flat). Bull = the engine
   (+198%). Chop = the known give-back (−26% in-chop). The capital-preservation net works.
3. **Parameters: mostly plateau, one caution.** Rebalance cadence and *slower* Donchian
   lengths are a clean plateau; the *fast* side (10–15d) is a cliff. Chosen 20/10 is the
   high-PF/low-DD corner of the plateau — defensible, but it is the plateau's **fastest**
   point.
4. **Risk sizing is edge-neutral — confirmed empirically.** PF/Sharpe ~flat across
   0.4–1.0% risk while return & drawdown scale. Validates the E3 "resize is risk control,
   not curve-fitting" claim.
5. **The broader universe degraded S1 — and it's a MORE honest number, not an artifact.**
   On today's 341-coin cache the headline is **PF 2.23 / maxDD −25.6% / Sharpe 0.71** vs the
   documented 157-coin E3 baseline **2.56 / −20.5% / 0.78**. Resolved by measurement
   (§5 + `scripts/s1_universe_check.py`): S1 traded **0** names below its $1M point-in-time
   floor — the difference is **not** sub-$1M junk. It comes from ~36 *legitimately ≥$1M*
   names the smaller ingest had missed (2023–25 alts: ARB, ONDO, TIA, SUI, ENA, AERO…),
   which S1 would have traded live and which mostly stopped out. So the 157 baseline was
   mildly survivorship-**optimistic**; the 341 number is the more complete estimate.
   Drawdown now nudges past the §9 25% line at 0.6% risk. **Flagged for your decision — no
   change made.**

---

## Setup

- Universe: **341 coins**, survivorship-clean, 2018-04-01 → 2026-05-23 (the current cache,
  broadened during the S3 ingest).
- Net of Kraken-Pro taker (0.40%) + slippage (0.15%/side), via the tested engine.
- Headline S1 = donchian **20/10**, risk **0.6%**, rebalance **7d** (the live config).

> Headline on this cache: **129 trades, PF 2.23, return +117%, maxDD −25.6%, Sharpe 0.71.**

---

## 1. Concentration — does the edge live in one year?

| year | trades | net P&L ($) | share of total | year return | PF |
|---|---:|---:|---:|---:|---:|
| 2019 | 6 | 148 | 5% | +6% | 5.07 |
| **2020** | 13 | **2,510** | **85%** | +33% | **25.68** |
| 2021 | 29 | −591 | −20% | +29%* | 0.11 |
| 2023 | 23 | 432 | 15% | +15% | 1.99 |
| 2024 | 32 | 615 | 21% | +3% | 1.97 |
| 2025 | 21 | 24 | 1% | +0% | 1.07 |
| 2026 | 5 | −176 | −6% | −3% | 0.00 |

\*2021's positive *equity* return with a losing *trade* PF reflects timing within the year
(the 2021 double-top chopped trend-following hard; net trade P&L was negative).

**Drop-the-best-year test:** remove 2020 → **PF 2.23 → 1.196** on the remaining 116 trades.

**Honest reading.** This *is* concentration. The system's **magnitude** of edge depends on
big trending years (2019 and especially 2020). Strip the best year and you're left with a
**weak-positive PF ~1.2** — above 1.0 (still makes money net of cost) but **below the §9
1.5 bar.** That said, it is **meaningfully better than S3's failure**: S3's out-of-sample
edge was statistical *noise* (lower-CI net PF 0.70 < 1.0). S1 is **positive in 5 of 7
years** (2019, 2020, 2023, 2024, 2025) and the two weak years are a known trend-killer
(2021 top) and a 5-trade partial year (2026). This is the expected signature of a
**trend-capture** system — lumpy, dependent on a few big moves — not a single-window
mirage. **But the caveat is real and goes in the monitoring sheet:** do not expect ~2.2–2.6
PF in an ordinary, non-trending year; expect PF ~1.0–2.0, with the big numbers only when a
sustained trend shows up.

> **Interpretation (explicit).** S1's edge is **real-but-bull-weighted** — a structural
> property of trend-following, **NOT** the S3 noise trap. The distinguishing evidence:
> positive in **5 of 7 years**, **bear-safe** (0 trades in bear, ~flat), and it **survives
> its parameter neighbourhood** (§3–§4). Consequence: **a flat or sub-2 PF in a chop/bear
> year is EXPECTED behaviour, not a tripwire.** This is exactly why the "what is NOT a
> tripwire" list in `S1_MONITORING.md` §5 exists — quiet/low-PF stretches when there is no
> trend are the system working as designed, not the edge breaking.

---

## 2. Regime decomposition (independent BTC classification)

| regime | % of period | exposure | compounded return | maxDD | trades | net P&L ($) |
|---|---:|---:|---:|---:|---:|---:|
| bull | 43% | 76% | +198% | −14.1% | 126 | 3,057 |
| bear | 38% | 2% | −1% | −1.5% | 0 | 0 |
| chop | 18% | 21% | −26% | −26.3% | 3 | −96 |

**Reading.** Exactly the intended profile, and it confirms two things:
- **The safety net works.** In *bear* (38% of the period) S1 is ~2% exposed, takes **0
  trades**, and is flat. It genuinely goes to cash — the core §9 capital-preservation
  requirement.
- **The weakness is chop, not bear.** All the drawdown pain (−26.3% in-chop) comes from
  the 18% chop regime — positions opened late in a bull that get held into a flip. This is
  the *same* chop give-back already documented; it is monitored, and the (un-deployed)
  `regime_exit` flag exists as a candidate fix to validate forward, not to backtest-tune.
- **The edge is a bull phenomenon** (+198%, 126 of 129 trades). Consistent with §1: when
  trends exist, S1 captures them; otherwise it should sit quiet.

---

## 3. Plateau vs peak — Donchian breakout length (exit = entry//2)

| entry/exit | trades | PF | return | maxDD | Sharpe |
|---|---:|---:|---:|---:|---:|
| 10/5 | 193 | 1.15 | +12% | −21.3% | 0.20 |
| 15/7 | 167 | 1.43 | +36% | −21.4% | 0.39 |
| **20/10** | 129 | **2.23** | +117% | −25.6% | **0.71** |
| 25/12 | 124 | 2.02 | +95% | −29.2% | 0.62 |
| 30/15 | 118 | 2.04 | +94% | −32.1% | 0.60 |
| 40/20 | 104 | 2.04 | +81% | −34.4% | 0.54 |
| 55/27 | 97 | 2.02 | +75% | −37.1% | 0.50 |

**Reading.** There is a **plateau from 20 through 55** (PF 2.02–2.23, all ≈2.0) and a
**cliff on the fast side** (15/7 → 1.43, 10/5 → 1.15). So the chosen 20/10 is **not a
lone spike** — everything *slower* than it works about as well on PF. Two honest caveats:
- 20 is the plateau's **fastest** point; if anything drifted faster it would degrade. The
  margin on the slow side is comfortable; on the fast side it is not.
- 20/10 is also near **DD-optimal**: drawdown worsens monotonically as you slow down
  (−25.6% at 20 → −37.1% at 55). So 20/10 picks the high-PF *and* low-DD corner of the
  plateau — a sensible a-priori choice, vindicated, rather than a fit.

**Verdict: plateau, with a mild "don't go faster" caution.** Not fragile.

---

## 4. Rebalance cadence

| days | rebalances | trades | PF | return | maxDD | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| 5 | 595 | 135 | 2.47 | +137% | −26.4% | 0.77 |
| **7** | 425 | 129 | 2.23 | +117% | −25.6% | 0.71 |
| 10 | 298 | 121 | 2.65 | +148% | −25.2% | 0.82 |
| 14 | 213 | 119 | 2.11 | +84% | −24.8% | 0.62 |

**Reading.** A clean plateau (PF 2.11–2.65 across all cadences). The chosen 7d is actually
the **second-lowest** PF of the four — i.e. it was **not cherry-picked**; 10d looks
marginally better but all are robust. **Verdict: robust, not a peak.** (No change proposed
— we're in a hold, and the differences are within noise.)

---

## 5. Risk sizing — edge-neutrality check

| risk % | trades | PF | return | maxDD | Sharpe |
|---|---:|---:|---:|---:|---:|
| 0.4 | 135 | 2.31 | +72% | −19.0% | 0.65 |
| **0.6** | 129 | 2.23 | +117% | −25.6% | 0.71 |
| 0.8 | 126 | 2.10 | +137% | −32.3% | 0.69 |
| 1.0 | 121 | 2.10 | +181% | −35.8% | 0.73 |

PF spread across the four = **0.21**; Sharpe spread = **0.08** — both small — while
**return and drawdown scale strongly** (return +72%→+181%, DD −19%→−36%). This is the
empirical proof that **per-position risk is the amplitude dial, not the edge**: it cannot
manufacture profit factor, only size it. Confirms the E3 argument that the 1.0%→0.6%
re-size was risk control, not curve-fitting.

**Honest flag (the new one).** On the documented 157-coin E3 panel, 0.6% risk gave maxDD
**−20.5%** (inside the §9 25% limit). On **today's broader 341-coin cache**, the *same*
0.6% gives **−25.6%** — a hair **past** the limit — and the headline PF/Sharpe also slipped
(2.56→2.23, 0.78→0.71). Nothing in the config changed; the **data cache grew** during the
S3 ingest. The obvious worry: is S1 now trading sub-$1M junk the live filter would reject?
**Resolved by measurement** below.

### 5b. Cache/baseline resolution (`scripts/s1_universe_check.py`, read-only)

S1's backtest schedule applies the **$1M point-in-time** filter, so every name it trades
must have cleared $1M *at the rebalance*. Measured on the 341-coin cache:

| quantity | count |
|---|---:|
| cache names (after static exclusions) | 341 |
| **never** cleared $1M PIT across the full window (true non-traded superset) | **148** |
| ever cleared $1M PIT | 193 |
| ever ELIGIBLE point-in-time (≥$1M **and** ≥90d history) | 152 |
| distinct names S1 actually **traded** | 59 |
| **traded names below $1M PIT** | **0** |

**Answer to "do the extra names sit below $1M?"** Partly yes, partly no — and the
distinction is the whole point:
- The **148** names that never clear $1M PIT are confirmed a **non-traded superset** — S1
  touches **zero** of them. The lowest-liquidity name S1 ever traded peaked at **$1.81M**
  (MKR); all 59 traded names are ≥$1M. So S1 is **not** trading sub-$1M junk. ✔
- **But the 2.56→2.23 difference is NOT caused by those names.** It comes from ~36
  *legitimately ≥$1M* names the original 157-ingest had **missed** — mostly 2023–25 alts
  (ARB $6.6M, ONDO $7.1M, TIA $8.9M, SUI $28.8M, ENA $12.4M, AERO $2.6M, AKT $2.9M, INJ,
  LDO, MINA, VVV, PENGU…). These **would** have been in S1's live universe historically;
  S1 traded them (+12 trades) and most **stopped out** in the 2024–25 chop, which is what
  deepened the drawdown. The 10 biggest losing trades are all ordinary **stops** on liquid
  names ($2.6M–$459M PIT) — genuine whipsaws, not liquidity artifacts.

**Conclusion (honest, less convenient one).** This is the "picture changes" branch: the
extra names are real members of S1's ≥$1M live universe, so the 341 number must **not** be
filed as "informational over a non-traded superset." Instead, the **157-coin 2.56 / −20.5%
was mildly survivorship-optimistic** (its ingest under-sampled the eligible universe), and
the **341-coin 2.23 / −25.6% is the more complete, more honest estimate** of S1's live
behaviour. **Decision (a): DONE** — the committed `FINDINGS.md` is re-baselined to the 341
numbers (PF 2.23 / DD −25.6% / Sharpe 0.71, subsample median 1.99) and fully regenerated for
consistency. At 0.6% risk the −25.6% drawdown fails the §9 `<25%` gate by 0.6pp, so the
**mechanical verdict is now NO-GO**; FINDINGS represents it as **CONDITIONAL on decision (b)**
(0.6% → fails by 0.6pp; 0.4% → passes at ≈−19%; same edge, different dial) — the gate is
respected, not overridden. **Decision (b) stays PARKED** — risk is unchanged at 0.6%; it is
decided cold and separately, never to flip a gate.

---

## Conclusion

S1 is a **trend-capture system whose edge is real but lumpy and bull-dependent**, with the
profit concentrated in big trend years (2020 above all) and a known chop give-back. It is
**not** the S3 failure mode (positive in most years, bear-safe, survives parameter
neighbourhoods) — but it is **not** a uniformly robust 2.2-PF machine either: strip its best
year and it's a marginal ~1.2. Its parameters are a genuine plateau (rebalance; Donchian on
the slow side) rather than a fitted spike, with a mild "don't trade faster than 20-day"
caution. Risk sizing is confirmed edge-neutral.

**What changes as a result:** nothing in the running system (this is a hold). The fragility
is logged here and folded into `S1_MONITORING.md` — specifically, *expect PF ~1.0–2.0 in
ordinary years and only headline numbers in trend years*. The cache/baseline question is
**resolved** (§5b): S1 trades no sub-$1M names, but the broader cache is a *more complete*
view of its real ≥$1M universe, so **2.23 / −25.6% is the more honest baseline** and the
157-coin 2.56 was mildly optimistic. Status of the two flagged items:
- **(a) DONE** — `FINDINGS.md` re-baselined to the 341 numbers and regenerated; verdict is
  **mechanical NO-GO, represented as CONDITIONAL on (b)** (the §9 DD gate is sizing-dependent
  and risk is edge-neutral). `S1_MONITORING.md` now references 2.23 / −25.6%.
- **(b) PARKED** — whether to re-seat drawdown under the §9 25% line via the edge-neutral risk
  lever (0.4% → −19.0%) is a *separate* pre-registered decision, taken cold on its own terms,
  **not** to flip the gate. Risk stays at 0.6% now.

Any actual change to S1 — including (b) and wiring `regime_exit` — remains a separate,
pre-registered decision requiring your go-ahead.
