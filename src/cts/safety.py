"""Backtest-only guardrails (hard constraint §0/§2). Phase 1 never connects to
Kraken and never places an order. If Kraken credentials happen to be present in
the environment we say so loudly and ignore them."""
from __future__ import annotations

import os

from cts.config import load_env

_KRAKEN_HINTS = ("KRAKEN_API_KEY", "KRAKEN_PRIVATE_KEY", "KRAKEN_SECRET", "KRAKEN_API_SECRET")


def backtest_only_notice() -> str:
    load_env()
    present = [k for k in _KRAKEN_HINTS if os.environ.get(k)]
    msg = "Phase 1 is BACKTEST-ONLY: no Kraken connection, no live/paper orders, market-data reads only."
    if present:
        msg += (" Kraken credentials detected in env (" + ", ".join(present) +
                ") — they are IGNORED here and no trade endpoint is ever called.")
    return msg
