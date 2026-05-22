#!/usr/bin/env python
"""Run the walk-forward backtest on cached data and write FINDINGS.md.

  python scripts/run_backtest.py
"""
from __future__ import annotations

import json

from cts.config import ROOT
from cts.data.cache import Cache
from cts.pipeline import load_cached, run_analysis
from cts.reporting.findings import render_findings
from cts.safety import backtest_only_notice


def main() -> None:
    print(backtest_only_notice())
    cache = Cache(ROOT / "data" / "cache")
    panel, metas, manifest = load_cached(cache, "coinapi")
    print(f"Loaded {len(panel)} symbols from cache. Running walk-forward analysis...")

    analysis = run_analysis(panel, metas, manifest)

    # Persist the universe log + a JSON snapshot alongside FINDINGS.md.
    (ROOT / "data" / "universe_log.csv").write_text(analysis["schedule_log"].to_csv(index=False))
    snapshot = {k: v for k, v in analysis.items() if k != "schedule_log"}
    (ROOT / "data" / "analysis.json").write_text(json.dumps(snapshot, indent=2, default=str))

    findings = render_findings(analysis)
    (ROOT / "FINDINGS.md").write_text(findings)
    print("Wrote FINDINGS.md, data/analysis.json, data/universe_log.csv")
    # echo the verdict line
    for line in findings.splitlines():
        if line.startswith("## VERDICT"):
            print(line.replace("##", "").strip())
            break


if __name__ == "__main__":
    main()
