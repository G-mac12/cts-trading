"""Render FINDINGS.md from the analysis dict. The gate verdict is computed
deterministically from the acceptance criteria (§9) applied to the HEADLINE
(starting-parameter) out-of-sample results, with an explicit overfit check."""
from __future__ import annotations

import math
from typing import Dict


def _num(x: float, dp: int = 2) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    return f"{x:.{dp}f}"


def _pct(x: float) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    return f"{x * 100:.1f}%"


def evaluate_gate(sysres: Dict, acceptance: Dict) -> Dict:
    h = sysres["headline"]
    bear, chop = sysres["regime"].get("bear", {}), sysres["regime"].get("chop", {})
    nb = sysres["robustness_neighbourhood"]["profit_factor"]
    sub = sysres["robustness_subsample"]["profit_factor"]

    pf_ok = h["profit_factor"] >= acceptance["min_profit_factor"]
    dd_ok = h["max_drawdown"] > -acceptance["max_drawdown"]  # e.g. -0.20 > -0.25
    sharpe_ok = h["sharpe"] > acceptance["min_oos_sharpe"]
    # Cash-preserving bear/chop: don't bleed and don't be heavily deployed.
    bear_ok = bear.get("compounded_return", -1) > -0.10 and bear.get("exposure", 1) < 0.5
    chop_ok = chop.get("compounded_return", -1) > -0.10 and chop.get("exposure", 1) < 0.5
    enough_trades = h["trade_count"] >= 30

    headline_pass = pf_ok and dd_ok and sharpe_ok and bear_ok and chop_ok
    # Overfit signal: passes at the exact point but the neighbourhood/subsample don't hold up.
    knife_edge = headline_pass and (nb["median"] < acceptance["min_profit_factor"] or sub["median"] < 1.0)

    return {
        "pf_ok": pf_ok, "dd_ok": dd_ok, "sharpe_ok": sharpe_ok,
        "bear_ok": bear_ok, "chop_ok": chop_ok, "enough_trades": enough_trades,
        "headline_pass": headline_pass, "knife_edge": knife_edge,
    }


def _regime_table(regime: Dict) -> str:
    rows = ["| Regime | % of period | Return | Max DD | Exposure | Trades | Trade P&L |",
            "|---|---|---|---|---|---|---|"]
    for lab in ("bull", "bear", "chop"):
        r = regime.get(lab, {})
        rows.append(
            f"| {lab} | {_pct(r.get('pct_of_period'))} | {_pct(r.get('compounded_return'))} | "
            f"{_pct(r.get('max_drawdown'))} | {_pct(r.get('exposure'))} | "
            f"{int(r.get('trades_entered', 0))} | {_num(r.get('trades_net_pnl'))} |"
        )
    return "\n".join(rows)


def _dist_row(name: str, d: Dict) -> str:
    return (f"| {name} | {_num(d['median'])} | {_num(d['mean'])} | {_num(d['min'])} | "
            f"{_num(d['p25'])} | {_num(d['p75'])} | {_num(d['max'])} |")


