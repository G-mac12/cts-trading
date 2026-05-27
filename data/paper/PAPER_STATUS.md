# CTS Paper Trading — status

_As of 2026-05-26 · paper started 2026-05-22 · source coinapi · 341 coins_

> SIMULATED ONLY — no real orders, no real money. Fills modelled with Kraken Pro taker fees + conservative slippage.

**Forward track:** 2026-05-22 → 2026-05-26

| Variant | Fwd return | Fwd trades | Profit factor | Max DD | Equity (USD) | Open |
|---|---|---|---|---|---|---|
| S1-baseline | -0.4% | 0 | 0.00 | -0.4% | 2530 | 1 |
| S1-chopfix | -0.4% | 0 | 0.00 | -0.4% | 2530 | 1 |

**S1-baseline — open positions:**
  - NEAR since 2026-05-26 @ 2.77105 (mark 2.548, stop 2.399203, 40.9845 units)
**S1-chopfix — open positions:**
  - NEAR since 2026-05-26 @ 2.77105 (mark 2.548, stop 2.399203, 40.9845 units)

Run `python scripts/run_paper.py --update` daily to extend the forward record.