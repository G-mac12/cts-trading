"""Plain-language paper-trading status report."""
from __future__ import annotations

from typing import Dict


def _pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def render_paper(report: Dict) -> str:
    L = []
    L.append("# CTS Paper Trading — status\n")
    L.append(f"_As of {report['as_of']} · paper started {report['paper_start']} · "
             f"source {report['data_source']} · {report['universe_symbols']} coins_\n")
    L.append("> SIMULATED ONLY — no real orders, no real money. Fills modelled with Kraken Pro "
             "taker fees + conservative slippage.\n")

    days_live = "first run (flat start)" if report["paper_start"] == report["as_of"] else \
                f"{report['paper_start']} → {report['as_of']}"
    L.append(f"**Forward track:** {days_live}\n")

    L.append("| Variant | Fwd return | Fwd trades | Profit factor | Max DD | Equity (USD) | Open |")
    L.append("|---|---|---|---|---|---|---|")
    for name, v in report["variants"].items():
        m = v["forward_metrics"]
        pf = m["profit_factor"]
        pf_s = "inf" if pf == float("inf") else f"{pf:.2f}"
        L.append(f"| {name} | {_pct(m['total_return'])} | {int(v['n_forward_trades'])} | {pf_s} | "
                 f"{_pct(m['max_drawdown'])} | {v['equity_last']:.0f} | {len(v['open_positions'])} |")
    L.append("")

    for name, v in report["variants"].items():
        if v["open_positions"]:
            L.append(f"**{name} — open positions:**")
            for p in v["open_positions"]:
                L.append(f"  - {p['symbol']} since {p['entry_date']} @ {p['entry_price']} "
                         f"(mark {p['mark']}, stop {p['stop']}, {p['units']:.4f} units)")
        nxt = v["next_session_orders"]
        if nxt.get("entries") or nxt.get("exits"):
            L.append(f"**{name} — planned next session:** "
                     f"buy {nxt.get('entries') or '—'} · sell {list((nxt.get('exits') or {}).keys()) or '—'}")
    if not any(v["open_positions"] or v["next_session_orders"].get("entries") or
               v["next_session_orders"].get("exits") for v in report["variants"].values()):
        L.append("_No open positions and nothing queued for next session yet — the strategy is in cash, "
                 "waiting for a risk-on breakout._")
    L.append("")
    L.append("Run `python scripts/run_paper.py --update` daily to extend the forward record.")
    return "\n".join(L)
