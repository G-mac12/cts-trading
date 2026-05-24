# CTS — System Overview (current state)

_A single-page map of the whole system, for brainstorming and onboarding. Pairs with
`PLAN.md` (original design), `FINDINGS.md` (the go/no-go verdict), and `EXPERIMENTS.md`
(post-gate tuning experiments)._

## What it is
A long-only **spot crypto** momentum system for a UK personal **Kraken Pro** account.
Daily **Donchian/Turtle breakout** + cross-sectional momentum + a BTC regime filter.
Status: **validated in backtest, now paper-trading itself in the cloud. No real money.**

## Current strategy (the adopted baseline — System 1)
- **Entry:** close > prior 20-day high (Donchian), with RVOL ≥ 1.5, only in top-tier
  coins by 30-day return, only when regime is risk-on.
- **Regime filter (master switch):** BTC > 100-day MA AND 50-day MA > 100-day MA.
  Risk-off ⇒ no new entries; idle = cash.
- **Sizing:** 0.6% equity risk per position, stop = 2× ATR(14). Max 5 positions, ≤50% deployed.
- **Exit:** close < 10-day low, or the stop — whichever first.
- **Universe:** Kraken USD/USDT spot, ≥ $1M/day volume (account-appropriate for £2k),
  stablecoins/wrapped/leveraged excluded. ~157 coins ingested incl. delisted (survivorship-clean).
- **Costs modelled:** Kraken Pro taker fee on entry (~0.4%), conservative slippage.
- System 2 (N=55/20) was tested and **retired** (drawdown too high — see EXPERIMENTS E3).

## Validation status (backtest, 2018–2026, out-of-sample, after fees)
S1: profit factor **2.56**, max drawdown **−20.5%**, Sharpe **0.78**, **117 trades**,
robust to universe subsampling (median PF 2.66). Verdict: **QUALIFIED** — clears every
hard criterion; the one open weakness is **chop give-back** (~−22% over choppy days),
which the paper "chop-fix" variant is testing forward. Full detail in `FINDINGS.md`.

## What's running right now (hands-off)
- **GitHub Actions** runs the paper-trader daily (00:30 UTC), SIMULATED — no real orders.
  It pulls fresh prices, runs two variants (S1 baseline + S1 "chop-fix"), updates the
  record, rebuilds the dashboard, and commits it back.
- **Live dashboard:** https://g-mac12.github.io/cts-trading/ (auto-refreshes).
- Data source: **CoinAPI** (key stored as a GitHub secret, never in the repo).

## Map of the code
- `src/cts/indicators.py` — Donchian, ATR, RVOL, MAs (pure functions).
- `src/cts/strategy/` — regime, ranking, signals (breakout + pullback), sizing, exits.
- `src/cts/data/` — pluggable adapter (CoinAPI), cache, point-in-time universe builder.
- `src/cts/engine/` — fees, slippage, portfolio, event-driven daily backtest, walk-forward.
- `src/cts/metrics/` — performance, regime decomposition, robustness, BTC benchmark.
- `src/cts/paper/` — the live paper-trader; `scripts/` — ingest, backtest, paper, dashboard.
- `tests/` — 42 unit tests (hand-computed fixtures, no-lookahead, end-to-end).

## Hard rules (do not break)
- Spot only, **no leverage, no shorting, no derivatives** (UK FCA).
- **No real orders** until a deliberate go-live (still simulated). Read-only/market data only.
- **No LLM in the strategy/backtest math** — all deterministic code.
- **Isolated from GTS** (Grant's equities system) — shares no code/data/infra.
- Secrets in `.env` / GitHub secrets, never committed. Times in UTC.

## Open questions / good brainstorm topics
1. **Chop give-back** — does the "chop-fix" (exit on regime flip) actually help on live
   data? Or a better de-risking rule? (No more backtest tuning — judge it forward.)
2. **Trade frequency** — ~14/yr is intrinsic to daily spot + regime gating. Worth it, or
   rethink? (Pullback entries were tried and failed — EXPERIMENTS E2.)
3. **Path to live** — what must the paper record show before risking real £2k? (See §11 of the spec.)
4. When to move off GitHub Actions to a real always-on server (droplet kit is in `deploy/`).

## How to go live later (gated — not yet)
Paper must clear the spec's §11 gates (enough trades, regime behaviour confirmed, stability),
then a Kraken **read-only → trade** key, small fixed £2k size. Deliberate decision only.
