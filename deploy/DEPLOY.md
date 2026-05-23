# Deploy CTS paper-trader to a droplet (24/7, hands-off)

This runs the **paper-trader** (SIMULATED — no real orders, no real money) on an
always-on cloud server so it builds the forward record without your laptop. Real
live trading is a separate, later, deliberate step — not this.

## What you need (one-time)
1. **DigitalOcean account** + a basic droplet — **Ubuntu 24.04, ~$6/mo** (1GB RAM is plenty).
   Add your SSH key during creation.
2. **Your CoinAPI key** (already in your local `.env`).
3. *(optional)* **Telegram bot** for a daily "it's alive" message — create one via
   `@BotFather` (token) and get your chat id from `@userinfobot`.

> No database/Supabase needed for this — the forward record lives in files on the
> droplet, and the optional Telegram ping tells you what happened each day.

## Steps (~10 minutes)
1. **Create the droplet** on DigitalOcean (Ubuntu 24.04, $6/mo, your SSH key).
   Note its IP.

2. **Get the code onto it.** Easiest is rsync from your Mac (no GitHub auth needed
   on the server). From your local repo folder:
   ```bash
   rsync -av --exclude .venv --exclude data/cache --exclude .git \
     ./ root@DROPLET_IP:/root/cts-trading/
   ```
   (Or `git clone` it if you set up a read-only deploy key.)

3. **SSH in and run setup:**
   ```bash
   ssh root@DROPLET_IP
   cd cts-trading
   bash deploy/setup_droplet.sh
   ```

4. **Add your key:**
   ```bash
   nano .env        # set COINAPI_KEY=...   (and optional TELEGRAM_* for alerts)
   ```

5. **Test it once:**
   ```bash
   .venv/bin/python scripts/run_paper.py --update
   ```
   You should see the paper status table (and a Telegram ping if configured).

Done. It now runs **every day at 00:30 UTC**, automatically, forever.

## Checking on it (whenever you feel like it)
- Next scheduled run: `systemctl list-timers cts-paper.timer`
- Last run's logs: `journalctl -u cts-paper.service -n 50`
- Plain status: `cat data/paper/PAPER_STATUS.md`
- Pull the status to your Mac: `scp root@DROPLET_IP:cts-trading/data/paper/PAPER_STATUS.md .`

## Turn it off
```bash
sudo systemctl disable --now cts-paper.timer
```

## Prefer I do it?
Create the droplet and send me its IP + SSH access, and I'll run steps 2–5 for you.
(You keep control of the key: I'll have you paste `COINAPI_KEY` into `.env` yourself,
or you add it after.)

---
**Reminder:** this is paper/simulation only. Going live with real money is Phase 7 —
gated behind the paper record proving out and your explicit go-live decision.
