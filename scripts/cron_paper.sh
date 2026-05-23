#!/usr/bin/env bash
# Daily paper-trader update. Pulls the latest candles and advances the forward
# record. Safe to miss days — update_cache catches up from the last cached date.
# SIMULATED ONLY: no real orders.
#
# Enable (runs daily at 02:00 local):
#   crontab -l 2>/dev/null | grep -q cron_paper.sh || \
#     (crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/scripts/cron_paper.sh") | crontab -
# Disable:
#   crontab -l | grep -v cron_paper.sh | crontab -
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/paper
.venv/bin/python scripts/run_paper.py --update >> data/paper/daily.log 2>&1
echo "$(date -u +%FT%TZ) paper updated" >> data/paper/daily.log
