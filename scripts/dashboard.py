#!/usr/bin/env python
"""Generate a single self-contained HTML dashboard from the backtest results
(data/analysis.json) and the paper-trading snapshot (data/paper/paper_snapshot.json).
No external libraries, no cloud — just open data/dashboard.html in a browser.

  python scripts/dashboard.py
"""
from __future__ import annotations

import json
from pathlib import Path

from cts.config import ROOT
from cts.reporting.findings import evaluate_gate


def _pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def _num(x, dp=2):
    if x is None:
        return "—"
    if isinstance(x, float) and x == float("inf"):
        return "∞"
    return f"{x:.{dp}f}"


def _fold_bars(per_fold):
    if not per_fold:
        return ""
    rets = [f["metrics"]["total_return"] for f in per_fold]
    hi = max(0.01, max(abs(r) for r in rets))
    w, gap, mid = 18, 6, 40
    bars = []
    for i, r in enumerate(rets):
        h = abs(r) / hi * 34
        y = mid - h if r >= 0 else mid
        colour = "#3fb950" if r >= 0 else "#f85149"
        x = i * (w + gap)
        bars.append(f'<rect x="{x}" y="{y:.0f}" width="{w}" height="{h:.0f}" fill="{colour}"/>')
    width = len(rets) * (w + gap)
    return (f'<svg width="{width}" height="80"><line x1="0" y1="{mid}" x2="{width}" y2="{mid}" '
            f'stroke="#30363d"/>{"".join(bars)}</svg>')


def _card(label, value, ok=None):
    badge = "" if ok is None else f'<span class="b {"ok" if ok else "no"}">{"PASS" if ok else "FAIL"}</span>'
    return f'<div class="card"><div class="lab">{label}</div><div class="val">{value}{badge}</div></div>'


def build_html(analysis: dict, paper: dict | None) -> str:
    acc = analysis["acceptance"]
    parts = [_HEAD]
    parts.append(f"<h1>CTS Dashboard</h1><p class='sub'>Backtest window {analysis['window'][0]} → "
                 f"{analysis['window'][1]} · source {analysis['source']} · "
                 f"{analysis['universe']['symbols_traded']} coins · SIMULATED, no real money</p>")

    for name, s in analysis["systems"].items():
        g = evaluate_gate(s, acc)
        h = s["headline"]
        parts.append(f"<h2>System {name} — backtest (after fees, out-of-sample)</h2><div class='cards'>")
        parts.append(_card("Profit factor", _num(h["profit_factor"]), g["pf_ok"]))
        parts.append(_card("Max drawdown", _pct(h["max_drawdown"]), g["dd_ok"]))
        parts.append(_card("Sharpe", _num(h["sharpe"]), g["sharpe_ok"]))
        parts.append(_card("Trades", str(int(h["trade_count"])), g["enough_trades"]))
        parts.append(_card("Total return", _pct(h["total_return"])))
        parts.append(_card("Robust (subsample PF)", _num(g["sub_median"]), not g["universe_fragile"]))
        parts.append("</div>")
        b = s["benchmark"]
        parts.append(f"<p class='note'>Buy &amp; hold BTC same window: return {_pct(b['total_return'])}, "
                     f"max DD {_pct(b['max_drawdown'])}, Sharpe {_num(b['sharpe'])}.</p>")
        # regime
        parts.append("<table><tr><th>Regime</th><th>% period</th><th>Return</th><th>Max DD</th>"
                     "<th>Exposure</th><th>Trades</th></tr>")
        for lab in ("bull", "bear", "chop"):
            r = s["regime"].get(lab, {})
            parts.append(f"<tr><td>{lab}</td><td>{_pct(r.get('pct_of_period'))}</td>"
                         f"<td>{_pct(r.get('compounded_return'))}</td><td>{_pct(r.get('max_drawdown'))}</td>"
                         f"<td>{_pct(r.get('exposure'))}</td><td>{int(r.get('trades_entered', 0))}</td></tr>")
        parts.append("</table>")
        if s.get("per_fold"):
            parts.append(f"<p class='note'>Per-fold OOS returns (each bar = a 6-month window):</p>{_fold_bars(s['per_fold'])}")

    # paper section
    parts.append("<h2>Paper trading (forward, simulated)</h2>")
    if paper:
        first = paper["paper_start"] == paper["as_of"]
        parts.append(f"<p class='sub'>Started {paper['paper_start']} · as of {paper['as_of']}"
                     + (" · first run, flat start" if first else "") + "</p>")
        parts.append("<table><tr><th>Variant</th><th>Fwd return</th><th>Fwd trades</th>"
                     "<th>Equity (USD)</th><th>Open</th></tr>")
        for vn, v in paper["variants"].items():
            m = v["forward_metrics"]
            parts.append(f"<tr><td>{vn}</td><td>{_pct(m['total_return'])}</td>"
                         f"<td>{int(v['n_forward_trades'])}</td><td>{v['equity_last']:.0f}</td>"
                         f"<td>{len(v['open_positions'])}</td></tr>")
        parts.append("</table>")
    else:
        parts.append("<p class='note'>No paper run yet. Run <code>python scripts/run_paper.py</code>.</p>")

    parts.append("</body></html>")
    return "".join(parts)


_HEAD = """<!doctype html><html><head><meta charset="utf-8"><title>CTS Dashboard</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#0d1117;color:#c9d1d9;margin:0;padding:24px;max-width:900px}
h1{margin:0 0 4px}h2{margin:28px 0 10px;border-bottom:1px solid #30363d;padding-bottom:6px;font-size:18px}
.sub{color:#8b949e;margin:0 0 8px}.note{color:#8b949e;font-size:13px}
.cards{display:flex;flex-wrap:wrap;gap:10px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 14px;min-width:120px}
.lab{color:#8b949e;font-size:12px}.val{font-size:20px;font-weight:600;margin-top:2px}
.b{font-size:10px;padding:2px 6px;border-radius:10px;margin-left:8px;vertical-align:middle}
.ok{background:#193b1f;color:#3fb950}.no{background:#3b1919;color:#f85149}
table{border-collapse:collapse;margin:8px 0;width:100%}
th,td{border:1px solid #30363d;padding:6px 10px;text-align:left;font-size:13px}
th{color:#8b949e;font-weight:500}code{background:#161b22;padding:2px 5px;border-radius:4px}
</style></head><body>"""


def main() -> None:
    analysis_path = ROOT / "data" / "analysis.json"
    if not analysis_path.exists():
        raise SystemExit("No data/analysis.json — run scripts/run_backtest.py first.")
    analysis = json.loads(analysis_path.read_text())
    paper_path = ROOT / "data" / "paper" / "paper_snapshot.json"
    paper = json.loads(paper_path.read_text()) if paper_path.exists() else None
    out = ROOT / "data" / "dashboard.html"
    out.write_text(build_html(analysis, paper))
    print(f"Wrote {out} — open it in a browser.")


if __name__ == "__main__":
    main()
