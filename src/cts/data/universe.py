"""Universe construction (§4) — point-in-time, no lookahead.

At each rebalance date, using only data up to that date, decide which symbols are
eligible (active, liquid, enough history, right quote, not excluded) and which are
in the top momentum tier. Every excluded symbol is logged with a reason code so
FINDINGS.md can show exactly what was in/out and why.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

import pandas as pd

from cts.data.adapter import SymbolMeta
from cts.indicators import pct_return
from cts.strategy.ranking import top_tier_mask


def is_stablecoin(base: str, cfg: dict) -> bool:
    return base.upper() in {b.upper() for b in cfg.get("stablecoin_bases", [])}


def is_wrapped(base: str, cfg: dict) -> bool:
    b = base.upper()
    if b in {x.upper() for x in cfg.get("wrapped_bases", [])}:
        return True
    return b.startswith("W") and len(b) >= 4  # WBTC, WETH, WSTETH ...


def is_leveraged(base: str, cfg: dict) -> bool:
    b = base.upper()
    for token in cfg.get("leveraged_substrings", []):
        t = token.upper()
        if b.endswith(t) and b not in ("UP", "DOWN"):  # e.g. BTCUP, ETHBEAR, ETH3L
            return True
    return False


def static_exclusion_reason(meta: SymbolMeta, cfg: dict) -> Optional[str]:
    """Reasons knowable from metadata alone (independent of date)."""
    if cfg.get("exclude_stablecoins", True) and is_stablecoin(meta.base, cfg):
        return "stablecoin"
    if cfg.get("exclude_wrapped", True) and is_wrapped(meta.base, cfg):
        return "wrapped"
    if cfg.get("exclude_leveraged", True) and is_leveraged(meta.base, cfg):
        return "leveraged"
    if meta.quote.upper() not in {q.upper() for q in cfg.get("quote_currencies", ["USD", "USDT"])}:
        return "quote!=USD/USDT"
    return None


def dollar_volume(df: pd.DataFrame) -> pd.Series:
    """Daily USD volume proxy = close * base-units traded (USDT treated as ~USD)."""
    return df["close"] * df["volume"]


@dataclass
class UniverseSchedule:
    rebalance_dates: List[pd.Timestamp]
    eligible_by_date: Dict[pd.Timestamp, List[str]]
    top_tier_by_date: Dict[pd.Timestamp, List[str]]
    log: pd.DataFrame  # columns: rebalance_date, symbol, status, reason
    notes: List[str] = field(default_factory=list)


def build_schedule(
    panel: Dict[str, pd.DataFrame],
    metas: Dict[str, SymbolMeta],
    cfg_universe: dict,
    cfg_strategy: dict,
    rebalance_dates: List[pd.Timestamp],
) -> UniverseSchedule:
    min_vol = float(cfg_universe.get("min_24h_usd_volume", 50_000_000))
    liq_window = int(cfg_universe.get("liquidity_window_days", 7))
    min_hist = int(cfg_universe.get("min_history_days", 90))
    cap = int(cfg_universe.get("universe_size_cap", 50))
    lookback = int(cfg_strategy.get("xs_momentum_lookback", 30))
    top_frac = float(cfg_strategy.get("xs_top_tier_frac", 0.33))

    # Precompute per-symbol dollar-volume and static exclusions once.
    dvol = {sym: dollar_volume(df) for sym, df in panel.items()}
    static_reason = {sym: static_exclusion_reason(metas[sym], cfg_universe) for sym in panel}

    eligible_by_date: Dict[pd.Timestamp, List[str]] = {}
    top_tier_by_date: Dict[pd.Timestamp, List[str]] = {}
    log_rows: List[dict] = []
    spread_enforced = False  # daily candle feeds carry no spread; logged as not enforced

    for rb in rebalance_dates:
        scores: Dict[str, float] = {}
        eligible: List[str] = []
        for sym, df in panel.items():
            hist = df.loc[:rb]
            # date-independent exclusions
            if static_reason[sym] is not None:
                log_rows.append({"rebalance_date": rb, "symbol": sym, "status": "excluded", "reason": static_reason[sym]})
                continue
            meta = metas[sym]
            if pd.Timestamp(meta.data_start, tz="UTC") > rb:
                log_rows.append({"rebalance_date": rb, "symbol": sym, "status": "excluded", "reason": "not-listed-yet"})
                continue
            if meta.data_end is not None and pd.Timestamp(meta.data_end, tz="UTC") < rb:
                log_rows.append({"rebalance_date": rb, "symbol": sym, "status": "excluded", "reason": "delisted-before-date"})
                continue
            valid_closes = hist["close"].dropna()
            if len(valid_closes) < min_hist:
                log_rows.append({"rebalance_date": rb, "symbol": sym, "status": "excluded", "reason": "age<min_history"})
                continue
            liq = dvol[sym].loc[:rb].tail(liq_window).median()
            if not (liq >= min_vol):
                log_rows.append({"rebalance_date": rb, "symbol": sym, "status": "excluded", "reason": "vol<min_usd"})
                continue
            mom = pct_return(hist["close"], lookback)
            score = mom.loc[rb] if rb in mom.index else float("nan")
            if pd.isna(score):
                log_rows.append({"rebalance_date": rb, "symbol": sym, "status": "excluded", "reason": "no-momentum-score"})
                continue
            eligible.append(sym)
            scores[sym] = float(score)

        # universe size cap: keep the most liquid `cap` eligible symbols
        if len(eligible) > cap:
            liq_rank = sorted(eligible, key=lambda s: dvol[s].loc[:rb].tail(liq_window).median(), reverse=True)
            kept = set(liq_rank[:cap])
            for s in eligible:
                if s not in kept:
                    log_rows.append({"rebalance_date": rb, "symbol": s, "status": "excluded", "reason": "below-universe-cap"})
                    scores.pop(s, None)
            eligible = [s for s in eligible if s in kept]

        score_series = pd.Series(scores)
        tt = top_tier_mask(score_series, top_frac) if not score_series.empty else pd.Series(dtype=bool)
        top = [s for s in eligible if bool(tt.get(s, False))]
        for s in eligible:
            log_rows.append(
                {"rebalance_date": rb, "symbol": s, "status": "included",
                 "reason": "top-tier" if s in top else "eligible-not-top"}
            )
        eligible_by_date[rb] = eligible
        top_tier_by_date[rb] = top

    log = pd.DataFrame(log_rows, columns=["rebalance_date", "symbol", "status", "reason"])
    notes = []
    if not spread_enforced:
        notes.append("max_spread filter NOT enforced: daily OHLCV feeds carry no reliable spread data.")
    return UniverseSchedule(rebalance_dates, eligible_by_date, top_tier_by_date, log, notes)
