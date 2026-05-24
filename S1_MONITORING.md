# S1 — Live-Monitoring Tripwire Sheet

**Purpose.** Cold-set, pre-registered rules for reading S1's *forward* record (the daily
paper run today; the same rules carry to live later). Decided **now, before** the live
data exists, so that future-me cannot move the goalposts after seeing a good or bad month.
This is the discipline that saved us on S2, the pullback experiment, and S3: decide the
bar first, then read the result honestly.

**One-line summary:** S1 trades rarely (~16/yr, clustered in bull bursts). That means
**early live numbers are mostly noise.** Do not act on PF, Sharpe, or a single drawdown
until enough *independent* trades have closed. Most of this sheet is about **not**
over-reacting.

---

## 0. The validated backtest baseline (the reference we measure against)

S1 @ $1M liquidity floor / 0.6% risk, 8-year survivorship-clean OOS, measured on the
**complete 341-coin cache** (this is the re-baselined, honest reference — see note below):

| metric | backtest reference |
|---|---|
| profit factor | **2.23** |
| max drawdown | **−25.6%** |
| Sharpe | **0.71** |
| trades | ~129 over 8y → **~16/yr** |
| subsample-median PF | 1.99 |
| §9 acceptance floor | PF > 1.5 · maxDD < 25% · Sharpe > 0 |

> **Re-baselined 2026-05-24.** The earlier reference (PF 2.56 / DD −20.5% / Sharpe 0.78)
> came from a 157-coin ingest that had *missed* ~36 legitimately ≥$1M-eligible names
> (2023–25 alts: ARB, ONDO, TIA, SUI, ENA, AERO…). On the complete 341-coin cache those
> names — which S1 *would* have traded live — are included; most stopped out in 2024–25
> chop, so the honest numbers are **softer** (2.23 / −25.6%). This is correcting a
> measurement to the honest one, not a change to the system. See `S1_ROBUSTNESS.md` §5b.
> **Note the drawdown now slightly exceeds the §9 25% line at 0.6% risk.** Decision (b)
> on this is **RESOLVED (2026-05-24): keep 0.6%** (deliberate cold call, no config change).
> Risk-sizing is **edge-neutral** (per the audit), so 0.6%→0.4% would be purely a
> drawdown/return tradeoff (≈−25.6% vs ≈−19% DD, ≈+117% vs +72% return) — we chose the
> fuller return and **accept the deeper drawdown**, including that live DD may run somewhat
> past −25.6% (the tripwires below govern when to act). The mechanical FINDINGS verdict
> stays a deliberately-accepted NO-GO on the DD gate. See `EXPERIMENTS.md` + `S1_ROBUSTNESS.md`.

> These are *backtest* numbers on historical data. Live will be **worse** than backtest
> almost by definition (slippage realism, regime luck, no hindsight on the universe). The
> job of monitoring is not "does live equal 2.23" — it is "is live *consistent with the
> same edge*, or has the edge broken?"

---

## 1. The power problem — how many trades before live-vs-backtest means anything

S1 closes **~16 trades/year**, and they are **not independent**: entries cluster in the
same BTC bull bursts and the book holds ≤5 names at once, so they rise and fall together.
S3 showed this concretely — 306 nominal trades behaved like **~2 independent bets**
(ρ̄ 0.52, N_eff 1.9). S1 will be milder (different exits, ≤5 concurrent) but the same
force applies: **nominal trade count overstates how much you actually know.**

Practical reading thresholds (pre-registered):

| closed trades | what you may conclude |
|---|---|
| **< 10** | **Nothing.** PF/Sharpe are pure noise. Watch only *behaviour* (§4), not P&L. |
| **10–29** | Direction only ("roughly tracking" vs "clearly broken"). No PF verdicts. |
| **≥ 30** | First **tentative** PF read. Expect ~2+ years of live to reach this. |
| **≥ 50** | A PF estimate worth comparing to backtest, still with wide error bars. |

Rule of thumb: **~30 closed trades ≈ 2 years**, and even then treat it as a handful of
independent bets, not 30. **Do not promote paper→live, or retire S1, on < 30 trades.**

---

## 2. Profit-factor tripwires (only once ≥ 30 closed trades)

Backtest PF = 2.23 (re-baselined). Live degradation is expected; collapse is not.

| live PF (rolling, ≥30 trades) | reading | action |
|---|---|---|
| **≥ 1.7** | consistent with the edge | none — running as designed |
| **1.3 – 1.7** | softer than backtest, still a real edge (around the §9 1.5 floor) | note it; keep running; widen the sample |
| **1.0 – 1.3** | edge has materially weakened; at/under the §9 acceptance floor | **investigate** — is it regime (bear/chop drag, expected) or signal decay (not)? Pause any live-scaling. |
| **< 1.0 over ≥30 trades** | losing money net of cost — the backtest edge is not showing up live | **stop trusting S1**: halt promotion to live / size down live; full review before continuing |

Before blaming the edge, always check **context first**: a low PF *during a long
regime-off / bear stretch* is the system doing its job badly-but-safely (few, small
trades), not the signal breaking. Decompose by regime before concluding.

