"""Lean local paper-trader (Phase 3-lite). Runs the VALIDATED Phase 1 strategy
forward from a fixed paper-start date, with a fresh simulation portfolio, on
freshly-pulled daily data. No real orders, ever — fills are simulated with the
same fee + slippage models as the backtest.

It runs four variants in parallel so live data can judge them:
  S1/S2 × {baseline, chopfix}, where chopfix = exit open positions when the
  regime flips off (the candidate fix for chop give-back). Paper is free, so we
  let forward results — not in-sample tuning — decide which is better.

Determinism: re-running the strategy from inception each day reproduces the exact
point-in-time decisions (no lookahead), so the forward record is a true paper
track, with the portfolio started fresh at paper_start (= the first run date).
"""
from __future__ import annotations

import csv
import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd

from cts.config import ROOT, backtest_config, universe_config
from cts.data.cache import Cache
from cts.data.universe import build_schedule
from cts.engine.backtest import run_backtest
from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel
from cts.metrics.performance import metrics_summary
from cts.pipeline import _params, find_btc, load_cached, make_rebalance_dates
from cts.strategy.regime import regime_on

PAPER_DIR = ROOT / "data" / "paper"


def _variants(cfg_s: dict) -> Dict[str, object]:
    out = {}
    for sysname, sysdef in cfg_s["systems"].items():
        label = "S1" if sysname == "system1" else ("S2" if sysname == "system2" else sysname)
        base = _params(cfg_s, int(sysdef["donchian_entry"]), int(sysdef["donchian_exit"]))
        out[f"{label}-baseline"] = base
        out[f"{label}-chopfix"] = replace(base, regime_exit=True)
    return out


def _load_state() -> Optional[dict]:
    p = PAPER_DIR / "paper_state.json"
    return json.loads(p.read_text()) if p.exists() else None


def _save_state(state: dict) -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    (PAPER_DIR / "paper_state.json").write_text(json.dumps(state, indent=2, default=str))


def _append_runlog(report: dict) -> None:
    """Append one row per variant in LONG format (stable schema even if the set of
    variants changes) — this is the equity-curve history the dashboard plots."""
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    path = PAPER_DIR / "paper_runs.csv"
    fields = ["as_of", "run_at", "variant", "equity", "fwd_trades", "fwd_return"]
    write_header = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        for v, vr in report["variants"].items():
            w.writerow({
                "as_of": report["as_of"], "run_at": report["generated_at"], "variant": v,
                "equity": round(vr["equity_last"], 2), "fwd_trades": vr["n_forward_trades"],
                "fwd_return": round(vr["forward_metrics"]["total_return"], 6),
            })


