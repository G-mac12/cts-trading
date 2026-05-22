# CTS — Crypto Trading System
## Build Spec v1.0

**Owner:** Grant MacMillan (personal)
**Status:** Specification complete — ready for Phase 1
**Relationship to GTS:** Independent system. Separate codebase, repo, runtime, account. Reuses GTS *infrastructure patterns*, not GTS strategy logic.
**Working name:** CTS (rename at will).

> Changelog v0.2 → v1.0: All five decisions LOCKED. Real risk numbers plugged in (§10) from the £2,000 simulation balance. New §0 "Training / no-real-money guarantees" added to make the no-real-trades design unmissable. Spec is now complete enough to begin Phase 1 (the data-and-backtest go/no-go gate) and to hand to Claude Code.

---

## 0. Training / no-real-money guarantees (read first)

CTS is built to run **without placing a single real trade** until a deliberate, explicit go-live decision at Phase 7. This is enforced three ways, not just by intent:

1. **Read-only API key during all training.** The Kraken key used through Phases 1–6 has query/market-data/balance permissions only — **no trade permission, no withdrawal permission.** Even a bug that tried to fire an order physically cannot place one. Trade permission is added to a *separate* key only at the paper→live crossing.
2. **Two stacked no-money stages before any live capital:**
   - **Backtest (Phase 1)** — strategy run against *historical* data. No connection to live orders at all.
   - **Self-hosted paper (Phase 3)** — full real logic against *live* Kraken data, but fills routed to a **simulator**, not the exchange. Records to `crypto_paper_trades`. No real orders.
3. **The £2,000 balance is a SIMULATION INPUT, not a deposit.** It is the equity figure the sizing engine takes its percentages from (see §10). No money is deposited to Kraken until Phase 7. You can re-run backtests at any balance to see how viability shifts; it's a planning parameter, freely changeable.

> The one thing crypto does NOT give us that GTS got free from IBKR: a broker-provided paper sandbox. We build the fill simulator ourselves (§8). Training results are only as trustworthy as that simulator — which is why realistic fill/slippage/fee modelling is mandatory, not optional.

---

## 1. Purpose & thesis

Automated, systematic **long-only spot** crypto bot for a UK personal operator, validated to GTS standard (backtest → self-hosted paper → live), reusing GTS execution/orchestration/reporting infrastructure where it transfers.

**The edge:** persistent short-to-medium-term price momentum in crypto — a documented, peer-reviewed anomaly. Strongest-performing assets over a recent lookback tend to keep outperforming over the subsequent short horizon; breakout-based trend capture (Turtle) has a decades-long cross-asset record. We *implement and validate* a known edge, exactly as GTS implements Cameron's Gap-and-Go.

**Success definition:** see §11. No live capital until validation gates clear.

---

## 2. Hard constraints (LOCKED)

- **Spot only.** No derivatives (futures, options, CFDs, perps) — FCA-banned for UK retail since Jan 2021.
- **Long only.** No shorting. "Risk-off" = exit to stablecoin (cash).
- **No leverage.** Settled spot balance only. No margin/buying-power/PDT. (Kraken offers up to 5x on some pairs — **do not enable**; outside legal scope.)
- **Venue:** Kraken Pro API (Decision 2). UK-registered, REST + WebSocket v2, full order types.
- **Account holder:** Grant MacMillan, **personal** (Decision 3). Not Sky GMAC. Keeps CTS cleanly separate from GTS.

---

## 3. Strategy — core engine

### 3.1 Primary engine: Daily Turtle / Donchian breakout (Decision 1 — LOCKED)

**Entry (long):**
- Close above the **N-day high** (Donchian upper band). Start: **N = 20** (System 1) + **N = 55** (System 2) in parallel for backtest comparison.
- **Volume:** breakout-bar volume ≥ 1.5× trailing 20-bar average (RVOL ≥ 1.5).
- **Regime risk-on** (§3.3) required.
- **Cross-sectional gate:** coin in top tier of §3.2 ranking.

