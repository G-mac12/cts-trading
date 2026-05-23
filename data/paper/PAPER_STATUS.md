# CTS Paper Trading — status

_As of 2026-05-22 · paper started 2026-05-22 · source coinapi · 157 coins_

> SIMULATED ONLY — no real orders, no real money. Fills modelled with Kraken Pro taker fees + conservative slippage.

**Forward track:** first run (flat start)

| Variant | Fwd return | Fwd trades | Profit factor | Max DD | Equity (USD) | Open |
|---|---|---|---|---|---|---|
| S1-baseline | 0.0% | 0 | 0.00 | 0.0% | 2540 | 0 |
| S1-chopfix | 0.0% | 0 | 0.00 | 0.0% | 2540 | 0 |

_No open positions and nothing queued for next session yet — the strategy is in cash, waiting for a risk-on breakout._

Run `python scripts/run_paper.py --update` daily to extend the forward record.