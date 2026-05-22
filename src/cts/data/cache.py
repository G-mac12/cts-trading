"""Local parquet cache + manifest. Backtests read ONLY from cache so a run is
reproducible and re-running never silently changes inputs. The manifest records
source, pull time, and per-symbol coverage for the audit trail in FINDINGS.md."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import pandas as pd


class Cache:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe(symbol_id: str) -> str:
        return symbol_id.replace("/", "_").replace("\\", "_")

    def _dir(self, source: str) -> Path:
        d = self.root / source
        d.mkdir(parents=True, exist_ok=True)
        return d

    def path(self, source: str, symbol_id: str, granularity: str = "1DAY") -> Path:
        return self._dir(source) / f"{self._safe(symbol_id)}__{granularity}.parquet"

    def has(self, source: str, symbol_id: str, granularity: str = "1DAY") -> bool:
        return self.path(source, symbol_id, granularity).exists()

    def read(self, source: str, symbol_id: str, granularity: str = "1DAY") -> pd.DataFrame:
        return pd.read_parquet(self.path(source, symbol_id, granularity))

    def write(self, source: str, symbol_id: str, df: pd.DataFrame, granularity: str = "1DAY") -> None:
        df.to_parquet(self.path(source, symbol_id, granularity))

    def write_manifest(self, source: str, payload: Dict) -> None:
        payload = dict(payload)
        payload["written_at"] = datetime.now(timezone.utc).isoformat()
        (self._dir(source) / "manifest.json").write_text(json.dumps(payload, indent=2, default=str))

    def read_manifest(self, source: str) -> Optional[Dict]:
        p = self._dir(source) / "manifest.json"
        return json.loads(p.read_text()) if p.exists() else None
