<!-- 2025-02-26 -->
# One City One Number – Chennai (Backend)

Flask + PostgreSQL + psycopg2 (raw SQL) + Socket.IO backend for the emergency and civic dispatch dashboard.

## Run locally

1. Create and activate a virtual environment
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set required vars:
   - `DATABASE_URL` (required)
   - `TELEGRAM_BOT_TOKEN` (required for Telegram incident reporting)
   - Optional: `CHENNAI_SOUTH`, `CHENNAI_NORTH`, `CHENNAI_WEST`, `CHENNAI_EAST`, `H3_RESOLUTION`, `INCIDENT_DENSITY_THRESHOLD`, `ACCIDENT_ALERT_THRESHOLD`, `OSRM_BASE_URL`, `API_BASE_URL`
4. Start app:
   - `python app.py`
   - default URL: `http://localhost:8000`

## Telegram bot

Run the bot in a **separate terminal** (backend must be running first):

```bash
cd backend
python scripts/run_telegram_bot.py
```

The bot posts incidents to `POST /api/incidents/telegram`. Set `API_BASE_URL` if the backend is not on `http://localhost:8000`.

## APIs

- `GET /health`
- `GET /api/hex-grid`
- `GET /api/incidents` – list all incidents
- `POST /api/incidents`
- `POST /api/incidents/telegram` – create incident from Telegram bot
- `GET /api/incidents/photo?file_id=...` – proxy Telegram photo (requires `TELEGRAM_BOT_TOKEN`)
- `PATCH /api/incidents/<id>/attended` – mark incident as attended
- `GET /api/patrol-alerts`
- `GET /api/vehicles` – list all vehicles
- `POST /api/vehicles/deploy` – deploy vehicles (body: `type`, `hex_id?`, `latitude?`, `longitude?`, `count?`, `status?`)
- `POST /api/vehicles/position` – update vehicle position (for patrol simulator; body: `vehicle_id`, `latitude`, `longitude`, `current_hex_id?`)
- `POST /api/simulation/config`
- `POST /api/simulation/run`
- `POST /api/simulation/reset`

## Socket events emitted

- `new_incident`
- `vehicle_dispatched`
- `route_update`
- `patrol_alert`
- `simulation_update`
- `vehicle_position` – when a vehicle’s position is updated (e.g. by patrol simulator)
- `incident_attended` – when an incident is marked as attended
- `radio_comm` – simulated control/dispatch radio (role, text, audio_filename?)

## Radio comms (TTS)

When an incident is reported and a vehicle is dispatched, simulated radio comms are emitted:

1. **Control**: "Control to {vehicle_id}, respond to {incident_type} in grid {hex_name}"
2. **Dispatch** (only when vehicle was patrolling → busy): "Dispatch {vehicle_id} to control, en route to grid {hex_name}"

- **Without Coqui TTS**: Frontend uses browser Web Speech API.
- **With Coqui TTS**: Set `ENABLE_RADIO_TTS=true` and install: `pip install coqui-tts torch`. First run downloads the model (~100MB). Audio served at `GET /api/radio/audio/<filename>`.

## Patrol simulator (OSRM road-based)

From the project root (with backend running and vehicles deployed as “patrolling”):

```bash
cd backend && python scripts/patrol_simulator.py
```

Optional env: `API_BASE_URL`, `OSRM_BASE_URL` (default `https://router.project-osrm.org`), `PATROL_STEP_SECONDS` (1.5), `PATROL_POINTS_PER_STEP` (3), `H3_RESOLUTION` (7), `DATABASE_URL`.

## Dispatch engine

- `services/dispatch_engine.py` – assigns nearest vehicle, computes route, green corridor hexes
- `services/route_service.py` – OSRM-based shortest path routing

## Database Access

- ORM is not used.
- Centralized DB helper is in `utils/db.py`.
- Use:
   - `get_connection()`
   - `execute_query(query, params)`
   - `fetch_one(query, params)`
   - `fetch_all(query, params)`
