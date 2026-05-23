from __future__ import annotations

from cts.notify import paper_summary_line, send


def test_send_is_noop_without_config(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    # also stop load_env() from repopulating from a local .env during the test
    monkeypatch.setattr("cts.notify.load_env", lambda *a, **k: {})
    assert send("hello") is False  # not configured -> no-op, no crash


def test_paper_summary_line():
    report = {
        "as_of": "2026-05-22",
        "variants": {
            "S1-baseline": {"forward_metrics": {"total_return": 0.05}, "n_forward_trades": 3,
                            "open_positions": [{"symbol": "X"}]},
        },
    }
    line = paper_summary_line(report)
    assert "2026-05-22" in line and "S1-baseline" in line and "+5.0%" in line and "3 trades" in line
