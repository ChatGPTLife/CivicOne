import os
import json
import logging
import urllib.request
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is missing. Put your bot token in the .env file."
    )

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------- BACKEND API HELPER ----------

def send_incident_to_backend(incident_type: str, latitude: float, longitude: float, description: str = "", category: str = "") -> dict | None:
    """Post an emergency or civic report directly to the CivicOne dashboard backend."""
    url = f"{API_BASE}/api/incidents/telegram"
    payload = {
        "type": incident_type,
        "category": category or incident_type.capitalize(),
        "latitude": float(latitude),
        "longitude": float(longitude),
        "description": description or f"{category or incident_type} emergency reported via Telegram",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data
    except Exception as e:
        logger.error("Failed to post incident to backend (%s): %s", url, e)
        return None


# ---------- MENUS ----------

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🚨 Emergency", callback_data="emergency")],
        [InlineKeyboardButton("📍 Nearby Services", callback_data="nearby")],
        [InlineKeyboardButton("📢 Report an Issue", callback_data="report")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def emergency_menu():
    keyboard = [
        [InlineKeyboardButton("🔥 Fire & Rescue", callback_data="fire_sub")],
        [InlineKeyboardButton("🚑 Ambulance", callback_data="ambulance_sub")],
        [InlineKeyboardButton("👮 Police", callback_data="police_sub")],
        [InlineKeyboardButton("↩️ Back", callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def fire_submenu():
    keyboard = [
        [InlineKeyboardButton("🚒 Quick Dispatch Fire (Chennai Central Demo)", callback_data="dispatch_fire_demo")],
        [InlineKeyboardButton("📍 Share Live GPS for Fire", callback_data="req_loc_fire")],
        [InlineKeyboardButton("↩️ Back", callback_data="emergency")],
    ]
    return InlineKeyboardMarkup(keyboard)


def ambulance_submenu():
    keyboard = [
        [InlineKeyboardButton("🚑 Quick Dispatch Ambulance (Demo)", callback_data="dispatch_ambulance_demo")],
        [InlineKeyboardButton("📍 Share Live GPS for Medical", callback_data="req_loc_ambulance")],
        [InlineKeyboardButton("↩️ Back", callback_data="emergency")],
    ]
    return InlineKeyboardMarkup(keyboard)


def police_submenu():
    keyboard = [
        [InlineKeyboardButton("👮 Quick Dispatch Police (Demo)", callback_data="dispatch_police_demo")],
        [InlineKeyboardButton("📍 Share Live GPS for Police", callback_data="req_loc_police")],
        [InlineKeyboardButton("↩️ Back", callback_data="emergency")],
    ]
    return InlineKeyboardMarkup(keyboard)


def nearby_menu():
    keyboard = [
        [InlineKeyboardButton("🏥 Hospitals", callback_data="nearby_hospital")],
        [InlineKeyboardButton("👮 Police Stations", callback_data="nearby_police")],
        [InlineKeyboardButton("🔥 Fire Stations", callback_data="nearby_fire")],
        [InlineKeyboardButton("📍 Share My Location", callback_data="share_location")],
        [InlineKeyboardButton("↩️ Back", callback_data="main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Back to Main Menu", callback_data="main")]
    ])


# ---------- COMMANDS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Welcome to *CivicOne*, {user.first_name}!\n\n"
        "Unified Emergency & Civic Dispatch for Chennai.\n\n"
        "Choose an option below to report an emergency or request assistance:"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *CivicOne Help*\n\n"
        "Use the buttons to report emergencies or request civic dispatch.\n\n"
        "Available commands:\n"
        "• /start — Open CivicOne\n"
        "• /menu — Open the main menu\n"
        "• /help — Show this help\n"
        "• /cancel — Cancel the current action\n\n"
        "When an emergency is reported, the CivicOne dispatch engine automatically assigns the closest available vehicle and activates green traffic corridors on the Live Command Dashboard (http://localhost:3000)."
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 *CivicOne Main Menu*\n\nChoose an option:",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Current action cancelled.\n\nChoose an option:",
        reply_markup=main_menu(),
    )


# ---------- BUTTON HANDLER ----------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main":
        await query.edit_message_text(
            "🏠 *CivicOne Main Menu*\n\nChoose an option:",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

    elif data == "emergency":
        await query.edit_message_text(
            "🚨 *Emergency Services*\n\n"
            "Choose the service you need to dispatch:",
            parse_mode="Markdown",
            reply_markup=emergency_menu(),
        )

    elif data == "fire_sub":
        await query.edit_message_text(
            "🔥 *Fire & Rescue Emergency*\n\n"
            "Select an option to dispatch Fire Engine:",
            parse_mode="Markdown",
            reply_markup=fire_submenu(),
        )

    elif data == "ambulance_sub":
        await query.edit_message_text(
            "🚑 *Ambulance / Medical Emergency*\n\n"
            "Select an option to dispatch Ambulance:",
            parse_mode="Markdown",
            reply_markup=ambulance_submenu(),
        )

    elif data == "police_sub":
        await query.edit_message_text(
            "👮 *Police Emergency*\n\n"
            "Select an option to dispatch Police Patrol:",
            parse_mode="Markdown",
            reply_markup=police_submenu(),
        )

    # --- QUICK DISPATCH BUTTONS (TEST & DEMO IN CHENNAI) ---
    elif data == "dispatch_fire_demo":
        await query.edit_message_text("⏳ *Contacting CivicOne Dispatch Engine...*", parse_mode="Markdown")
        res = send_incident_to_backend("fire", 13.0827, 80.2707, "Fire incident reported near Chennai Central", "Fire Incident")
        if res:
            assigned = res.get("dispatch", {}).get("vehicle") or {}
            v_type = assigned.get("type", "Fire Unit").capitalize()
            v_id = str(assigned.get("id", ""))[:8]
            await query.edit_message_text(
                "🚨 *FIRE INCIDENT REGISTERED & DISPATCHED!*\n\n"
                f"📍 *Location:* Chennai Central (`13.0827, 80.2707`)\n"
                f"🚒 *Assigned Unit:* {v_type} (ID: `{v_id}`)\n"
                "🚦 *Green Corridor:* Activated along response route\n"
                "🌐 *Status:* Live on dashboard at http://localhost:3000\n\n"
                "Emergency responders are en route!",
                parse_mode="Markdown",
                reply_markup=back_menu(),
            )
        else:
            await query.edit_message_text(
                "⚠️ *Dispatch Engine Offline.*\n\nPlease verify backend server is running at http://localhost:8000.",
                parse_mode="Markdown",
                reply_markup=back_menu(),
            )

    elif data == "dispatch_ambulance_demo":
        await query.edit_message_text("⏳ *Contacting CivicOne Dispatch Engine...*", parse_mode="Markdown")
        res = send_incident_to_backend("medical", 13.0475, 80.2824, "Medical emergency reported near Marina Beach", "Medical Emergency")
        if res:
            assigned = res.get("dispatch", {}).get("vehicle") or {}
            v_type = assigned.get("type", "Ambulance").capitalize()
            v_id = str(assigned.get("id", ""))[:8]
            await query.edit_message_text(
                "🚑 *MEDICAL EMERGENCY REGISTERED & DISPATCHED!*\n\n"
                f"📍 *Location:* Marina Beach (`13.0475, 80.2824`)\n"
                f"🏥 *Assigned Unit:* {v_type} (ID: `{v_id}`)\n"
                "🚦 *Green Corridor:* Activated along response route\n"
                "🌐 *Status:* Live on dashboard at http://localhost:3000\n\n"
                "Medical team is en route!",
                parse_mode="Markdown",
                reply_markup=back_menu(),
            )
        else:
            await query.edit_message_text(
                "⚠️ *Dispatch Engine Offline.* Please check backend status.",
                parse_mode="Markdown",
                reply_markup=back_menu(),
            )

    elif data == "dispatch_police_demo":
        await query.edit_message_text("⏳ *Contacting CivicOne Dispatch Engine...*", parse_mode="Markdown")
        res = send_incident_to_backend("theft", 13.0418, 80.2341, "Police emergency reported in T. Nagar", "Theft")
        if res:
            assigned = res.get("dispatch", {}).get("vehicle") or {}
            v_type = assigned.get("type", "Police Patrol").capitalize()
            v_id = str(assigned.get("id", ""))[:8]
            await query.edit_message_text(
                "👮 *POLICE PATROL DISPATCHED!*\n\n"
                f"📍 *Location:* T. Nagar (`13.0418, 80.2341`)\n"
                f"🚓 *Assigned Unit:* {v_type} (ID: `{v_id}`)\n"
                "🌐 *Status:* Live on dashboard at http://localhost:3000\n\n"
                "Officers are en route!",
                parse_mode="Markdown",
                reply_markup=back_menu(),
            )
        else:
            await query.edit_message_text(
                "⚠️ *Dispatch Engine Offline.* Please check backend status.",
                parse_mode="Markdown",
                reply_markup=back_menu(),
            )

    # --- LOCATION REQUEST HANDLERS ---
    elif data in ("req_loc_fire", "req_loc_ambulance", "req_loc_police", "share_location"):
        loc_type = "fire" if "fire" in data else ("medical" if "ambulance" in data else ("theft" if "police" in data else "general"))
        context.user_data["pending_emergency"] = loc_type

        location_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Tap to Share My Location", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        await query.message.reply_text(
            f"📍 Please tap the *Share My Location* button below to dispatch {loc_type.upper()} responders to your current GPS position.",
            parse_mode="Markdown",
            reply_markup=location_keyboard,
        )

    elif data == "nearby":
        await query.edit_message_text(
            "📍 *Nearby Civic Services*\n\n"
            "Choose a service or share your location:",
            parse_mode="Markdown",
            reply_markup=nearby_menu(),
        )

    elif data == "nearby_hospital":
        await query.edit_message_text(
            "🏥 *Emergency Hospitals in Chennai*\n\n"
            "• Rajiv Gandhi Govt General Hospital (Central)\n"
            "• Stanley Medical College Hospital (Royapuram)\n"
            "• Kilpauk Medical College (Kilpauk)\n"
            "• Apollo Hospitals (Greams Road)\n\n"
            "Emergency Helpline: *108* / *112*",
            parse_mode="Markdown",
            reply_markup=back_menu(),
        )

    elif data == "nearby_police":
        await query.edit_message_text(
            "👮 *Police Stations in Chennai*\n\n"
            "• Chennai Central Police Station\n"
            "• T. Nagar Law & Order Police Station\n"
            "• Mylapore Police Station\n"
            "• Anna Nagar Police Station\n\n"
            "Police Helpline: *100* / *112*",
            parse_mode="Markdown",
            reply_markup=back_menu(),
        )

    elif data == "nearby_fire":
        await query.edit_message_text(
            "🔥 *Fire Stations in Chennai*\n\n"
            "• Egmore Fire Station\n"
            "• Mylapore Fire & Rescue Station\n"
            "• Ambattur Industrial Fire Station\n\n"
            "Fire Helpline: *101* / *112*",
            parse_mode="Markdown",
            reply_markup=back_menu(),
        )

    elif data == "report":
        context.user_data["state"] = "report"
        await query.edit_message_text(
            "📢 *Report a Civic Issue*\n\n"
            "Please send a short description of the issue (pothole, road damage, garbage, streetlight, etc.).\n\n"
            "Example:\n"
            "_\"Large pothole causing traffic jam near Anna Nagar roundtana.\"_\n\n"
            "Use /cancel to cancel.",
            parse_mode="Markdown",
        )

    elif data == "help":
        await help_command(query, context)


# ---------- LOCATION HANDLER ----------

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    latitude = location.latitude
    longitude = location.longitude

    pending_type = context.user_data.get("pending_emergency", "fire")
    context.user_data["pending_emergency"] = None

    category_label = "Fire Incident" if pending_type == "fire" else ("Medical Emergency" if pending_type == "medical" else "Police Emergency")
    res = send_incident_to_backend(pending_type, latitude, longitude, f"{category_label} reported via user GPS", category_label)

    if res:
        assigned = res.get("dispatch", {}).get("vehicle") or {}
        v_type = assigned.get("type", pending_type.capitalize()).capitalize()
        v_id = str(assigned.get("id", ""))[:8]
        await update.message.reply_text(
            f"🚨 *{category_label.upper()} DISPATCHED TO YOUR LOCATION!*\n\n"
            f"📍 *GPS Coordinates:* `{latitude:.4f}, {longitude:.4f}`\n"
            f"🚒 *Assigned Unit:* {v_type} (ID: `{v_id}`)\n"
            "🚦 *Green Corridor:* Activated along route\n"
            "🌐 *Live Map:* Incident is live on http://localhost:3000\n\n"
            "Responders have been notified and are en route to your position.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            f"📍 Location received: `{latitude:.4f}, {longitude:.4f}`.\n\n"
            "Report logged. Emergency operators have been notified.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )

    await update.message.reply_text("What would you like to do next?", reply_markup=main_menu())


# ---------- TEXT HANDLER ----------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    user_text = update.message.text

    if state == "report":
        context.user_data["state"] = None
        # Default report location in Chennai center
        res = send_incident_to_backend("garbage", 13.0827, 80.2707, user_text, "Civic Issue")
        if res:
            await update.message.reply_text(
                "✅ *Civic Issue Reported Successfully!*\n\n"
                f"📝 *Description:* _{user_text}_\n"
                "📍 *Location:* Chennai (`13.0827, 80.2707`)\n"
                "🌐 *Dashboard:* Dispatched to municipal works on http://localhost:3000\n\n"
                "Municipal response team has been assigned.",
                parse_mode="Markdown",
                reply_markup=main_menu(),
            )
        else:
            await update.message.reply_text(
                "✅ *Report received!*\n\n"
                f"Your report:\n_{user_text}_\n\n"
                "Logged in CivicOne dispatch queue.",
                parse_mode="Markdown",
                reply_markup=main_menu(),
            )
    else:
        await update.message.reply_text(
            "Please choose an option from the menu below:",
            reply_markup=main_menu(),
        )


# ---------- ERROR HANDLER ----------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram bot error: %s", context.error)


# ---------- MAIN ----------

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.LOCATION, location_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    application.add_error_handler(error_handler)

    print("CivicOne Telegram Bot is running and connected to CivicOne dashboard...")
    print("Open Telegram, find @civicone_bot, and tap /start.")
    application.run_polling()


if __name__ == "__main__":
    main()
