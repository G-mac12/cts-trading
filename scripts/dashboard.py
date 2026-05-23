#!/usr/bin/env python
"""Build a single self-contained dashboard (docs/index.html) to track the system —
backtest evidence + the live paper record. No external libraries, no cloud; just
open the file in a browser. SIMULATED — no real money.

  python scripts/dashboard.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from cts.config import ROOT
from cts.reporting.findings import evaluate_gate

COLOURS = ["#58a6ff", "#3fb950", "#d29922", "#bc8cff"]


def _pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def _num(x, dp=2):
    if x is None:
        return "—"
    if isinstance(x, float) and x == float("inf"):
        return "∞"
    return f"{x:.{dp}f}"


def _load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def _equity_series(path: Path):
    """{variant: [(as_of, equity), ...]} from the long-format run log."""
    if not path.exists():
        return {}
    out: dict = {}
    for row in csv.DictReader(path.open()):
        v, a, e = row.get("variant"), row.get("as_of"), row.get("equity")
        if not v or not a or not e:
            continue
        try:
            out.setdefault(v, []).append((a, float(e)))
        except ValueError:
            continue
    for v in out:
        # one point per as_of (keep last), sorted
        seen = {}
        for a, e in out[v]:
            seen[a] = e
        out[v] = sorted(seen.items())
    return out


def _equity_chart(series: dict, inception: float) -> str:
    if not series or all(len(v) < 1 for v in series.values()):
        return "<p class='note'>Equity curve will appear here once the paper record has a few days.</p>"
    dates = sorted({a for pts in series.values() for a, _ in pts})
    xi = {d: i for i, d in enumerate(dates)}
    vals = [e for pts in series.values() for _, e in pts] + [inception]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 1.0)
    W, H, padx, pady = 640, 220, 50, 20
    def X(d):
        return padx + (xi[d] / max(len(dates) - 1, 1)) * (W - padx - 10)
    def Y(e):
        return H - pady - (e - lo) / span * (H - 2 * pady)
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:680px">']
    # inception baseline
    y0 = Y(inception)
    parts.append(f'<line x1="{padx}" y1="{y0:.0f}" x2="{W-10}" y2="{y0:.0f}" stroke="#30363d" stroke-dasharray="4"/>')
    parts.append(f'<text x="{padx-6}" y="{y0:.0f}" fill="#8b949e" font-size="10" text-anchor="end">{inception:.0f}</text>')
    parts.append(f'<text x="{padx-6}" y="{Y(hi):.0f}" fill="#8b949e" font-size="10" text-anchor="end">{hi:.0f}</text>')
    legend = []
    for i, (v, pts) in enumerate(sorted(series.items())):
        c = COLOURS[i % len(COLOURS)]
        if len(pts) == 1:
            d, e = pts[0]
            parts.append(f'<circle cx="{X(d):.0f}" cy="{Y(e):.0f}" r="3" fill="{c}"/>')
        else:
            poly = " ".join(f"{X(d):.0f},{Y(e):.0f}" for d, e in pts)
            parts.append(f'<polyline points="{poly}" fill="none" stroke="{c}" stroke-width="2"/>')
        legend.append(f'<span style="color:{c}">■</span> {v}')
    parts.append(f'<text x="{padx}" y="{H-4}" fill="#8b949e" font-size="10">{dates[0]}</text>')
    parts.append(f'<text x="{W-10}" y="{H-4}" fill="#8b949e" font-size="10" text-anchor="end">{dates[-1]}</text>')
    parts.append("</svg>")
    return "".join(parts) + '<div class="note">' + " &nbsp; ".join(legend) + "</div>"


def _card(label, value, ok=None):
    badge = "" if ok is None else f'<span class="b {"ok" if ok else "no"}">{"PASS" if ok else "FAIL"}</span>'
    return f'<div class="card"><div class="lab">{label}</div><div class="val">{value}{badge}</div></div>'


def build_html(analysis, paper, equity) -> str:
    P = [_HEAD, "<h1>CTS Dashboard</h1>"]
    if paper:
        P.append(f"<p class='sub'>Paper started {paper['paper_start']} · as of {paper['as_of']} · "
                 f"{paper['universe_symbols']} coins · SIMULATED — no real money</p>")
        # regime banner
        on = paper.get("regime_on", False)
        P.append(f'<div class="banner {"on" if on else "off"}">Market regime: '
                 f'{"RISK-ON — eligible to trade" if on else "RISK-OFF — staying in cash"}</div>')

        # equity curve
        P.append("<h2>Paper equity (forward, simulated)</h2>")
        P.append(_equity_chart(equity, paper.get("inception_equity_usd", 0)))

        # per-variant cards + positions + trades
        for vn, v in paper["variants"].items():
            m = v["forward_metrics"]
            P.append(f"<h2>{vn}</h2><div class='cards'>")
            P.append(_card("Equity (USD)", f"{v['equity_last']:.0f}"))
            P.append(_card("Fwd return", _pct(m["total_return"])))
            P.append(_card("Trades", str(int(v["n_forward_trades"]))))
            P.append(_card("Profit factor", _num(m["profit_factor"])))
            P.append(_card("Max DD", _pct(m["max_drawdown"])))
            P.append(_card("Open", str(len(v["open_positions"]))))
            P.append("</div>")
            if v["open_positions"]:
                P.append("<table><tr><th>Holding</th><th>Since</th><th>Entry</th><th>Mark</th><th>Stop</th></tr>")
                for p in v["open_positions"]:
                    P.append(f"<tr><td>{p['symbol']}</td><td>{p['entry_date']}</td><td>{p['entry_price']}</td>"
                             f"<td>{p['mark']}</td><td>{p['stop']}</td></tr>")
                P.append("</table>")
            if v.get("trades"):
                P.append("<details><summary>Trade log ({} closed)</summary><table>".format(len(v["trades"])))
                P.append("<tr><th>Coin</th><th>In</th><th>Out</th><th>Return</th><th>P&L</th><th>Why</th></tr>")
                for t in v["trades"][-25:]:
                    P.append(f"<tr><td>{t['symbol']}</td><td>{t['entry_date']}</td><td>{t['exit_date']}</td>"
                             f"<td>{_pct(t['return_pct'])}</td><td>{t['net_pnl']}</td><td>{t['reason']}</td></tr>")
                P.append("</table></details>")
            nxt = v.get("next_session_orders", {})
            if nxt.get("entries") or nxt.get("exits"):
                P.append(f"<p class='note'>Planned next session — buy: {nxt.get('entries') or '—'} · "
                         f"sell: {nxt.get('exits') or '—'}</p>")

        wl = paper.get("watchlist", [])
        P.append("<h2>Watchlist (top-tier coins being scanned)</h2>")
        P.append(f"<p class='note'>{', '.join(wl) if wl else '—'}</p>")
    else:
        P.append("<p class='note'>No paper run yet. Run <code>python scripts/run_paper.py</code>.</p>")

    # backtest reference
    if analysis:
        P.append("<h2>Validated edge (backtest reference)</h2>")
        P.append(f"<p class='sub'>{analysis['window'][0]} → {analysis['window'][1]} · after fees · out-of-sample</p>")
        for name, s in analysis["systems"].items():
            g = evaluate_gate(s, analysis["acceptance"]); h = s["headline"]
            P.append(f"<h3>System {name}</h3><div class='cards'>")
            P.append(_card("Profit factor", _num(h["profit_factor"]), g["pf_ok"]))
            P.append(_card("Max drawdown", _pct(h["max_drawdown"]), g["dd_ok"]))
            P.append(_card("Sharpe", _num(h["sharpe"]), g["sharpe_ok"]))
            P.append(_card("Trades", str(int(h["trade_count"])), g["enough_trades"]))
            P.append(_card("Robust (subsample PF)", _num(g["sub_median"]), not g["universe_fragile"]))
            P.append("</div>")
            b = s["benchmark"]
            P.append(f"<p class='note'>Buy &amp; hold BTC: {_pct(b['total_return'])} return, "
                     f"{_pct(b['max_drawdown'])} max DD.</p>")
    P.append(f"<p class='note' style='margin-top:24px'>Generated {paper['generated_at'] if paper else ''} · "
             "auto-refreshes daily via GitHub Actions.</p></body></html>")
    return "".join(P)


_HEAD = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CTS Dashboard</title><style>
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0d1117;color:#c9d1d9;margin:0;padding:20px;max-width:760px}
h1{margin:0 0 2px}h2{margin:26px 0 10px;border-bottom:1px solid #30363d;padding-bottom:6px;font-size:17px}
h3{margin:14px 0 6px;font-size:14px;color:#c9d1d9}.sub{color:#8b949e;margin:0 0 10px;font-size:13px}
.note{color:#8b949e;font-size:13px}
.banner{padding:10px 14px;border-radius:8px;font-weight:600;margin:10px 0}
.banner.on{background:#193b1f;color:#3fb950}.banner.off{background:#3b2a19;color:#d29922}
.cards{display:flex;flex-wrap:wrap;gap:8px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:8px 12px;min-width:96px}
.lab{color:#8b949e;font-size:11px}.val{font-size:18px;font-weight:600;margin-top:2px}
.b{font-size:9px;padding:1px 5px;border-radius:9px;margin-left:6px;vertical-align:middle}
.ok{background:#193b1f;color:#3fb950}.no{background:#3b1919;color:#f85149}
table{border-collapse:collapse;margin:8px 0;width:100%}
th,td{border:1px solid #30363d;padding:5px 9px;text-align:left;font-size:12px}
th{color:#8b949e;font-weight:500}code{background:#161b22;padding:2px 5px;border-radius:4px}
details summary{cursor:pointer;color:#8b949e;font-size:13px;margin:6px 0}
</style></head><body>"""


def main() -> None:
    analysis = _load(ROOT / "data" / "analysis.json")
    paper = _load(ROOT / "data" / "paper" / "paper_snapshot.json")
    equity = _equity_series(ROOT / "data" / "paper" / "paper_runs.csv")
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(analysis, paper, equity))
    print(f"Wrote {out} — open it in a browser.")


if __name__ == "__main__":
    main()