**Sizing (ATR / Turtle):**
- `Units = (Equity × Risk%) / (ATR-based stop distance)`
- Risk per position: **1% of equity**. ATR period **14**.

**Stop:** initial hard stop **2 × ATR** below entry. Volatility-scaled — NOT a fixed cash amount. Do not transplant GTS's $0.03 logic (crypto moves 5–10× equities).

**Exit:** close below **10-day low** (System 1) / **20-day low** (System 2), OR stop, whichever first. **No pyramiding in v1.**

**Timeframe:** daily candles, anchored **00:00 UTC**. Swing system, holds days–weeks. Low-touch (once-a-day check), which fits running alongside a now-low-maintenance GTS.

### 3.2 Universe selection: cross-sectional momentum

- Rank eligible universe (§4) by **30-day return**.
- Re-evaluate eligible set every **7 days** (stable band: 15–35d lookback, 7d rebalance).
- Engine only fires in coins in the **top tier**.

### 3.3 Regime filter (master switch — Decision 5 LOCKED, tune in backtest)

- **Risk-on:** BTC above its **100-day MA** AND **50-day MA above 100-day MA.**
- **Risk-off:** no new entries; open positions still managed by their exits; idle capital in stablecoin.
- Highest-leverage parameter — locked as the *starting* definition; expect heavy tuning.

### 3.4 Deferred to Phase 2

- **Intraday ORB** — least track-recorded engine AND worst fit for the fee floor (§3.5). Add as a parallel strategy only after the daily core validates.
- Pyramiding / unit scaling. Sentiment / on-chain signals.

### 3.5 Fee economics (why daily)

Kraken Pro maker/taker (LOCKED to Pro, not the ~0.99% standard app):
- Entry tier **0.25% maker / 0.40% taker**, stepping down with 30-day volume.
- Breakout entry crosses the band → **takes liquidity → taker fee.** Round trip ≈ **0.8%** before slippage.
- **Decisive for Decision 1:** negligible against the daily system's 30–50% target moves; fatal against 1–2% intraday moves.
- Fees are percentage-based → the 0.8% drag is identical at £2k or £200k. Small account is not penalised on fees, only smaller in absolute pounds.
- **Execution:** model **taker fees on entry** in backtest/sim. Exits via resting limit orders *may* earn maker rate — model both, never let maker assumptions flatter the entry.

---

## 4. Universe & eligibility filters

| Filter | Start value | Rationale |
|---|---|---|
| Venue | Kraken pairs only | Locked |
| Min 24h USD volume | ≥ $50M | Liquidity — avoids manipulation-prone thin coins |
| Max spread | ≤ 0.3% | Execution quality |
| Exclude | Stablecoins, wrapped, leveraged tokens | Not tradable signal |
| Universe size cap | Top ~30–50 by eligibility | Tractable & liquid |
| Min listing age | ≥ 90 days clean data | Avoid new-listing noise & backtest gaps |
| Quote currency | USD/USDT pairs on Kraken | Consistent sizing & stablecoin parking |

---

## 5. Scoring model

Composite 0–100, gating entries (GTS 75+ discipline):

- **Cross-sectional rank** — highest weight.
- **Breakout strength** (distance/cleanliness above band).
- **Volume** (RVOL).
- **Trend quality** (ADX or MA alignment).
- **Net-of-fee expectancy gate:** candidate whose projected move doesn't comfortably clear ~0.8% round-trip + slippage is scored down. (Fee floor lives in the scorer, not just the backtest.)
- **Regime alignment** — binary; risk-off floors score to 0.

Entry threshold: start **75**, tune. AUTO threshold as GTS.

---

## 6. Architecture

### 6.1 Reuse from GTS (plumbing — transfers)