def run_paper(as_of: Optional[str] = None, source: str = "coinapi") -> dict:
    cfg_u, cfg_bt = universe_config(), backtest_config()
    cfg_s = cfg_bt["strategy"]
    panel, metas, manifest = load_cached(Cache(ROOT / "data" / "cache"), source)

    btc_id = find_btc(metas)
    if btc_id is None:
        raise RuntimeError("No BTC/USD or BTC/USDT symbol — regime filter needs BTC.")
    btc_close = panel[btc_id]["close"]
    if int(btc_close.notna().sum()) < 200:
        raise RuntimeError("BTC data looks degenerate — refusing to paper-trade on it.")

    data_end = max(df.index.max() for df in panel.values())
    as_of_ts = pd.Timestamp(as_of, tz="UTC") if as_of else data_end

    eq_usd = float(cfg_bt["equity"]["start_gbp"]) * float(cfg_bt["equity"]["gbp_usd_rate"])
    state = _load_state()
    if state is None:  # first run sets paper-start = now, fixed thereafter
        paper_start = as_of_ts
        state = {"paper_start": paper_start.date().isoformat(), "inception_equity_usd": eq_usd,
                 "first_run_at": datetime.now(timezone.utc).isoformat()}
        _save_state(state)
    else:
        paper_start = pd.Timestamp(state["paper_start"], tz="UTC")

    rebalance_dates = make_rebalance_dates(panel, cfg_u, cfg_s)  # full history for indicator warmup
    schedule = build_schedule(panel, metas, cfg_u, cfg_s, rebalance_dates)
    fees = FeeModel(taker_pct=cfg_bt["fees"]["taker_pct"], maker_pct=cfg_bt["fees"]["maker_pct"],
                    exit_uses_maker=cfg_bt["fees"]["exit_uses_maker"])
    slip = SlippageModel(per_side_pct=cfg_bt["slippage"]["per_side_pct"])
    maxpos = int(cfg_bt["portfolio"]["max_concurrent_positions"])
    maxdep = float(cfg_bt["portfolio"]["max_deployed_pct"])

    # Current regime (is the market risk-on right now?) and the watchlist it's scanning.
    reg = regime_on(btc_close, int(cfg_s["regime"]["ma_short"]), int(cfg_s["regime"]["ma_long"]))
    reg_upto = reg[reg.index <= as_of_ts]
    regime_on_now = bool(reg_upto.iloc[-1]) if len(reg_upto) else False
    past_rbs = [d for d in rebalance_dates if d <= as_of_ts]
    watch_ids = schedule.top_tier_by_date.get(past_rbs[-1], []) if past_rbs else []
    watchlist = [metas[s].base for s in watch_ids if s in metas]

    def _base(sym):
        return metas[sym].base if sym in metas else sym

    variants_out = {}
    for name, p in _variants(cfg_s).items():
        r = run_backtest(panel, btc_close, schedule, p, fees, slip, eq_usd,
                         paper_start, as_of_ts, maxpos, maxdep, name, close_at_end=False)
        last_prices = {s: df["close"].reindex([as_of_ts]).ffill().iloc[0]
                       for s, df in panel.items() if s in {pos.symbol for pos in r.open_positions}}
        variants_out[name] = {
            "regime_exit": p.regime_exit,
            "n_entry": p.n_entry, "n_exit": p.n_exit,
            "equity_last": float(r.equity_curve.iloc[-1]) if len(r.equity_curve) else eq_usd,
            "forward_metrics": metrics_summary(r.equity_curve, r.trades),
            "n_forward_trades": len(r.trades),
            "open_positions": [
                {"symbol": _base(pos.symbol), "entry_date": pos.entry_date.date().isoformat(),
                 "entry_price": round(pos.entry_price, 6), "units": round(pos.units, 6),
                 "stop": round(pos.stop, 6),
                 "mark": round(float(last_prices.get(pos.symbol, pos.entry_price)), 6)}
                for pos in r.open_positions
            ],
            "trades": [
                {"symbol": _base(t.symbol), "entry_date": t.entry_date.date().isoformat(),
                 "exit_date": t.exit_date.date().isoformat(), "entry_price": round(t.entry_price, 6),
                 "exit_price": round(t.exit_price, 6), "net_pnl": round(t.net_pnl, 2),
                 "return_pct": round(t.return_pct, 4), "reason": t.exit_reason}
                for t in r.trades
            ],
            "next_session_orders": {"entries": [_base(s) for s in r.pending_orders.get("entries", [])],
                                    "exits": [_base(s) for s in r.pending_orders.get("exits", {})]},
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_start": paper_start.date().isoformat(),
        "as_of": as_of_ts.date().isoformat(),
        "inception_equity_usd": eq_usd,
        "data_source": manifest.get("source"),
        "survivorship_clean": manifest.get("survivorship_clean", False),
        "universe_symbols": len(panel),
        "regime_on": regime_on_now,
        "watchlist": watchlist,
        "variants": variants_out,
    }
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    (PAPER_DIR / "paper_snapshot.json").write_text(json.dumps(report, indent=2, default=str))
    _append_runlog(report)
    return report
