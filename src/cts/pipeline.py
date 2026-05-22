"""Orchestration: ingest -> universe -> walk-forward -> metrics. Deterministic.

This wires the tested building blocks into one analysis. It is data-source-agnostic:
it operates on a cached panel + symbol metadata, so it runs identically on real
CoinAPI data or on synthetic fixtures (see tests/test_pipeline_smoke.py).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd

from cts.config import backtest_config, get_secret, universe_config
from cts.data.adapter import OHLCV_COLUMNS, DataAdapter, SymbolMeta
from cts.data.cache import Cache
from cts.data.universe import build_schedule, static_exclusion_reason
from cts.engine.backtest import StrategyParams, run_backtest
from cts.engine.fees import FeeModel
from cts.engine.slippage import SlippageModel
from cts.engine.walkforward import generate_folds, run_fixed, run_tuned
from cts.metrics.benchmark import benchmark_summary
from cts.metrics.performance import metrics_summary, profit_factor
from cts.metrics.regime_decomp import classify_regime, decompose
from cts.metrics.robustness import distribution, neighbourhood, subsample_symbols

_BTC_BASES = ("BTC", "XBT")


# --------------------------------------------------------------------------- #
# Data ingest / load
# --------------------------------------------------------------------------- #
def get_coinapi_adapter() -> DataAdapter:
    from cts.data.coinapi import CoinAPIAdapter  # local import keeps requests optional

    return CoinAPIAdapter(get_secret("COINAPI_KEY"), exchange=universe_config().get("exchange", "KRAKEN"))


def ingest(adapter: DataAdapter, cache: Cache, start: date, end: date,
           max_symbols: Optional[int] = None,
           min_recent_volume_usd: float = 5_000_000.0,
           refresh: bool = False) -> Tuple[Dict[str, pd.DataFrame], Dict[str, SymbolMeta]]:
    """Pull symbols + daily OHLCV into the cache, scoped to bound credit spend.

    Scope: keep ALL delisted coins (the survivorship core — they cost little and
    matter most) plus active coins whose current USD volume >= min_recent_volume_usd.
    Order delisted FIRST so that if the credit budget is exhausted mid-run, the
    survivorship-critical coins are already cached. Fails safe on a quota 403.
    Statically-excluded symbols (stablecoin/wrapped/leveraged/quote) are skipped
    but still recorded. Returns (panel, metas) for symbols actually downloaded."""
    import requests as _rq

    cfg_u = universe_config()
    symbols = adapter.list_symbols()
    panel: Dict[str, pd.DataFrame] = {}
    metas: Dict[str, SymbolMeta] = {}
    manifest_syms = []
    candidates: list = []
    for m in symbols:
        excluded = static_exclusion_reason(m, cfg_u)
        rec = {
            "symbol_id": m.symbol_id, "base": m.base, "quote": m.quote,
            "data_start": m.data_start, "data_end": m.data_end, "is_active": m.is_active,
            "recent_volume_usd": m.recent_volume_usd, "static_excluded": excluded,
        }
        manifest_syms.append(rec)
        if excluded is not None:
            continue
        in_scope = (not m.is_active) or (m.recent_volume_usd >= min_recent_volume_usd)
        if not in_scope:
            rec["static_excluded"] = "below-ingest-volume"
            continue
        candidates.append(m)

    # delisted first (is_active False sorts before True), then most-liquid actives.
    candidates.sort(key=lambda m: (m.is_active, -m.recent_volume_usd))
    if max_symbols is not None:
        candidates = candidates[:max_symbols]

    truncated = None
    skipped: list = []
    for m in candidates:
        try:
            if not refresh and cache.has(adapter.source_name, m.symbol_id):
                df = cache.read(adapter.source_name, m.symbol_id)  # resume: reuse cached
            else:
                df = adapter.daily_ohlcv(m.symbol_id, max(start, m.data_start), end)
                if not df.empty:
                    cache.write(adapter.source_name, m.symbol_id, df)
        except _rq.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if code == 403:
                truncated = f"quota exhausted at {m.symbol_id} after {len(panel)} symbols"
                break
            skipped.append({"symbol_id": m.symbol_id, "reason": f"http-{code}"})
            continue
        except _rq.RequestException:
            skipped.append({"symbol_id": m.symbol_id, "reason": "network-error"})
            continue
        if df.empty:
            continue
        panel[m.symbol_id] = df
        metas[m.symbol_id] = m

    cache.write_manifest(adapter.source_name, {
        "source": adapter.source_name,
        "survivorship_clean": adapter.survivorship_clean and truncated is None,
        "exchange": cfg_u.get("exchange"),
        "range": [start, end],
        "min_recent_volume_usd": min_recent_volume_usd,
        "symbol_count_total": len(symbols),
        "symbol_count_pulled": len(panel),
        "request_cost_credits": getattr(adapter, "total_request_cost", None),
        "truncated": truncated,
        "skipped": skipped,
        "symbols": manifest_syms,
    })
    return panel, metas


def load_cached(cache: Cache, source: str) -> Tuple[Dict[str, pd.DataFrame], Dict[str, SymbolMeta], dict]:
    manifest = cache.read_manifest(source)
    if manifest is None:
        raise RuntimeError(f"No cached data for source {source!r}. Run ingest first.")
    panel: Dict[str, pd.DataFrame] = {}
    metas: Dict[str, SymbolMeta] = {}
    for s in manifest["symbols"]:
        if s.get("static_excluded") is not None:
            continue
        sid = s["symbol_id"]
        if not cache.has(source, sid):
            continue
        df = cache.read(source, sid)
        if df.empty:
            continue
        panel[sid] = df
        metas[sid] = SymbolMeta(
            symbol_id=sid, base=s["base"], quote=s["quote"], exchange=manifest.get("exchange", "KRAKEN"),
            data_start=_as_date(s["data_start"]), data_end=_as_date(s.get("data_end")), is_active=s["is_active"],
        )
    return panel, metas, manifest


def _as_date(v) -> Optional[date]:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    return pd.Timestamp(v).date()


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def find_btc(metas: Dict[str, SymbolMeta]) -> Optional[str]:
    for quote in ("USD", "USDT"):
        for sid, m in metas.items():
            if m.base in _BTC_BASES and m.quote == quote:
                return sid
    return None


def make_rebalance_dates(panel: Dict[str, pd.DataFrame], cfg_u: dict, cfg_s: dict) -> List[pd.Timestamp]:
    first = min(df.index.min() for df in panel.values())
    last = max(df.index.max() for df in panel.values())
    warmup = pd.Timedelta(days=int(cfg_u.get("min_history_days", 90)))
    step = f"{int(cfg_s.get('xs_rebalance_days', 7))}D"
    return list(pd.date_range(first + warmup, last, freq=step))


def _params(cfg_s: dict, n_entry: int, n_exit: int) -> StrategyParams:
    return StrategyParams(
        n_entry=n_entry, n_exit=n_exit,
        atr_period=int(cfg_s["atr_period"]), atr_stop_mult=float(cfg_s["atr_stop_mult"]),
        rvol_period=int(cfg_s["rvol_period"]), rvol_min=float(cfg_s["rvol_min"]),
        risk_per_position_pct=float(cfg_s["risk_per_position_pct"]),
        regime_ma_short=int(cfg_s["regime"]["ma_short"]), regime_ma_long=int(cfg_s["regime"]["ma_long"]),
    )


def _slice_metrics(equity: pd.Series, trades, start, end) -> dict:
    eq = equity[(equity.index >= start) & (equity.index <= end)]
    tr = [t for t in trades if start <= t.entry_date <= end]
    return metrics_summary(eq, tr)


def analyse_system(panel, metas, btc_close, schedule, base_params, cfg_bt,
                   full_start, full_end, system_name) -> dict:
    fees = FeeModel(taker_pct=cfg_bt["fees"]["taker_pct"], maker_pct=cfg_bt["fees"]["maker_pct"],
                    exit_uses_maker=cfg_bt["fees"]["exit_uses_maker"])
    slip = SlippageModel(per_side_pct=cfg_bt["slippage"]["per_side_pct"])
    eq_usd = float(cfg_bt["equity"]["start_gbp"]) * float(cfg_bt["equity"]["gbp_usd_rate"])
    maxpos = int(cfg_bt["portfolio"]["max_concurrent_positions"])
    maxdep = float(cfg_bt["portfolio"]["max_deployed_pct"])
    common = dict(fee_model=fees, slippage=slip, start_equity_usd=eq_usd,
                  max_positions=maxpos, max_deployed_pct=maxdep, system_name=system_name)

    # Headline: starting params, never fitted -> already OOS w.r.t. parameter choice.
    headline_res = run_fixed(panel, btc_close, schedule, base_params,
                             start=full_start, end=full_end, **common)
    headline = metrics_summary(headline_res.equity_curve, headline_res.trades)

    # Per-fold slices of the headline curve (stability across time).
    wf = cfg_bt["walk_forward"]
    folds = generate_folds(full_start, full_end, wf["in_sample_months"], wf["out_of_sample_months"], wf["step_months"])
    per_fold = [{
        "fold": f.index, "oos_start": f.oos_start.date().isoformat(), "oos_end": f.oos_end.date().isoformat(),
        "metrics": _slice_metrics(headline_res.equity_curve, headline_res.trades, f.oos_start, f.oos_end),
    } for f in folds]

    # Regime decomposition (independent classification).
    rd_cfg = cfg_bt["regime_decomp"]
    labels = classify_regime(btc_close, rd_cfg["ma_short"], rd_cfg["ma_long"])
    regime = decompose(headline_res.equity_curve, headline_res.trades, labels)

    # Benchmark: buy & hold BTC over the same window.
    bench = benchmark_summary(btc_close, full_start, full_end)

    # Robustness — universe subsampling.
    rob = cfg_bt["robustness"]
    cfg_u, cfg_s = universe_config(), cfg_bt["strategy"]
    rebalance_dates = schedule.rebalance_dates
    sub_pf, sub_ret, sub_dd = [], [], []
    for seed in rob["subsample_seeds"]:
        subset = subsample_symbols(list(panel.keys()), rob["subsample_frac"], seed)
        sub_panel = {s: panel[s] for s in subset}
        sub_metas = {s: metas[s] for s in subset}
        sub_sched = build_schedule(sub_panel, sub_metas, cfg_u, cfg_s, rebalance_dates)
        r = run_fixed(sub_panel, btc_close, sub_sched, base_params, start=full_start, end=full_end, **common)
        m = metrics_summary(r.equity_curve, r.trades)
        sub_pf.append(m["profit_factor"]); sub_ret.append(m["total_return"]); sub_dd.append(m["max_drawdown"])

    # Robustness — parameter neighbourhood (distribution, not the peak).
    nb = rob["param_neighbourhood"]
    axes = {"n_entry": nb["donchian_entry"], "atr_stop_mult": nb["atr_stop_mult"], "rvol_min": nb["rvol_min"]}
    nb_pf, nb_ret, nb_dd = [], [], []
    for cand in neighbourhood(base_params, axes):
        r = run_fixed(panel, btc_close, schedule, cand, start=full_start, end=full_end, **common)
        m = metrics_summary(r.equity_curve, r.trades)
        nb_pf.append(m["profit_factor"]); nb_ret.append(m["total_return"]); nb_dd.append(m["max_drawdown"])

    # Tuned walk-forward (tune on IS, apply OOS). Compact grid to stay tractable.
    tuned = None
    if folds:
        tune_axes = {"n_entry": nb["donchian_entry"], "atr_stop_mult": nb["atr_stop_mult"]}
        candidates = neighbourhood(base_params, tune_axes)
        t = run_tuned(panel, btc_close, schedule, candidates, folds,
                      objective=lambda r: profit_factor(r.trades) if r.trades else float("-inf"), **common)
        tuned = {
            "metrics": metrics_summary(t["equity"], t["trades"]),
            "chosen": [{"fold": f.index, "n_entry": p.n_entry, "atr_stop_mult": p.atr_stop_mult,
                        "is_pf": (None if score == float("-inf") else round(score, 3))}
                       for (f, p, score) in t["chosen"]],
        }

    return {
        "system": system_name,
        "params": base_params.__dict__,
        "headline": headline,
        "per_fold": per_fold,
        "regime": regime,
        "benchmark": bench,
        "robustness_subsample": {
            "profit_factor": distribution(sub_pf), "total_return": distribution(sub_ret),
            "max_drawdown": distribution(sub_dd),
        },
        "robustness_neighbourhood": {
            "profit_factor": distribution(nb_pf), "total_return": distribution(nb_ret),
            "max_drawdown": distribution(nb_dd), "n": len(nb_pf),
        },
        "tuned": tuned,
        "window": [full_start.date().isoformat(), full_end.date().isoformat()],
    }


def run_analysis(panel, metas, manifest: dict) -> dict:
    cfg_u, cfg_bt = universe_config(), backtest_config()
    cfg_s = cfg_bt["strategy"]
    btc_id = find_btc(metas)
    if btc_id is None:
        raise RuntimeError("No BTC/USD or BTC/USDT symbol found — regime filter needs BTC.")
    btc_close = panel[btc_id]["close"]

    # Data-sanity guard: never emit a verdict on degenerate (e.g. all-NaN) data.
    valid_btc = int(btc_close.notna().sum())
    if valid_btc < 200:
        raise RuntimeError(
            f"BTC close has only {valid_btc} non-NaN points — data looks broken. Refusing to "
            "emit a verdict on degenerate data; re-ingest and check the data adapter."
        )
    usable = sum(1 for df in panel.values() if df["close"].notna().sum() >= 90)
    if usable < 3:
        raise RuntimeError(f"Only {usable} symbols have >=90 valid closes — universe too degenerate to test.")

    rebalance_dates = make_rebalance_dates(panel, cfg_u, cfg_s)
    schedule = build_schedule(panel, metas, cfg_u, cfg_s, rebalance_dates)
    full_start = rebalance_dates[0]
    full_end = max(df.index.max() for df in panel.values())

    systems = {}
    for name, sysdef in cfg_s["systems"].items():
        label = "S1" if name == "system1" else ("S2" if name == "system2" else name)
        bp = _params(cfg_s, int(sysdef["donchian_entry"]), int(sysdef["donchian_exit"]))
        systems[label] = analyse_system(panel, metas, btc_close, schedule, bp, cfg_bt,
                                         full_start, full_end, label)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": manifest.get("source"),
        "survivorship_clean": manifest.get("survivorship_clean", False),
        "window": [full_start.date().isoformat(), full_end.date().isoformat()],
        "universe": {
            "symbols_traded": len(panel),
            "btc_symbol": btc_id,
            "rebalance_count": len(rebalance_dates),
            "exclusion_notes": schedule.notes,
        },
        "acceptance": cfg_bt_acceptance(),
        "systems": systems,
        "schedule_log": schedule.log,
    }


def cfg_bt_acceptance() -> dict:
    return {"min_profit_factor": 1.5, "max_drawdown": 0.25, "min_oos_sharpe": 0.0}