---

## 3. Drawdown tripwires (live, from peak equity)

Backtest worst drawdown (re-baselined) = **−25.6%** at 0.6% risk. This is itself a hair past
the §9 −25% line — **deliberately accepted** (decision (b), resolved; see below). Bands are set
against the **actual −25.6% backtest envelope** we run at today, and live DD may exceed it.

| live drawdown | band | action |
|---|---|---|
| **0 to −18%** | **normal** — within routine backtest experience | none |
| **−18% to −25.6%** | **elevated** but still inside the backtested envelope | watch closely; confirm regime filter is behaving (§4); no new risk-scaling |
| **−25.6% to −30%** | **alarming** — worse than the worst 8-year backtest | **review now**: pause any plan to add capital; verify it's market-driven, not a bug (stops firing? regime exits working?) |
| **beyond −30%** | **breach** — well past anything backtested | **halt**: stop promotion to live / cut live size; treat the edge as unproven until explained |

Drawdown is the **fastest** real signal (you don't need 30 trades to see a −30% drop), so
it gets a hard line even when the trade count is still too low for a PF verdict.

> **Decision (b) — risk sizing — RESOLVED 2026-05-24: keep 0.6%.** Per-position risk (0.6%)
> sets the *amplitude* of drawdown, not the edge: the audit confirms PF/Sharpe are ~flat
> across 0.4–1.0% while return & drawdown scale. Cutting **0.6%→0.4%** would re-seat the
> backtest DD to ≈−19% (under the §9 25% line) at the cost of return (≈+72% vs +117%) — a pure
> drawdown/return tradeoff, **not** an edge improvement. **We deliberately chose 0.6%** — the
> fuller-return side — and **accept the ≈−25.6% backtested max DD and that live DD may run
> somewhat past it** without auto-intervening (the bands above govern when to act). No config
> change. See `EXPERIMENTS.md` + risk-sweep in `S1_ROBUSTNESS.md` §5.

---

## 4. Behavioural tripwires (these need NO minimum sample — a breach is a *bug*, not noise)

These check the machinery, not the luck. Any failure here is investigated immediately,
regardless of trade count.

- **Regime → cash.** When BTC regime is **OFF** (price < 100d MA or 50d MA < 100d MA), S1
  must open **no new** positions and bleed existing ones down to cash via stops/Donchian
  exits. If S1 opens a *fresh* breakout while regime is off → **bug**, fix before trusting
  any numbers. This is the capital-preservation safety net the whole §9 thesis rests on.
- **Long flat stretches are EXPECTED, not failure.** Weeks/months with zero trades during
  bear/chop are the design working (it sits in cash). Do **not** "fix" quiet periods by
  loosening entries — that is exactly the pullback experiment (E2) that failed.
- **Stops fire.** Every open position must carry a stop (entry − 2·ATR). A position that
  rides far below its stop without exiting = **bug**.
- **≤ 5 concurrent positions, ≤ 50% deployed.** If the book exceeds either, the
  portfolio constraints are broken = **bug**.
- **Trade cadence sanity.** ~16/yr *on average*, bursty. A whole **bull** market (regime
  on for months) with near-zero entries would be suspect (signal/universe wiring); a quiet
  **bear** is not.

---

## 5. What is explicitly NOT a tripwire (do not act on these)

- One or two losing trades in a row. (Win rate is < 50% by design; the edge is in payoff.)
- A single month of negative return.
- PF/Sharpe wobble under 30 closed trades.
- No trades for a few months while the regime is off.
- Live trailing backtest's 2.23 — it *should* trail. Only a *collapse* (§2) matters.

---

## 6. Quick decision table

| observation | trades so far | verdict |
|---|---|---|
| equity drifting, few trades, regime off | any | **fine** — preserving capital |
| DD −12%, PF noisy | < 30 | **fine** — too early to read PF |
| DD −22% | any | **review** — past backtest worst; rule out a bug |
| DD −27% | any | **halt** — §9 breach; don't scale to live |
| PF 1.4 over 40 trades | ≥ 30 | **keep running** — softer but real |
| PF 0.8 over 35 trades | ≥ 30 | **stop trusting** — edge not appearing live |
| opens a new long while regime OFF | any | **bug** — fix immediately |
| 6 concurrent positions | any | **bug** — constraint broken |

---

## 7. Cadence & scope

- **Check cadence:** the daily paper run already updates the record; a *weekly* glance at
  the dashboard is enough. Daily P&L is noise.
- **Formal review:** at **30 closed trades**, and thereafter every ~25 trades or any §3/§4
  breach.
- **Scope:** S1 only. This is a **hold** — no new strategy, no parameter changes to S1.
  Any change to the system requires a fresh pre-registered spec and explicit go-ahead
  (same discipline as E1–E3 / S3). Monitoring observes; it does not tune.

*All thresholds above were fixed before any live data accumulated. They are not to be
loosened to keep S1 alive, nor tightened to kill it — only acted on as written.*
