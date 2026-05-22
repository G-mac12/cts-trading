"""CoinAPI adapter (primary, survivorship-clean).

Why CoinAPI for the gate: its symbol metadata includes delisted/inactive markets
with honest data_start/data_end, so the point-in-time Kraken universe (including
pairs Kraken later delisted) can be reconstructed. That is exactly what §9 needs.

Read-only market-data calls only. No trading endpoints exist on CoinAPI; this
adapter never touches Kraken's API at all.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import pandas as pd
import requests

from cts.data.adapter import OHLCV_COLUMNS, DataAdapter, SymbolMeta

BASE_URL = "https://rest.coinapi.io/v1"
# A symbol whose data_end is older than this many days from "now" is treated as delisted.
_ACTIVE_GRACE_DAYS = 14


def _parse_dt(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()


class CoinAPIAdapter(DataAdapter):
    survivorship_clean = True
    source_name = "coinapi"

    def __init__(self, api_key: str, exchange: str = "KRAKEN", timeout: int = 60):
        if not api_key:
            raise ValueError("CoinAPI key required")
        self.exchange = exchange
        self.timeout = timeout
        self.total_request_cost = 0  # sum of x-ratelimit-request-cost (credits spent)
        self._session = requests.Session()
        self._session.headers.update({"X-CoinAPI-Key": api_key, "Accept": "application/json"})

    def _get(self, path: str, params: Optional[dict] = None, max_retries: int = 5):
        url = f"{BASE_URL}{path}"
        for attempt in range(max_retries):
            resp = self._session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 429:  # rate limited -> respect reset / back off
                wait = float(resp.headers.get("Retry-After", 2 ** attempt))
                time.sleep(min(wait, 60))
                continue
            if resp.status_code == 550:  # CoinAPI "no data" sentinel
                return []
            resp.raise_for_status()
            try:
                self.total_request_cost += int(resp.headers.get("x-ratelimit-request-cost", 0))
            except (TypeError, ValueError):
                pass
            return resp.json()
        raise RuntimeError(f"CoinAPI rate limit not cleared after {max_retries} retries: {path}")

    def _to_meta(self, s: dict, today, with_volume: bool) -> Optional[SymbolMeta]:
        if s.get("symbol_type") != "SPOT":
            return None
        quote = (s.get("asset_id_quote") or "").upper()
        if quote not in ("USD", "USDT"):
            return None
        dstart = _parse_dt(s.get("data_start"))
        if dstart is None:
            return None
        dend = _parse_dt(s.get("data_end"))
        active = dend is not None and (today - dend) <= timedelta(days=_ACTIVE_GRACE_DAYS)
        vol = 0.0
        if with_volume:
            try:
                vol = float(s.get("volume_1day_usd") or 0.0)
            except (TypeError, ValueError):
                vol = 0.0
        return SymbolMeta(
            symbol_id=s["symbol_id"], base=(s.get("asset_id_base") or "").upper(), quote=quote,
            exchange=self.exchange, data_start=dstart, data_end=None if active else dend,
            is_active=active, recent_volume_usd=vol,
        )

    def list_symbols(self) -> List[SymbolMeta]:
        """Survivorship-clean USD/USDT spot universe = current listings (with live USD
        volume) UNION delisted symbols (from the history endpoint, which carries the
        coins that later went to zero or left Kraken)."""
        today = datetime.now(timezone.utc).date()
        out: dict = {}
        # current/active set — carries volume_1day_usd for ingest scoping
        for s in self._get("/symbols", params={"filter_exchange_id": self.exchange}):
            m = self._to_meta(s, today, with_volume=True)
            if m is not None:
                out[m.symbol_id] = m
        # historical set — adds delisted coins not present in the current snapshot
        for s in self._get(f"/symbols/{self.exchange}/history", params={"limit": 100000}):
            m = self._to_meta(s, today, with_volume=False)
            if m is not None and m.symbol_id not in out:
                out[m.symbol_id] = m
        return list(out.values())

    def daily_ohlcv(self, symbol_id: str, start: date, end: date) -> pd.DataFrame:
        params = {
            "period_id": "1DAY",
            "time_start": f"{start.isoformat()}T00:00:00",
            "time_end": f"{end.isoformat()}T00:00:00",
            "limit": 100000,
        }
        rows = self._get(f"/ohlcv/{symbol_id}/history", params=params)
        if not rows:
            return pd.DataFrame(columns=OHLCV_COLUMNS, index=pd.DatetimeIndex([], tz="UTC"))
        df = pd.DataFrame(rows)
        idx = pd.to_datetime(df["time_period_start"], utc=True).dt.normalize()
        out = pd.DataFrame(
            {
                "open": df["price_open"].astype("float64"),
                "high": df["price_high"].astype("float64"),
                "low": df["price_low"].astype("float64"),
                "close": df["price_close"].astype("float64"),
                "volume": df["volume_traded"].astype("float64"),
            },
            index=idx,
        )
        out.index.name = "date"
        return out[~out.index.duplicated(keep="last")].sort_index()
