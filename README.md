<!-- 2025-02-26 -->
# Civic-one | One City One Number

**Unified City Emergency & Civic Dispatch Command Dashboard for Chennai**

Civic-one is a full-stack emergency and civic incident management system that provides real-time dispatch coordination, hexagonal grid-based geospatial intelligence, and multi-channel incident reporting (web + Telegram). Designed for Chennai, it enables operators to visualize incidents, deploy vehicles, track dispatches, and receive AI-driven patrol alerts—all from a single command dashboard.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Socket Events](#socket-events)
- [Database Schema](#database-schema)
- [Algorithms & Logic](#algorithms--logic)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Features of Civic-One

### Core Capabilities

| Feature | Description |
|--------|-------------|
| **Live Map** | Interactive Leaflet map with Chennai hex grid, incidents, vehicles, and dispatch routes |
| **Incident Reporting** | Web form + Telegram bot for citizens to report emergencies (fire, medical, road accident, civic issues) |
| **Nearest-Vehicle Dispatch** | Automatic assignment of the closest available vehicle by type (police, ambulance, fire, municipal) |
| **Green Corridor** | Hex cells along dispatch route marked for traffic signal priority (10 min duration) |
| **Traffic Signals** | Simulated traffic lights per hex; green along green corridor, red elsewhere |
| **Radio Comms** | Simulated control/dispatch radio announcements (browser TTS or Coqui TTS) |
| **Patrol Simulator** | OSRM road-based movement of patrolling vehicles between hex cells |
| **Intelligence Engine** | Patrol alerts when incident density exceeds threshold; ambulance pre-stationing suggestions |
| **Hex Management** | Lookup hex by coordinates; view incident counts and type breakdown per hex |
| **Simulation** | Batch deploy vehicles, run incident simulations, reset state |

### Incident Types

- **Emergency:** Fire, Medical, Road Accident  
- **Civic:** Road Damage, Garbage, Public Safety  
- **Law & Order:** Theft, Suspicious Activity, Public Disturbance  

### Vehicle Types

- **Police** – theft, suspicious, public disturbance  
- **Ambulance** – road accident, medical  
- **Fire** – fire incidents  
- **Municipal** – garbage, road damage, pothole  

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS, Leaflet, Socket.IO Client |
| **Backend** | Flask 3, Flask-SocketIO, Flask-CORS, psycopg2 (raw SQL) |
| **Database** | PostgreSQL |
| **Geospatial** | H3 (Uber), OSRM (routing) |
| **Telegram** | Python (python-telegram-bot) or Node.js (node-telegram-bot-api) |
| **TTS (optional)** | Coqui TTS for radio audio; fallback: browser Web Speech API |

---

## Project Structure

```
sdg_hackathon/
├── backend/                 # Flask API + Socket.IO
│   ├── app.py               # App factory, extensions, bootstrap
│   ├── config.py             # Environment config (dotenv, DATABASE_URL, etc.)
│   ├── extensions.py        # Socket.IO extension
│   ├── requirements.txt
│   ├── .env.example
│   ├── routes/              # API blueprints
│   │   ├── __init__.py      # Blueprint registration
│   │   ├── incidents.py     # Incidents CRUD, Telegram proxy
│   │   ├── vehicles.py      # Deploy, position, delete
│   │   ├── hex_grid.py      # Hex grid, incidents-summary
│   │   ├── hex_lookup.py    # Coordinate → hex lookup
│   │   ├── dispatches.py    # Active dispatches
│   │   ├── patrol_alerts.py # Intelligence alerts
│   │   ├── simulation.py   # Simulation config/run/reset
│   │   ├── radio.py        # Radio static audio, test
│   │   ├── green_corridor.py
│   │   └── traffic_signals.py
│   ├── services/
│   │   ├── dispatch_engine.py      # Nearest-vehicle, routing, green corridor
│   │   ├── hex_service.py          # H3 hex generation, DB bootstrap
│   │   ├── route_service.py        # OSRM routing
│   │   ├── intelligence_engine.py  # Patrol alerts, ambulance suggestions
│   │   ├── simulation_engine.py    # Batch incident simulation
│   │   ├── green_corridor_engine.py
│   │   ├── radio_comms.py          # Radio event emission
│   │   ├── tts_service.py          # Coqui TTS (optional)
│   │   └── telegram_bot.py        # Python Telegram bot
│   ├── sockets/
│   │   └── events.py        # Socket event handlers
│   ├── utils/
│   │   ├── db.py           # DB connection, execute_query, fetch_one/all
│   │   ├── geo.py          # Haversine distance
│   │   └── hex_labels.py   # Human-readable hex labels (A1, B-2)
│   ├── scripts/
│   │   ├── run_telegram_bot.py
│   │   ├── patrol_simulator.py     # OSRM-based patrol movement
│   │   ├── traffic_signal_simulator.py
│   │   └── generate_control_audio.py
│   └── docs/
│       ├── API_REFERENCE.md
│       ├── ALGORITHMS.md
│       ├── HEX_GRID.md
│       └── INTELLIGENCE_ENGINE.md
│
├── frontend/                # Next.js app
│   ├── app/
│   │   ├── layout.tsx       # Root layout, RadioProvider
│   │   ├── page.tsx         # Live Map (main dashboard)
│   │   ├── incidents/       # Incidents list, mark attended
│   │   ├── dispatch/        # Dispatch view
│   │   ├── simulation/      # Deploy vehicles, patrol simulator
│   │   └── management/      # Hex management, coordinate lookup
│   ├── components/
│   │   ├── AppShell.tsx    # Header, sidebar nav
│   │   ├── MapView.tsx     # Leaflet map, hexes, incidents, vehicles
│   │   ├── IncidentForm.tsx
│   │   ├── SimulationPanel.tsx
│   │   ├── LiveFeedPanel.tsx
│   │   ├── StatusBar.tsx
│   │   ├── RadioProvider.tsx
│   │   └── DashboardHeader.tsx
│   ├── lib/
│   │   ├── api.ts          # REST API client
│   │   ├── socket.ts       # Socket.IO client
│   │   └── hexLabels.ts    # Hex label utilities
│   ├── types/
│   │   └── index.ts        # TypeScript types
│   └── .env.example
│
├── telegram-bot/            # Node.js Telegram bot (alternative to Python)
│   ├── index.js
│   ├── package.json
│   ├── .env.example
│   └── README.md
│
├── .gitignore
└── README.md
```

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Telegram Bot  │     │   Next.js App    │     │  Patrol Simulator│
│  (Python/Node)  │     │  (React + Leaflet)│     │   (Python)       │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                        │                          │
         │ POST /api/incidents/    │ REST + Socket.IO         │ POST /api/vehicles/
         │ telegram               │                          │ position
         ▼                        ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Flask Backend (port 8000)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │ Dispatch    │  │ Hex Service   │  │ Intelligence Engine         │ │
│  │ Engine      │  │ (H3)          │  │ (alerts, ambulance suggest) │ │
│  └─────────────┘  └──────────────┘  └────────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │ Route       │  │ Green         │  │ Simulation Engine          │ │
│  │ Service     │  │ Corridor      │  │                            │ │
│  │ (OSRM)      │  │ Engine        │  │                            │ │
│  └─────────────┘  └──────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│  vehicles       │
│  incidents      │
│  hex_cells      │
│  traffic_signals│
└─────────────────┘
```

### Data Flow (Incident → Dispatch)

1. **Incident created** (web form or Telegram) → `POST /api/incidents` or `POST /api/incidents/telegram`
2. **Hex assigned** → `hex_service.get_hex_id_from_latlng()` → incident stored with `hex_id`
3. **Dispatch engine** → Finds nearest available vehicle by type → OSRM route → Green corridor hexes
4. **Socket events** → `vehicle_dispatched`, `route_update`, `radio_comm` → Frontend updates map
5. **Mark attended** → `PATCH /api/incidents/:id/attended` → Vehicle status → patrolling, green corridor cleared

---

## Getting Started

### Prerequisites

- **Python 3.10+** (backend)
- **Node.js 18+** (frontend, telegram-bot)
- **PostgreSQL** (create database `civic1`)
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATABASE_URL, TELEGRAM_BOT_TOKEN
python app.py
```

Backend runs at `http://localhost:8000`.

### 2. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local: NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_SOCKET_URL (default localhost:8000)
npm run dev
```

Frontend runs at `http://localhost:3000`.

### 3. Telegram Bot (choose one)

**Python (recommended):**

```bash
cd backend
python scripts/run_telegram_bot.py
```

**Node.js:**

```bash
cd telegram-bot
npm install
cp .env.example .env
# Edit .env: TELEGRAM_BOT_TOKEN
npm start
```

> **Note:** Only one bot instance (Python or Node) can run at a time. Stop the other before starting.

### 4. Patrol Simulator (optional)

With backend running and vehicles deployed as "patrolling":

```bash
cd backend
python scripts/patrol_simulator.py
```

---

## Configuration

### Backend (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `TELEGRAM_BOT_TOKEN` | Yes* | - | Telegram bot token (*for incident reporting) |
| `PORT` | No | 8000 | Backend port |
| `CHENNAI_SOUTH` | No | 12.80 | Chennai bbox south |
| `CHENNAI_NORTH` | No | 13.30 | Chennai bbox north |
| `CHENNAI_WEST` | No | 79.95 | Chennai bbox west |
| `CHENNAI_EAST` | No | 80.35 | Chennai bbox east |
| `H3_RESOLUTION` | No | 7 | H3 hex resolution |
| `INCIDENT_DENSITY_THRESHOLD` | No | 5 | Patrol alert when hex incidents ≥ this |
| `ACCIDENT_ALERT_THRESHOLD` | No | 3 | Ambulance suggestion when accidents ≥ this |
| `OSRM_BASE_URL` | No | https://router.project-osrm.org | OSRM server |
| `API_BASE_URL` | No | - | Public URL for photo proxy |
| `ENABLE_RADIO_TTS` | No | false | Use Coqui TTS for radio |

### Frontend (`.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | http://localhost:8000 | Backend API URL |
| `NEXT_PUBLIC_SOCKET_URL` | http://localhost:8000 | Socket.IO URL |
| `NEXT_PUBLIC_USE_OFFLINE_TILES` | false | Use offline map tiles |

---

## API Reference

### Incidents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/incidents` | Create incident (web) |
| POST | `/api/incidents/telegram` | Create incident (Telegram bot) |
| GET | `/api/incidents` | List incidents |
| PATCH | `/api/incidents/:id/attended` | Mark attended, set vehicle to patrolling |
| GET | `/api/incidents/photo?file_id=` | Proxy Telegram photo (requires token) |

### Vehicles

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/vehicles` | List vehicles |
| POST | `/api/vehicles/deploy` | Deploy vehicles |
| DELETE | `/api/vehicles/:id` | Remove vehicle |
| POST | `/api/vehicles/position` | Update position (patrol simulator) |

### Hex Grid

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/hex-grid` | Hex cells with polygons |
| GET | `/api/hex-grid/incidents-summary` | Hexes with incident count & type breakdown |
| GET | `/api/hex-lookup/from-coordinates?lat=&lng=` | Lookup hex by coordinates |

### Other

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/patrol-alerts` | Intelligence alerts |
| GET | `/api/dispatches/active` | Active dispatches |
| GET | `/api/traffic-signals` | Traffic signal phases |
| GET | `/api/radio/static/:name` | Static radio audio |
| POST | `/api/simulation/config` | Set simulation config |
| POST | `/api/simulation/run` | Run simulation |
| POST | `/api/simulation/reset` | Reset simulation |

---

## Socket Events

| Event | Direction | Payload |
|-------|-----------|---------|
| `new_incident` | Server → Client | Incident object |
| `vehicle_dispatched` | Server → Client | `{ incident_id, vehicle, route, green_corridor_hexes }` |
| `route_update` | Server → Client | `{ route, green_corridor_hexes }` |
| `vehicle_position` | Server → Client | `{ vehicle }` |
| `vehicle_removed` | Server → Client | `{ vehicle_id }` |
| `incident_attended` | Server → Client | `{ incident_id }` |
| `patrol_alert` | Server → Client | PatrolAlert object |
| `radio_comm` | Server → Client | `{ role, text, audio_filename? }` |
| `simulation_update` | Server → Client | SimulationResult |

---

## Database Schema

### `vehicles`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| type | VARCHAR(20) | police, ambulance, fire, municipal |
| latitude | DOUBLE PRECISION | |
| longitude | DOUBLE PRECISION | |
| status | VARCHAR(30) | available, patrolling, busy |
| current_hex_id | VARCHAR(20) | H3 hex ID |

### `incidents`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| type | VARCHAR(80) | Incident type |
| latitude, longitude | DOUBLE PRECISION | |
| hex_id | VARCHAR(20) | H3 hex ID |
| assigned_vehicle_id | UUID | FK to vehicles |
| status | VARCHAR(30) | new, assigned, attended |
| attended | BOOLEAN | |
| report_id | VARCHAR(80) | e.g. CIV-123 |
| photo_url, video_url, voice_url | TEXT | Media URLs |
| source | VARCHAR(20) | web, telegram |
| created_at | TIMESTAMPTZ | |

### `hex_cells`

| Column | Type | Description |
|--------|------|-------------|
| hex_id | VARCHAR(20) | H3 cell ID (PK) |
| center_lat, center_lng | DOUBLE PRECISION | |
| incident_count | INT | |
| patrol_priority_score | FLOAT | |

---

## Algorithms & Logic

### Haversine Distance

Great-circle distance (km) between two lat/lng points. Used for nearest-vehicle selection.

### Dispatch Algorithm

1. **Vehicle type matching:** Map incident type → vehicle types (e.g. fire → fire truck)
2. **Filter:** `status IN ('available', 'patrolling')` and matching type
3. **Select:** Vehicle with minimum Haversine distance to incident
4. **Route:** OSRM road-based shortest path; fallback: straight line
5. **Green corridor:** Hex cells along route; traffic signals turn green for 10 min

### Intelligence Engine

- **High incident density:** Alert when `incident_count ≥ INCIDENT_DENSITY_THRESHOLD` (default 5)
- **Ambulance pre-stationing:** Suggestion when accident count ≥ 3 in a hex
- **Patrol priority score:** Incremented per hex when threshold exceeded

### H3 Hex Grid

- Chennai bbox partitioned into H3 resolution-7 cells
- Each hex ~7× larger than resolution-8
- Human-readable labels: A1, B-2, etc. (see `utils/hex_labels.py`)

---

## Deployment

1. **Database:** Create PostgreSQL database `civic1` (or configure `DATABASE_URL`)
2. **Backend:** Deploy Flask app (e.g. Gunicorn + eventlet for Socket.IO)
3. **Frontend:** `npm run build && npm start` or deploy to Vercel
4. **Environment:** Set all required env vars; never commit `.env`
5. **Telegram:** Run bot as separate process (systemd, PM2, etc.)

### Production Checklist

- [ ] Set strong `DATABASE_URL` with credentials
- [ ] Set `TELEGRAM_BOT_TOKEN`
- [ ] Configure `API_BASE_URL` for public photo proxy
- [ ] Use HTTPS for frontend and backend
- [ ] Configure CORS for production frontend origin

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes; ensure backend and frontend run locally
4. Submit a pull request

---

## License


