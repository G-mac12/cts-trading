"""Optional Telegram notifier — a heartbeat so an unattended run can tell you it's
alive and what it did, without you logging into the server. Config-gated: a no-op
(returns False) when TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID aren't set, so nothing
breaks if you don't use it. Read-only outbound message; never places orders."""
from __future__ import annotations

import os

from cts.config import load_env


def send(message: str, timeout: int = 20) -> bool:
    """Send a Telegram message if configured. Returns True if sent, False if not
    configured, and swallows network errors (a notifier must never crash the run)."""
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False
    try:
        import requests

        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            timeout=timeout,
        )
        return resp.status_code == 200
    except Exception:
        return False


def paper_summary_line(report: dict) -> str:
    """One-line status from a paper report (for the daily heartbeat)."""
    bits = [f"CTS paper {report['as_of']} (SIM, no real money)"]
    for name, v in report["variants"].items():
        m = v["forward_metrics"]
        bits.append(f"{name}: {m['total_return'] * 100:+.1f}% / {int(v['n_forward_trades'])} trades / "
                    f"{len(v['open_positions'])} open")
    return "\n".join(bits)
