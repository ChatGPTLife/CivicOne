#!/usr/bin/env python3
# 2025-02-26
"""
Run the CivicOne Telegram bot (Python). Start this in a separate terminal.
Requires the backend (app.py) to be running on port 8000 for incident submission.

If the Python bot is laggy, try the Node.js version instead:
  cd telegram-bot && npm install && TELEGRAM_BOT_TOKEN=xxx npm start
"""
import os
import sys

# Add backend to path so we can import services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    from services.telegram_bot import run_bot
    run_bot()