- Orchestration/scheduler (adapted to 24/7, §10).
- Subagent architecture.
- **Executor discipline:** fill-driven state machine, explicit SUBMITTED→FILLED/REJECTED→CLOSED, rejection handling. (GTS-weekend **margin gate is N/A** — spot has no margin — but fill-driven promotion + rejection classification transfer wholesale and are mandatory here.)
- Supabase (new tables: `crypto_paper_trades`, `crypto_universe`, `crypto_signals`).
- Dashboard (Next.js/Vercel) — fork GTS.
- Telegram + Resend reporting. Droplet hosting.

### 6.2 Build new

- Kraken connector (§7), REST + WebSocket v2, Pro endpoints.
- Data layer (§7).
- Self-hosted paper shim (§8).
- Strategy engine (§3) — no GTS strategy code transfers.
- 24/7 operation & autonomous recovery (§10).

### 6.3 Subagents (mirror GTS 7-agent pattern)

1. **Orchestrator/CEO** — session state, reconciliation, halt authority.
2. **Universe selector** — eligibility + cross-sectional ranking (7d rebalance).
3. **Scorer** — composite score + net-of-fee gate.
4. **Regime monitor** — master risk-on/off.
5. **Executor** — submission, fill-driven state machine, rejection handling.
6. **Position monitor** — ATR stop, Donchian exit.
7. **Reporter** — Telegram + Resend, dashboard.

---

## 7. Infrastructure

| Component | Choice | Notes |
|---|---|---|
| **Exchange** | **Kraken Pro** (LOCKED) | Personal. Pro API/fees, NOT standard app. |
| **Price data (live)** | Kraken WebSocket v2 + CoinGecko/CoinAPI (secondary) | Push, sub-second |
| **Backtest data** | CoinDesk API (ex-CryptoCompare) or CoinAPI | Tick-level, survivorship-clean. **NEW SIGN-UP REQUIRED.** |
| **News (Phase 2, optional)** | CoinGecko / Benzinga | Crypto catalysts ≠ equity; logic rebuild needed |
| **Hosting** | DigitalOcean droplet | 24/7 critical |
| **Database** | Supabase | New crypto-prefixed tables |
| **Inference** | Groq / Alibaba failover | Reuse pattern. **All strategy/execution math = deterministic code, never inference.** |

