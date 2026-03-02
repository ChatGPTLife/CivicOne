// 2025-02-26
require("dotenv").config();

/**
 * CivicOne Telegram Bot - Node.js version
 * Async by default, handles load well. Run: npm start
 * Requires backend (app.py) on port 8000.
 *
 * IMPORTANT: Only ONE bot instance (Python OR Node) can run at a time.
 * Stop the Python bot before starting this: pkill -f run_telegram_bot
 */
const fs = require("fs");
const path = require("path");
const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";
const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
if (!TOKEN) {
  console.error("ERROR: TELEGRAM_BOT_TOKEN is required. Set it in .env or environment.");
  process.exit(1);
}

const LOCK_PATH = process.env.TELEGRAM_BOT_LOCK_PATH || "/tmp/civicone-telegram-bot.lock";

function acquireLock() {
  try {
    fs.writeFileSync(LOCK_PATH, String(process.pid), { flag: "wx" });
    return true;
  } catch (err) {
    if (err.code === "EEXIST") {
      let otherPid;
      try {
        otherPid = parseInt(fs.readFileSync(LOCK_PATH, "utf8"), 10);
      } catch {
        otherPid = 0;
      }
      try {
        process.kill(otherPid, 0);
        console.error(
          `ERROR: Another bot is already running (pid=${otherPid}).\n` +
            `Stop it first: kill ${otherPid}\n` +
            `Or delete lock: rm ${LOCK_PATH}`
        );
        process.exit(1);
      } catch (e) {
        if (e.code === "ESRCH") {
          fs.unlinkSync(LOCK_PATH);
          return acquireLock();
        }
      }
    }
    throw err;
  }
}

function releaseLock() {
  try {
    fs.unlinkSync(LOCK_PATH);
  } catch {}
}

process.on("exit", releaseLock);
process.on("SIGINT", () => {
  releaseLock();
  process.exit();
});
process.on("SIGTERM", () => {
  releaseLock();
  process.exit();
});

acquireLock();

const CATEGORY_TO_TYPE = {
  "Fire Incident": "fire",
  "Medical Emergency": "medical",
  "Road Accident": "road_accident",
  "Road Damage": "road_damage",
  "Garbage Issue": "garbage",
  "Public Safety Issue": "public_safety",
  Theft: "theft",
  "Suspicious Activity": "suspicious",
  "Public Disturbance": "public_disturbance",
};

const GREETINGS = new Set(["hi", "hello", "hey"]);
const userStates = new Map();


const bot = new TelegramBot(TOKEN, {
  polling: { drop_pending_updates: true },
  request: { timeout: 20000 },
});

const axiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 8000,
  validateStatus: () => true,
});

async function postIncident(payload) {
  try {
    const res = await axiosInstance.post("/api/incidents/telegram", payload);
    if (res.status >= 200 && res.status < 300) return res.data;
    console.error("POST incident failed:", res.status, res.data);
    return null;
  } catch (err) {
    console.error("POST incident failed:", err.code || err.message);
    return null;
  }
}

async function postApi(path, body) {
  try {
    await axiosInstance.post(path, body, { timeout: 8000 });
    return true;
  } catch (err) {
    console.warn("API call failed:", path, err.message);
    return false;
  }
}

function incidentType(category) {
  return CATEGORY_TO_TYPE[category] || category.toLowerCase().replace(/\s+/g, "_");
}

function startBotFlow(chatId) {
  userStates.set(chatId, { state: "MAIN_MENU", data: {} });
  bot.sendMessage(chatId, "CivicOne\n\nWhat is your Emergency?");
  showMainMenu(chatId);
}

function showMainMenu(chatId) {
  bot.sendMessage(chatId, "Select a service:", {
    reply_markup: {
      inline_keyboard: [
        [{ text: "Emergency Response", callback_data: "emergency" }],
        [{ text: "Civic Infrastructure Issue", callback_data: "civic" }],
        [{ text: "Law & Order Report", callback_data: "crime" }],
      ],
    },
  });
}

