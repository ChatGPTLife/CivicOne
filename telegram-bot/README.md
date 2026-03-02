<!-- 2025-02-26 -->
# CivicOne Telegram Bot (Node.js)

Async-first implementation. Handles load well and is less prone to lag.

## Setup

```bash
cd telegram-bot
npm install
cp .env.example .env
# Edit .env and add your TELEGRAM_BOT_TOKEN (from @BotFather)
```

## Run

```bash
npm start
```

## 409 Conflict Error

**Only ONE bot instance can run at a time.** If you get "409 Conflict: terminated by other getUpdates request":

1. Stop all bots:
   ```bash
   npm run stop-others
   ```
   Or manually: `pkill -f run_telegram_bot` (Python) and `pkill -f telegram-bot` (Node)

2. Remove stale lock: `rm /tmp/civicone-telegram-bot.lock`

3. Start again: `npm start`

## Backend Required

The Flask backend (app.py) must be running on port 8000 for incident submission. If the backend is down, the bot will still respond but reports won't reach the dashboard.