def _system_section(sysres: Dict, gate: Dict) -> str:
    h = sysres["headline"]
    p = sysres["params"]
    out = []
    out.append(f"### System {sysres['system']} — Donchian entry N={p['n_entry']}, exit N={p['n_exit']}\n")
    out.append("**Headline (starting parameters, out-of-sample, after fees)**\n")
    out.append("| Metric | Value | Bar | Pass |")
    out.append("|---|---|---|---|")
    out.append(f"| Profit factor | {_num(h['profit_factor'])} | > 1.5 | {'✅' if gate['pf_ok'] else '❌'} |")
    out.append(f"| Max drawdown | {_pct(h['max_drawdown'])} | > -25% | {'✅' if gate['dd_ok'] else '❌'} |")
    out.append(f"| Sharpe | {_num(h['sharpe'])} | > 0 | {'✅' if gate['sharpe_ok'] else '❌'} |")
    out.append(f"| Total return | {_pct(h['total_return'])} | — | |")
    out.append(f"| CAGR | {_pct(h['cagr'])} | — | |")
    out.append(f"| Win rate | {_pct(h['win_rate'])} | — | |")
    out.append(f"| Avg win / avg loss | {_num(h['payoff_ratio'])} | — | |")
    out.append(f"| Expectancy / trade (USD) | {_num(h['expectancy'])} | — | |")
    out.append(f"| Trade count | {int(h['trade_count'])} | >= 30 | {'✅' if gate['enough_trades'] else '⚠️'} |")
    out.append(f"| Exposure (time in market) | {_pct(h['exposure'])} | — | |")
    out.append("")
    b = sysres["benchmark"]
    out.append(f"**Benchmark — buy & hold BTC (same window):** return {_pct(b['total_return'])}, "
               f"max DD {_pct(b['max_drawdown'])}, Sharpe {_num(b['sharpe'])}.\n")
    out.append("**Regime decomposition** (must preserve capital + stay in cash during bear/chop):\n")
    out.append(_regime_table(sysres["regime"]))
    out.append(f"\nBear behaviour {'✅ controlled' if gate['bear_ok'] else '❌ NOT controlled'}; "
               f"chop behaviour {'✅ controlled' if gate['chop_ok'] else '❌ NOT controlled'}.\n")
    out.append("**Robustness — profit factor distribution** (a real edge survives off the exact peak):\n")
    out.append("| Source | Median | Mean | Min | P25 | P75 | Max |")
    out.append("|---|---|---|---|---|---|---|")
    out.append(_dist_row(f"Universe subsample (2/3, {int(sysres['robustness_subsample']['profit_factor']['n'])} seeds)",
                         sysres["robustness_subsample"]["profit_factor"]))
    out.append(_dist_row(f"Parameter neighbourhood ({sysres['robustness_neighbourhood']['n']} sets)",
                         sysres["robustness_neighbourhood"]["profit_factor"]))
    out.append("")
    if sysres.get("tuned"):
        tm = sysres["tuned"]["metrics"]
        out.append(f"**Tuned walk-forward (tune on IS, apply OOS):** PF {_num(tm['profit_factor'])}, "
                   f"return {_pct(tm['total_return'])}, max DD {_pct(tm['max_drawdown'])}, "
                   f"Sharpe {_num(tm['sharpe'])}, trades {int(tm['trade_count'])}.")
        chosen = ", ".join(f"f{c['fold']}:N={c['n_entry']}/stop={c['atr_stop_mult']}" for c in sysres["tuned"]["chosen"])
        out.append(f"Per-fold chosen params (instability = overfit signal): {chosen}\n")
    if sysres.get("per_fold"):
        out.append("**Per-fold OOS stability (headline params):**\n")
        out.append("| Fold | OOS window | PF | Return | Max DD | Trades |")
        out.append("|---|---|---|---|---|---|")
        for f in sysres["per_fold"]:
            m = f["metrics"]
            out.append(f"| {f['fold']} | {f['oos_start']}→{f['oos_end']} | {_num(m['profit_factor'])} | "
                       f"{_pct(m['total_return'])} | {_pct(m['max_drawdown'])} | {int(m['trade_count'])} |")
        out.append("")
    if gate["knife_edge"]:
        out.append("> ⚠️ **Overfit warning:** the headline passes but the parameter-neighbourhood / "
                   "subsample medians do NOT hold up. This edge appears to exist only at the exact "
                   "starting point and should be treated as fragile (effectively a fail).\n")
    return "\n".join(out)


