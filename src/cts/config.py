"""Config + secret loading. Tiny .env parser (no extra dependency); secrets are
read at runtime from .env (git-ignored) and never logged or committed."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


def load_env(path: Path | None = None) -> Dict[str, str]:
    """Parse .env into os.environ (without overriding already-set vars)."""
    path = Path(path) if path else ROOT / ".env"
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        env[key] = val
        os.environ.setdefault(key, val)
    return env


def get_secret(name: str) -> str:
    load_env()
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Missing secret {name!r}. Copy .env.example to .env and set it. "
            "(Phase 1 needs only a data-vendor key; no Kraken key required.)"
        )
    return val


def load_yaml(name: str) -> Dict[str, Any]:
    return yaml.safe_load((CONFIG_DIR / name).read_text())


def universe_config() -> Dict[str, Any]:
    return load_yaml("universe.yml")


def backtest_config() -> Dict[str, Any]:
    return load_yaml("backtest.yml")
