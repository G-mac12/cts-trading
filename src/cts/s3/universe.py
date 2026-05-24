"""S3 universe — point-in-time, survivorship-clean, segmented. Separate from S1's
universe builder. Eligibility = ADV floor (30d avg $ volume) + listing age + not in
the fiat/stable/commodity exclude list; segment from config/s3_segments.yml.
"""
from __future__ import annotations

from typing import Dict, List

import pandas as pd
import yaml

from cts.config import CONFIG_DIR


class S3Universe:
    def __init__(self, panel: Dict[str, pd.DataFrame], metas: Dict, cfg_universe: dict):
        seg_cfg = yaml.safe_load((CONFIG_DIR / "s3_segments.yml").read_text())
        self.panel = panel
        self.metas = metas
        self.min_adv = float(cfg_universe["min_adv_usd"])
        self.adv_window = int(cfg_universe["adv_window_days"])
        self.min_age = int(cfg_universe["min_listing_age_days"])
        self.base_to_seg = {b.upper(): seg for seg, bs in seg_cfg["segments"].items() for b in bs}
        self.exclude = {b.upper() for b in seg_cfg.get("exclude", [])}
        self.adv = {s: (df["close"] * df["volume"]).rolling(
            self.adv_window, min_periods=max(10, self.adv_window // 2)).mean() for s, df in panel.items()}
        self.first_date = {s: df.index.min() for s, df in panel.items()}

    def segment(self, sym: str) -> str:
        return self.base_to_seg.get(self.metas[sym].base.upper(), "other")

    def adv_at(self, sym: str, date: pd.Timestamp) -> float:
        s = self.adv[sym]
        s = s[s.index <= date].dropna()
        return float(s.iloc[-1]) if len(s) else 0.0

    def eligible_frame(self, dates: pd.DatetimeIndex) -> pd.DataFrame:
        """Boolean (dates x coins) eligibility, vectorised — for the hot rotation loop.
        Eligible = ADV>=floor, >=min_age old, alive (not delisted before date), excludes
        fiat/stable/commodity."""
        idx = pd.DatetimeIndex(dates)
        cols = [s for s in self.panel if self.metas[s].base.upper() not in self.exclude]
        adv_wide = pd.DataFrame({s: self.adv[s] for s in cols}).reindex(idx).ffill()
        elig = (adv_wide >= self.min_adv) & adv_wide.notna()
        for s in cols:
            fd, ld = self.first_date[s], self.panel[s].index.max()
            alive = (idx >= fd + pd.Timedelta(days=self.min_age)) & (idx <= ld + pd.Timedelta(days=10))
            elig[s] = elig[s] & alive
        return elig.fillna(False)

    def eligible(self, date: pd.Timestamp) -> List[str]:
        row = self.eligible_frame(pd.DatetimeIndex([pd.Timestamp(date)])).iloc[0]
        return [s for s in row.index if bool(row[s])]