def render_findings(analysis: Dict) -> str:
    acceptance = analysis["acceptance"]
    gates = {name: evaluate_gate(s, acceptance) for name, s in analysis["systems"].items()}

    genuine_pass = {n for n, g in gates.items() if g["headline_pass"] and not g["knife_edge"]}
    trades_ok = {n for n, g in gates.items() if g["enough_trades"]}
    go = bool(genuine_pass & trades_ok)

    L = []
    L.append("# CTS Phase 1 — FINDINGS\n")
    L.append(f"_Generated {analysis['generated_at']} · data source: {analysis['source']} · "
             f"window {analysis['window'][0]} → {analysis['window'][1]}_\n")

    # The verdict, up top and unmissable.
    verdict = "GO" if go else "NO-GO"
    L.append(f"## VERDICT: **{verdict}** for Phase 2\n")
    if not analysis.get("survivorship_clean", False):
        L.append("> 🟠 **PROVISIONAL — data was NOT certified survivorship-clean by the adapter.** "
                 "Delisted-coin coverage is not guaranteed, so live results would likely be WORSE "
                 "than shown. Treat every number below as optimistic until re-run on survivorship-clean data.\n")
    else:
        L.append("> ✅ Data adapter reports survivorship-clean coverage (delisted symbols included).\n")

    # Plain-language summary.
    L.append("### Does the edge survive — plain answer\n")
    if go:
        names = ", ".join(sorted(genuine_pass & trades_ok))
        L.append(f"On out-of-sample, after-fee data, **system(s) {names} cleared the §9 bar on the "
                 f"STARTING parameters** (PF > 1.5, max DD < 25%, positive Sharpe, capital-preserving "
                 f"in bear/chop) and held up across the parameter neighbourhood and universe subsamples. "
                 f"The momentum edge appears real under these assumptions.\n")
    else:
        reasons = []
        for n, g in gates.items():
            why = [k for k, ok in [("PF<1.5", not g["pf_ok"]), ("DD>=25%", not g["dd_ok"]),
                                   ("Sharpe<=0", not g["sharpe_ok"]), ("bear not controlled", not g["bear_ok"]),
                                   ("chop not controlled", not g["chop_ok"]), ("<30 trades", not g["enough_trades"]),
                                   ("knife-edge/overfit", g["knife_edge"])] if ok]
            reasons.append(f"**{n}**: " + (", ".join(why) if why else "passed"))
        L.append("On out-of-sample, after-fee data, the starting parameters **did not clear the §9 bar**. "
                 "Per system: " + "; ".join(reasons) + ".\n")
        L.append("Per the spec, a clean failure here is a **successful** outcome for Phase 1: it stops the "
                 "project before any infrastructure is built. Recommend **NO-GO** unless the assumptions "
                 "below are revisited.\n")

    # Universe / assumptions.
    u = analysis["universe"]
    L.append("### Universe & assumptions\n")
    L.append(f"- Symbols actually traded: **{u['symbols_traded']}** · BTC (regime): `{u['btc_symbol']}` · "
             f"rebalances: {u['rebalance_count']}.")
    L.append("- Fees: Kraken Pro **taker on entry**; exits taker by default (maker only where a resting "
             "limit genuinely earns it). Round-trip ≈ 0.8% before slippage.")
    L.append("- Slippage: explicit per-side assumption (see config); stress band reported via neighbourhood.")
    L.append("- Execution: signals on daily close; entries/Donchian-exits at NEXT open; stops intrabar "
             "(stop wins ties). Daily candles (Phase 1 resolution).")
    L.append("- Equity: £2,000 simulation balance converted to USD at a fixed rate (no real money).")
    for note in u.get("exclusion_notes", []):
        L.append(f"- {note}")
    if not analysis.get("survivorship_clean", False):
        L.append("- ⚠️ Survivorship: NOT guaranteed clean by this source — see provisional banner above.")
    L.append("- Residual gap (any source): no vendor encodes UK-specific Kraken availability, so the "
             "universe is 'Kraken global' as a proxy for what a UK account could trade.\n")

    # Per-system detail.
    L.append("## Per-system results\n")
    for name in analysis["systems"]:
        L.append(_system_section(analysis["systems"][name], gates[name]))
        L.append("")

    # Reasoning.
    L.append("## Recommendation & reasoning\n")
    L.append(f"**{verdict}.** " + (
        "At least one system clears the acceptance bar on starting parameters with robustness support. "
        "Proceed to Phase 2 (strategy engine) — but carry the assumptions above as live risks."
        if go else
        "No system clears the acceptance bar on the starting parameters without relying on suspiciously "
        "narrow tuning. Do not build Phase 2+ infrastructure on this edge as specified. Options: revisit "
        "the regime filter / universe / fee assumptions and re-run, or stop here — cheaply, as intended."
    ))
    L.append("\n_Anti-overfitting note: the headline uses the spec's starting parameters unchanged. "
             "Any result that appears only under tuning is reported as such and treated as a fail._\n")
    return "\n".join(L)