function showEmergencyMenu(chatId) {
  bot.sendMessage(chatId, "Emergency Type:", {
    reply_markup: {
      inline_keyboard: [
        [{ text: "Fire Incident", callback_data: "Fire Incident" }],
        [{ text: "Medical Emergency", callback_data: "Medical Emergency" }],
        [{ text: "Road Accident", callback_data: "Road Accident" }],
        [{ text: "Back", callback_data: "back_main" }],
      ],
    },
  });
}

function showCivicMenu(chatId) {
  bot.sendMessage(chatId, "Civic Issue Category:", {
    reply_markup: {
      inline_keyboard: [
        [{ text: "Road / Pothole Damage", callback_data: "Road Damage" }],
        [{ text: "Garbage / Sanitation", callback_data: "Garbage Issue" }],
        [{ text: "Public Safety Issue", callback_data: "Public Safety Issue" }],
        [{ text: "Back", callback_data: "back_main" }],
      ],
    },
  });
}

function showCrimeMenu(chatId) {
  bot.sendMessage(chatId, "Report Type:", {
    reply_markup: {
      inline_keyboard: [
        [{ text: "Theft", callback_data: "Theft" }],
        [{ text: "Suspicious Activity", callback_data: "Suspicious Activity" }],
        [{ text: "Public Disturbance", callback_data: "Public Disturbance" }],
        [{ text: "Back", callback_data: "back_main" }],
      ],
    },
  });
}

async function confirmComplaint(chatId) {
  const state = userStates.get(chatId);
  if (!state) return;
  const data = state.data;
  const reportId = `CIV-${Date.now()}`;

  const loc = data.location || {};
  const lat = loc.latitude;
  const lng = loc.longitude;
  if (lat == null || lng == null) {
    bot.sendMessage(chatId, "Location is required. Please share your location.");
    return;
  }

  // Send immediate feedback so user doesn't think bot froze
  bot.sendMessage(chatId, "Processing your report...").catch(() => {});

  const payload = {
    report_id: reportId,
    type: incidentType(data.category || ""),
    category: data.category || "",
    latitude: Number(lat),
    longitude: Number(lng),
    photo_file_id: data.photo?.[0]?.file_id || null,
    video_file_id: data.video?.file_id || null,
    voice_file_id: data.voice?.file_id || null,
  };

  const result = await postIncident(payload);
  if (result) {
    bot.sendMessage(
      chatId,
      `Report Successfully Registered\n\nReport ID: ${reportId}\nEmergency services have been dispatched to your location.`
    );
  } else {
    bot.sendMessage(
      chatId,
      `Report received. Our team will process it shortly. Report ID: ${reportId}`
    );
  }

  bot.sendMessage(chatId, "Would you like any of the following?", {
    reply_markup: {
      inline_keyboard: [
        [{ text: "Request a Callback", callback_data: `callback_${reportId}` }],
        [{ text: "Add Additional Details", callback_data: `details_${reportId}` }],
        [{ text: "No, I'm Done", callback_data: "done" }],
      ],
    },
  });
  state.lastReportId = reportId;
  state.state = "POST_SUBMISSION";
}

// --- Handlers ---

bot.onText(/\/start/, (msg) => {
  startBotFlow(msg.chat.id);
});

