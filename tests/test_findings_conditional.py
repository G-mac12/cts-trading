"""The DD-only-conditional verdict path must be emitted MECHANICALLY (so it survives a
bare regeneration of FINDINGS.md and can never present a standalone, misleading NO-GO).

These tests pin that behaviour: when the sole failing §9 sub-metric is the (sizing-
dependent) drawdown gate — PF/Sharpe pass, powered, robust — the renderer must
  * mark the verdict CONDITIONAL,
  * print the loud "MECHANICAL VERDICT ONLY" marker,
  * explain the edge-neutral risk dependency,
and must NOT do any of that when drawdown actually passes.
"""
from __future__ import annotations

from cts.reporting.findings import evaluate_gate, render_findings

ACCEPT = {"min_profit_factor": 1.5, "max_drawdown": 0.25, "min_oos_sharpe": 0.0}


def _dist(median: float) -> dict:
    return {"mean": median, "std": 0.0, "min": median, "p25": median,
            "median": median, "p75": median, "max": median, "n": 3.0}


def _system(max_dd: float) -> dict:
    """Minimal-but-complete system result. PF/Sharpe/power/robustness all pass; only the
    drawdown varies, so `max_dd` alone decides whether the DD gate fails."""
    return {
        "system": "S1",
        "params": {"n_entry": 20, "n_exit": 10, "risk_per_position_pct": 0.6},
        "headline": {
            "profit_factor": 2.23, "max_drawdown": max_dd, "sharpe": 0.71,
            "total_return": 1.17, "cagr": 0.10, "win_rate": 0.34, "payoff_ratio": 4.3,
            "expectancy": 23.0, "trade_count": 129.0, "exposure": 0.37,
        },
        "benchmark": {"total_return": 10.0, "max_drawdown": -0.77, "sharpe": 0.79},
        "regime": {
            "bull": {"pct_of_period": 0.43, "compounded_return": 1.98, "max_drawdown": -0.14,
                     "exposure": 0.76, "trades_entered": 126, "trades_net_pnl": 3057.0},
            "bear": {"pct_of_period": 0.38, "compounded_return": -0.015, "max_drawdown": -0.015,
                     "exposure": 0.017, "trades_entered": 0, "trades_net_pnl": 0.0},
            "chop": {"pct_of_period": 0.18, "compounded_return": -0.26, "max_drawdown": -0.26,
                     "exposure": 0.21, "trades_entered": 3, "trades_net_pnl": -96.0},
        },
        "robustness_subsample": {"profit_factor": _dist(1.99)},
        "robustness_neighbourhood": {"profit_factor": _dist(2.37), "n": 6},
        "per_fold": [],
        "window": ["2018-04-01", "2026-05-23"],
    }


def _analysis(max_dd: float) -> dict:
    return {
        "generated_at": "2026-05-24T00:00:00+00:00", "source": "coinapi",
        "survivorship_clean": True, "window": ["2018-04-01", "2026-05-23"],
        "universe": {"symbols_traded": 341, "btc_symbol": "KRAKEN_SPOT_BTC_USD",
                     "rebalance_count": 425, "exclusion_notes": []},
        "acceptance": ACCEPT, "systems": {"S1": _system(max_dd)},
    }


def test_dd_only_conditional_flag():
    # DD fails (−25.6% breaches the <25% gate); everything else passes -> conditional.
    g_fail = evaluate_gate(_system(-0.256), ACCEPT)
    assert g_fail["dd_only_conditional"] is True
    assert not g_fail["dd_ok"] and g_fail["pf_ok"] and g_fail["sharpe_ok"]
    assert round(g_fail["dd_fail_pp"], 1) == 0.6
    # DD passes -> not conditional.
    g_ok = evaluate_gate(_system(-0.15), ACCEPT)
    assert g_ok["dd_only_conditional"] is False


def test_conditional_verdict_is_emitted_mechanically():
    md = render_findings(_analysis(-0.256))
    assert "CONDITIONAL" in md
    assert "MECHANICAL VERDICT ONLY" in md          # the loud, un-missable marker
    assert "edge-neutral" in md                      # the dependency is explained
    assert "0.6pp" in md                             # the precise margin, computed
    # the NO-GO token is still present and not flipped to GO
    assert "NO-GO" in md and "**GO**" not in md


def test_passing_drawdown_emits_no_conditional_block():
    md = render_findings(_analysis(-0.15))
    assert "MECHANICAL VERDICT ONLY" not in md
    assert "CONDITIONAL" not in md
