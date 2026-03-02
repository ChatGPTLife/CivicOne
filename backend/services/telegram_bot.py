# 2025-02-26
"""
CivicOne Telegram Bot - Python port of the Node.js bot.
Runs as a standalone process; POSTs incidents to the backend API.
Uses asyncio.to_thread for blocking HTTP calls to avoid blocking the event loop.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

import requests
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest
from telegram.error import Conflict, TelegramError

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: CallbackContext) -> None:
    """Log errors and prevent bot crash."""
    logger.exception("Telegram bot error: %s", context.error)
    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Something went wrong. Please try /start again."
            )
        except TelegramError:
            pass

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def get_telegram_token() -> str:
    from config import Config
    return Config.TELEGRAM_BOT_TOKEN

# Map Telegram category strings to incident types
CATEGORY_TO_TYPE = {
    "Fire Incident": "fire",
    "Medical Emergency": "medical",
    "Road Accident": "road_accident",
    "Road Damage": "road_damage",
    "Garbage Issue": "garbage",
    "Public Safety Issue": "public_safety",
    "Theft": "theft",
    "Suspicious Activity": "suspicious",
    "Public Disturbance": "public_disturbance",
}

GREETINGS = {"hi", "hello", "hey"}
user_states: dict[int, dict] = {}

LOCK_PATH = os.getenv("TELEGRAM_BOT_LOCK_PATH", "/tmp/civicone-telegram-bot.lock")


def _acquire_single_instance_lock() -> None:
    """
    Ensure only one local bot process runs.

    Prevents Telegram Conflict errors caused by accidentally starting the bot twice.
    """
    pid_bytes = str(os.getpid()).encode("utf-8")
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        try:
            os.write(fd, pid_bytes)
        finally:
            os.close(fd)
        return
    except FileExistsError:
        other_pid = 0
        try:
            with open(LOCK_PATH, "rb") as f:
                raw = f.read().strip()
            other_pid = int(raw.decode("utf-8") or "0")
        except Exception:
            other_pid = 0

        if other_pid:
            try:
                os.kill(other_pid, 0)
                raise RuntimeError(
                    f"Telegram bot already running (pid={other_pid}). "
                    f"Stop it or delete lock file: {LOCK_PATH}"
                )
            except ProcessLookupError:
                pass
            except PermissionError:
                raise RuntimeError(f"Telegram bot lock exists. Delete lock file: {LOCK_PATH}")

        try:
            os.remove(LOCK_PATH)
        except Exception as e:
            raise RuntimeError(f"Could not remove stale lock file: {LOCK_PATH}: {e}")
        _acquire_single_instance_lock()


def _release_single_instance_lock() -> None:
    try:
        os.remove(LOCK_PATH)
    except Exception:
        pass


def _incident_type(category: str) -> str:
    return CATEGORY_TO_TYPE.get(category, category.lower().replace(" ", "_"))


def _post_incident_sync(payload: dict) -> dict | None:
    """Blocking HTTP call - run via asyncio.to_thread."""
    for attempt in range(2):
        try:
            r = requests.post(
                f"{API_BASE}/api/incidents/telegram",
                json=payload,
                timeout=(5, 15),
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("POST incident attempt %d failed: %s", attempt + 1, e)
            if attempt == 0:
                time.sleep(1)
            else:
                logger.exception("Failed to POST incident")
                return None
    return None


async def _post_incident(payload: dict) -> dict | None:
    """Non-blocking: runs HTTP in thread pool."""
    return await asyncio.to_thread(_post_incident_sync, payload)


def _post_api_sync(url: str, json_data: dict) -> bool:
    """Blocking HTTP call - run via asyncio.to_thread."""
    try:
        r = requests.post(url, json=json_data, timeout=8)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.warning("API call failed %s: %s", url, e)
        return False


async def start_bot_flow(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_states[chat_id] = {"state": "MAIN_MENU", "data": {}}
    if update.message:
        await update.message.reply_text("CivicOne\n\nWhat is your Emergency?")
    await show_main_menu(update, context)


async def show_main_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Emergency Response", callback_data="emergency")],
        [InlineKeyboardButton("Civic Infrastructure Issue", callback_data="civic")],
        [InlineKeyboardButton("Law & Order Report", callback_data="crime")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "Select a service:"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup)


async def show_emergency_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Fire Incident", callback_data="Fire Incident")],
        [InlineKeyboardButton("Medical Emergency", callback_data="Medical Emergency")],
        [InlineKeyboardButton("Road Accident", callback_data="Road Accident")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Emergency Type:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def show_civic_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Road / Pothole Damage", callback_data="Road Damage")],
        [InlineKeyboardButton("Garbage / Sanitation", callback_data="Garbage Issue")],
        [InlineKeyboardButton("Public Safety Issue", callback_data="Public Safety Issue")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Civic Issue Category:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def show_crime_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Theft", callback_data="Theft")],
        [InlineKeyboardButton("Suspicious Activity", callback_data="Suspicious Activity")],
        [InlineKeyboardButton("Public Disturbance", callback_data="Public Disturbance")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Report Type:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def confirm_complaint(update: Update, context: CallbackContext, chat_id: int) -> None:
    data = user_states[chat_id]["data"]
    report_id = f"CIV-{int(update.effective_message.date.timestamp() * 1000)}"

    loc = data.get("location") or {}
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    if lat is None or lng is None:
        await context.bot.send_message(chat_id, "Location is required. Please share your location.")
        return

    photo_file_id = None
    if data.get("photo"):
        photos = data["photo"]
        photo_file_id = photos[0].file_id if hasattr(photos[0], "file_id") else str(photos[0])

    video_file_id = None
    if data.get("video"):
        v = data["video"]
        video_file_id = v.file_id if hasattr(v, "file_id") else str(v)

    voice_file_id = None
    if data.get("voice"):
        v = data["voice"]
        voice_file_id = v.file_id if hasattr(v, "file_id") else str(v)

    payload = {
        "report_id": report_id,
        "type": _incident_type(data.get("category", "")),
        "category": data.get("category", ""),
        "latitude": float(lat),
        "longitude": float(lng),
        "photo_file_id": photo_file_id,
        "video_file_id": video_file_id,
        "voice_file_id": voice_file_id,
    }

    result = await _post_incident(payload)
    if result:
        await context.bot.send_message(
            chat_id,
            f"Report Successfully Registered\n\nReport ID: {report_id}\n"
            "Emergency services have been dispatched to your location.",
        )
    else:
        await context.bot.send_message(
            chat_id,
            "Report received. Our team will process it shortly. Report ID: " + report_id,
        )

    keyboard = [
        [InlineKeyboardButton("Request a Callback", callback_data=f"callback_{report_id}")],
        [InlineKeyboardButton("Add Additional Details", callback_data=f"details_{report_id}")],
        [InlineKeyboardButton("No, I'm Done", callback_data="done")],
    ]
    await context.bot.send_message(
        chat_id,
        "Would you like any of the following?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    user_states[chat_id]["last_report_id"] = report_id
    user_states[chat_id]["state"] = "POST_SUBMISSION"


async def handle_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    chat_id = query.message.chat.id if query.message else 0
    data = query.data or ""

    if data == "emergency":
        await show_emergency_menu(update, context)
        return
    if data == "civic":
        await show_civic_menu(update, context)
        return
    if data == "crime":
        await show_crime_menu(update, context)
        return
    if data == "back_main":
        await show_main_menu(update, context)
        return

    if data.startswith("callback_"):
        report_id = data.split("_", 1)[1]
        await asyncio.to_thread(
            _post_api_sync,
            f"{API_BASE}/api/callback-request",
            {"report_id": report_id},
        )
        await context.bot.send_message(chat_id, "Our team will contact you shortly.")
        user_states.pop(chat_id, None)
        return

    if data.startswith("details_"):
        await context.bot.send_message(chat_id, "Please type additional details:")
        user_states[chat_id]["state"] = "ADDING_DETAILS"
        return

    if data == "done":
        await context.bot.send_message(chat_id, "Thank you for using CivicOne.")
        user_states.pop(chat_id, None)
        return

    # Category selected
    if chat_id not in user_states:
        user_states[chat_id] = {"state": "MAIN_MENU", "data": {}}
    user_states[chat_id]["data"]["category"] = data
    user_states[chat_id]["state"] = "WAITING_FOR_LOCATION"

    keyboard = [[KeyboardButton("Share Location", request_location=True)]]
    await context.bot.send_message(
        chat_id,
        f"You selected: {data}\n\nPlease share the exact location.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
    )


async def handle_message(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id if update.effective_chat else 0
    text = (update.message.text or "").strip().lower()

    if text in GREETINGS and chat_id not in user_states:
        await start_bot_flow(update, context)
        return

    if chat_id not in user_states:
        return

    state = user_states[chat_id]["state"]
    data = user_states[chat_id]["data"]

    if state == "WAITING_FOR_LOCATION" and update.message.location:
        data["location"] = {
            "latitude": update.message.location.latitude,
            "longitude": update.message.location.longitude,
        }
        user_states[chat_id]["state"] = "WAITING_FOR_MEDIA"
        await context.bot.send_message(
            chat_id,
            "Upload supporting media (optional):\n• Photo\n• Video (max 30 sec)\n• Voice note\n\nOr type 'skip' to continue.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if state == "WAITING_FOR_MEDIA" and text == "skip":
        await confirm_complaint(update, context, chat_id)
        return

    if state == "WAITING_FOR_MEDIA" and update.message.photo:
        data["photo"] = update.message.photo
        await confirm_complaint(update, context, chat_id)
        return

    if state == "WAITING_FOR_MEDIA" and update.message.video:
        if update.message.video.duration and update.message.video.duration > 30:
            await context.bot.send_message(chat_id, "Video too long. Max 30 seconds allowed.")
            return
        data["video"] = update.message.video
        await confirm_complaint(update, context, chat_id)
        return

    if state == "WAITING_FOR_MEDIA" and update.message.voice:
        data["voice"] = update.message.voice
        await confirm_complaint(update, context, chat_id)
        return

    if state == "ADDING_DETAILS" and update.message.text:
        report_id = user_states[chat_id].get("last_report_id")
        await asyncio.to_thread(
            _post_api_sync,
            f"{API_BASE}/api/incidents/add-details",
            {"report_id": report_id, "additional_details": update.message.text},
        )
        await context.bot.send_message(chat_id, "Additional details added successfully.")
        user_states.pop(chat_id, None)


def run_bot() -> None:
    token = get_telegram_token()
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set. Bot will not start.")
        return

    _acquire_single_instance_lock()
    try:
        request = HTTPXRequest(
            connect_timeout=20,
            read_timeout=20,
            write_timeout=20,
            pool_timeout=5,
        )
        app = Application.builder().token(token).request(request).build()
        app.add_handler(CommandHandler("start", start_bot_flow))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(
            MessageHandler(
                filters.TEXT | filters.LOCATION | filters.PHOTO | filters.VIDEO | filters.VOICE,
                handle_message,
            )
        )
        app.add_error_handler(error_handler)

        logger.info("CivicOne Telegram Bot running...")
        try:
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
        except Conflict as e:
            logger.error(
                "Telegram Conflict: another getUpdates consumer is active for this token. "
                "Stop the other bot instance and retry. Error: %s",
                e,
            )
            time.sleep(2)
            raise
    finally:
        _release_single_instance_lock()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bot()