bot.on("message", (msg) => {
  const chatId = msg.chat.id;
  const text = (msg.text || "").trim().toLowerCase();

  if (GREETINGS.has(text) && !userStates.has(chatId)) {
    startBotFlow(chatId);
    return;
  }

  if (!userStates.has(chatId)) return;

  const state = userStates.get(chatId).state;
  const data = userStates.get(chatId).data;

  if (state === "WAITING_FOR_LOCATION" && msg.location) {
    data.location = {
      latitude: msg.location.latitude,
      longitude: msg.location.longitude,
    };
    userStates.get(chatId).state = "WAITING_FOR_MEDIA";
    bot
      .sendMessage(
        chatId,
        "Upload supporting media (optional):\n• Photo\n• Video (max 30 sec)\n• Voice note\n\nOr type 'skip' to continue.",
        { reply_markup: { remove_keyboard: true } }
      )
      .catch((err) => {
        console.error("Send message failed:", err.message);
        bot.sendMessage(chatId, "Got your location. Type 'skip' to continue or send a photo.").catch(() => {});
      });
    return;
  }

  if (state === "WAITING_FOR_MEDIA" && text === "skip") {
    confirmComplaint(chatId).catch((err) => {
      console.error("confirmComplaint error:", err);
      bot.sendMessage(chatId, "Something went wrong. Please try /start again.");
    });
    return;
  }

  if (state === "WAITING_FOR_MEDIA" && msg.photo) {
    data.photo = msg.photo;
    confirmComplaint(chatId).catch((err) => {
      console.error("confirmComplaint error:", err);
      bot.sendMessage(chatId, "Something went wrong. Please try /start again.");
    });
    return;
  }

  if (state === "WAITING_FOR_MEDIA" && msg.video) {
    if (msg.video.duration > 30) {
      bot.sendMessage(chatId, "Video too long. Max 30 seconds allowed.");
      return;
    }
    data.video = msg.video;
    confirmComplaint(chatId).catch((err) => {
      console.error("confirmComplaint error:", err);
      bot.sendMessage(chatId, "Something went wrong. Please try /start again.");
    });
    return;
  }

  if (state === "WAITING_FOR_MEDIA" && msg.voice) {
    data.voice = msg.voice;
    confirmComplaint(chatId).catch((err) => {
      console.error("confirmComplaint error:", err);
      bot.sendMessage(chatId, "Something went wrong. Please try /start again.");
    });
    return;
  }

  if (state === "ADDING_DETAILS" && msg.text) {
    const reportId = userStates.get(chatId).lastReportId;
    postApi("/api/incidents/add-details", {
      report_id: reportId,
      additional_details: msg.text,
    });
    bot.sendMessage(chatId, "Additional details added successfully.");
    userStates.delete(chatId);
  }
});

bot.on("callback_query", async (query) => {
  await bot.answerCallbackQuery(query.id);
  const chatId = query.message.chat.id;
  const data = query.data;

  if (data === "emergency") return showEmergencyMenu(chatId);
  if (data === "civic") return showCivicMenu(chatId);
  if (data === "crime") return showCrimeMenu(chatId);
  if (data === "back_main") return showMainMenu(chatId);

  if (data.startsWith("callback_")) {
    const reportId = data.split("_")[1];
    await postApi("/api/callback-request", { report_id: reportId });
    bot.sendMessage(chatId, "Our team will contact you shortly.");
    userStates.delete(chatId);
    return;
  }

  if (data.startsWith("details_")) {
    bot.sendMessage(chatId, "Please type additional details:");
    userStates.get(chatId).state = "ADDING_DETAILS";
    return;
  }

  if (data === "done") {
    bot.sendMessage(chatId, "Thank you for using CivicOne.");
    userStates.delete(chatId);
    return;
  }

  // Category selected
  if (!userStates.has(chatId)) {
    userStates.set(chatId, { state: "MAIN_MENU", data: {} });
  }
  userStates.get(chatId).data.category = data;
  userStates.get(chatId).state = "WAITING_FOR_LOCATION";

  bot.sendMessage(chatId, `You selected: ${data}\n\nPlease share the exact location.`, {
    reply_markup: {
      keyboard: [[{ text: "Share Location", request_location: true }]],
      resize_keyboard: true,
      one_time_keyboard: true,
    },
  });
});

bot.on("polling_error", (err) => {
  console.error("Polling error:", err.message);
  if (err.message && err.message.includes("409")) {
    console.error("\n>>> Stop the other bot first: npm run stop-others\n");
  }
});

// Warn if backend might be down
axiosInstance.get("/health", { timeout: 3000 }).catch(() => {
  console.warn("WARNING: Backend not reachable at", API_BASE, "- reports may not be saved.");
});

console.log("CivicOne Telegram Bot (Node.js) running...");
