# CivicOne Telegram Bot

## 1. Install Python

Use Python 3.10+.

## 2. Open this folder in a terminal

```text
civicone_telegram_bot
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Add your bot token

Copy `.env.example` to `.env`:

```text
TELEGRAM_BOT_TOKEN=YOUR_REAL_BOT_TOKEN
```

Do not share `.env` or upload it to GitHub.

## 5. Run

```bash
python bot.py
```

You should see:

```text
CivicOne Telegram bot is running...
Press Ctrl+C to stop.
```

Then open your bot in Telegram and send:

```text
/start
```

## Current menu

- Emergency
  - Police
  - Ambulance
  - Fire & Rescue
- Nearby Services
  - Hospitals
  - Police Stations
  - Fire Stations
  - Share Location
- Report an Issue
- Help

The nearby-service sections currently contain placeholders for an external location/API service. The report is currently kept in the user's session only; a database can be added next.
