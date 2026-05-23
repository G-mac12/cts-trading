#!/usr/bin/env bash
# One-time setup for a fresh Ubuntu droplet. Makes the PAPER-trader run daily,
# hands-off, via a systemd timer. SIMULATED ONLY — never places real orders.
#
# Usage (from the repo root, as a sudo-capable user):
#   bash deploy/setup_droplet.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(whoami)"
echo "==> CTS droplet setup  (repo: $REPO, run-as user: $USER_NAME)"

echo "==> System packages (needs sudo)"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git rsync

echo "==> Python venv + dependencies"
cd "$REPO"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt
./.venv/bin/pip install --quiet -e .

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env — you MUST add COINAPI_KEY before the timer runs."
fi

echo "==> Installing systemd service + timer (daily 00:30 UTC, after the daily close)"
sudo tee /etc/systemd/system/cts-paper.service >/dev/null <<EOF
[Unit]
Description=CTS paper-trader daily update (SIMULATED, no real orders)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER_NAME
WorkingDirectory=$REPO
ExecStart=$REPO/.venv/bin/python scripts/run_paper.py --update
EOF

sudo tee /etc/systemd/system/cts-paper.timer >/dev/null <<EOF
[Unit]
Description=Run CTS paper-trader daily

[Timer]
OnCalendar=*-*-* 00:30:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now cts-paper.timer

echo
echo "==> Done. Timer status:"
systemctl list-timers cts-paper.timer --no-pager 2>/dev/null | head -3 || true
echo
echo "NEXT STEPS:"
echo "  1) Add your key:        nano $REPO/.env   (set COINAPI_KEY=...)"
echo "  2) (optional) alerts:   set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env"
echo "  3) Test it now:         $REPO/.venv/bin/python scripts/run_paper.py --update"
echo "  4) When does it run:    systemctl list-timers cts-paper.timer"
echo "  5) Logs:                journalctl -u cts-paper.service -n 50"
echo "  6) Status file:         cat $REPO/data/paper/PAPER_STATUS.md"
