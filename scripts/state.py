#!/usr/bin/env python
"""Generate docs/PROJECT_CONTEXT.md — a single, daily-auto-updated snapshot of the
live system for brainstorming / Claude.ai Project sync (mirrors the GTS pattern):
current paper status + validated metrics + a change log (recent commits) + links.
Regenerated and committed by the daily GitHub Action, so the repo copy is always
current with no manual action.

  python scripts/state.py
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from cts.config import ROOT


def _load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def _pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def _changelog(n: int = 15) -> str:
    try:
        out = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:- %ad — %s", "--date=short"],
            cwd=ROOT, capture_output=True, text=True, timeout=20,
        )
        return out.stdout.strip() or "_(no history available)_"
    except Exception:
        return "_(no history available)_"


def main() -> None:
    paper = _load(ROOT / "data" / "paper" / "paper_snapshot.json")
    analysis = _load(ROOT / "data" / "analysis.json")
    L = ["# CTS — Project Context (auto-updated daily)\n"]
    L.append(f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} · "
             "SIMULATED — no real money · dashboard: https://g-mac12.github.io/cts-trading/_\n")

    if paper:
        on = paper.get("regime_on", False)
        L.append("## Paper status (forward, simulated)")
        L.append(f"- As of **{paper['as_of']}** (paper started {paper['paper_start']}).")
        L.append(f"- Market regime: **{'RISK-ON — eligible to trade' if on else 'RISK-OFF — in cash'}**.")
        for vn, v in paper["variants"].items():
            m = v["forward_metrics"]
            L.append(f"- **{vn}**: equity ${v['equity_last']:.0f} · return {_pct(m['total_return'])} · "
                     f"{int(v['n_forward_trades'])} trades · {len(v['open_positions'])} open.")
        if paper.get("watchlist"):
            L.append(f"- Watchlist: {', '.join(paper['watchlist'])}.")
        L.append("")

    if analysis:
        L.append("## Validated edge (backtest, after fees, out-of-sample)")
        for name, s in analysis["systems"].items():
            h = s["headline"]
            L.append(f"- **System {name}**: profit factor {h['profit_factor']:.2f} · "
                     f"max DD {_pct(h['max_drawdown'])} · Sharpe {h['sharpe']:.2f} · "
                     f"{int(h['trade_count'])} trades.")
        L.append("")

    L.append("## Recent changes (log)")
    L.append(_changelog())
    L.append("")
    L.append("## More")
    L.append("- Overview: `SYSTEM_OVERVIEW.md` · Verdict: `FINDINGS.md` · Experiments: `EXPERIMENTS.md`")

    out = ROOT / "docs" / "PROJECT_CONTEXT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