**Kraken account actions (one-time, existing personal account):**
- Verify to **Intermediate+** (≈15 min, gov ID + selfie, **desktop only**). Starter's ~$2,500/day cap throttles funding/API.
- API keys **read-only first** (NO trade, NO withdraw). Separate trade key only at paper→live. **Never enable withdrawal on a bot key.** IP-allowlist to droplet.
- Confirm GBP rail (personal bank → Kraken) with a small test deposit — UK banks vary on crypto transfers. (This is the only place real money moves before Phase 7, and it's just to prove the rail — withdraw it back if you like.)

---

## 8. Self-hosted paper-trading layer

- Full real logic against **live Kraken WebSocket data**; fills → **simulator**, not exchange.
- **Realistic fill modelling mandatory:** spread, slippage, partial fills, Pro **taker fee on entry** (§3.5).
- Sim-vs-real gap is *wider* in crypto than equities; optimistic modelling overstates results badly.
- All sim trades → `crypto_paper_trades`, GTS schema discipline.

---

## 9. Backtesting plan

- **Data:** tick/second-level only; never aggregated snapshots for entry logic.
- **Walk-forward, out-of-sample mandatory.** No tuning on full history.
- **Survivorship bias:** dataset MUST include delisted/failed coins. Source a survivorship-clean universe explicitly.
- **Costs at Kraken Pro taker rate on entry** (0.40% start) + slippage. Maker only where a resting exit genuinely earns it.
- **Regime decomposition:** report bull / bear / chop separately. Must show it goes to cash and survives bear/chop.
- **Short clean history (<5yr)** → overfitting more dangerous than GTS's 5-yr equity backtests. Distrust single runs; demand robustness across subsamples and parameter neighbourhoods.

**Minimum acceptance (start, tune):** profit factor > 1.5 *after Pro fees*, max drawdown < 25%, positive OOS Sharpe, controlled bear/chop performance.

---

## 10. Risk management (real numbers — £2,000 simulation balance, Decision 4 LOCKED)

- **Simulation/start balance: £2,000** (simulation input per §0, also the intended Phase-7 small live size).
- **Per-position risk: 1% = £20.**
- **Max concurrent positions: 5.**
- **Max deployed: 50% = £1,000** working (~£200/position avg), rest in stablecoin.
- **Worst-case all-5-stops-hit ≈ £100 (5% of equity)** — the portfolio-risk ceiling per cycle.
- ATR/fractional sizing: a ~£200 position is fine on Kraken (fractional buys); no minimum-order issues at this size.
- **Daily & weekly loss limits** → auto-halt to cash.
- **Regime filter** (§3.3) is the master switch.
- **24/7 autonomous recovery mandatory** — runs unattended overnight. Connection-loss, restart, reconciliation must be robust. **Higher bar than GTS has cleared even for equities — first-class build task.**

> All limits are percentage-based, so funding more later scales the whole system without changing strategy logic. £2k proves the edge; it does not constrain eventual scale.

---

## 11. Validation gates → go-live

No live capital until ALL of:

1. **Backtest** clears §9 (after Pro fees), walk-forward, survivorship-clean.
2. **Self-hosted paper** ≥ **100 trades** on live data; sim-vs-would-be-real fill+fee reconciliation within acceptable divergence.
3. **Regime behaviour confirmed:** demonstrably went to cash in an observed risk-off period in paper.
4. **24/7 stability:** unattended run ~30 days, no unrecovered failures.
5. **Manual review** of paper equity curve, drawdown sequencing, sample trades.

Then: live at **£2,000 small fixed size**; scale only after live matches paper.

---

## 12. Funding mechanics (per trade)

- Pre-fund (Phase 7 only): personal bank GBP → GBP on Kraken → stablecoin float.
- Each trade = spot cash-for-coin, settles ~instantly, recycles immediately. No PDT, no T+1, no buying-power gate.
- Friction = GBP↔crypto conversion spread + Kraken withdrawal limits (tier-dependent), not settlement timing.

**Personal tax / record-keeping:** profits are personal, likely UK CGT territory (frequent automated trading can raise trading-income questions). Not advice — brief accountant conversation once realised gains exist. Build implication: log every trade's entry/exit/fee cleanly (trade table already does this).

---

## 13. Decisions — all LOCKED

- **[D1] Engine timeframe** → daily Turtle/Donchian.
- **[D2] Exchange** → Kraken Pro, personal.
- **[D3] Personal vs company** → personal.
- **[D4] Capital & sizing** → £2,000 sim balance, 5 max positions, 50% max deployed.
- **[D5] Regime filter** → BTC > 100d MA AND 50d MA > 100d MA (starting definition, tune in backtest).

---

## 14. Build sequencing

**Phase 0 — Spec (this doc).** Complete.
**Phase 1 — Data & backtest harness + Kraken account prep.** Read-only connector; Intermediate verification; backtest-data sign-up + ingest; survivorship-clean universe; backtest engine. **GO/NO-GO GATE — prove the edge before building the machine.**
**Phase 2 — Strategy engine.** Implement §3; tune; clear §9 (after-fee).
**Phase 3 — Paper layer.** Self-hosted shim (§8), live data, realistic fill+fee modelling. Fork GTS executor/state-machine discipline.
**Phase 4 — Orchestration & subagents.** Wire §6.3, regime monitor, reporting, dashboard fork.
**Phase 5 — 24/7 hardening.** Autonomous recovery, unattended-run validation.
**Phase 6 — Validation.** Clear §11 gates.
**Phase 7 — Live (small).** £2,000 fixed size; scale on live-matches-paper.

> The discipline that got GTS this far is unchanged: **prove the edge in backtest before building the machine to scale it.** Phase 1 is the go/no-go — if the momentum edge doesn't survive survivorship-clean, after-fee, walk-forward testing, the project stops there, cheaply, before any infrastructure is built.

---

*v1.0 — all decisions locked. Ready for Phase 1.*
