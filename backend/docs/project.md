# Civic-one | Unified Project Documentation & Technical Specification

> **Chennai Emergency & Civic Dispatch Command System**  
> Complete technical reference consolidating root, backend, frontend, telegram-bot documentation, geospatial algorithms, APIs, database schemas, and operational guides.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture & Data Flow](#2-system-architecture--data-flow)
3. [Project Directory Structure](#3-project-directory-structure)
4. [Technology Stack](#4-technology-stack)
5. [Core Features & Classification Matrices](#5-core-features--classification-matrices)
6. [Database Schema & Data Access Layer](#6-database-schema--data-access-layer)
7. [Geospatial Architecture & Algorithms](#7-geospatial-architecture--algorithms)
   - [7.1 H3 Hexagonal Grid Partitioning](#71-h3-hexagonal-grid-partitioning)
   - [7.2 Haversine Great-Circle Distance](#72-haversine-great-circle-distance)
   - [7.3 Dispatch Engine & Nearest Vehicle Selection](#73-dispatch-engine--nearest-vehicle-selection)
   - [7.4 OSRM Routing Service](#74-osrm-routing-service)
   - [7.5 Green Corridor & Traffic Signal Preemption](#75-green-corridor--traffic-signal-preemption)
   - [7.6 Auto-Mark Attended Proximity Logic](#76-auto-mark-attended-proximity-logic)
   - [7.7 Incident Intelligence Engine & Patrol Scoring](#77-incident-intelligence-engine--patrol-scoring)
   - [7.8 Simulated Radio Communications & TTS](#78-simulated-radio-communications--tts)
8. [Comprehensive REST API Reference](#8-comprehensive-rest-api-reference)
9. [Socket.IO Real-Time Event Architecture](#9-socketio-real-time-event-architecture)
10. [Setup, Execution & Operating Guides](#10-setup-execution--operating-guides)
    - [10.1 Environment Variables Configuration](#101-environment-variables-configuration)
    - [10.2 Backend Setup & Execution](#102-backend-setup--execution)
    - [10.3 Frontend Setup & Execution](#103-frontend-setup--execution)
    - [10.4 Telegram Bot Integration (Python & Node.js)](#104-telegram-bot-integration-python--nodejs)
    - [10.5 Autonomous Patrol Simulator](#105-autonomous-patrol-simulator)
11. [Production Deployment & Operational Checklist](#11-production-deployment--operational-checklist)

---

## 1. Executive Summary

**Civic-one (One City One Number)** is a full-stack unified municipal emergency and civic incident management command system tailored for Chennai.

The platform coordinates multi-agency dispatch operations across Police, Fire & Rescue, Medical/Ambulance, and Municipal services. Key capabilities include:
- Multi-channel citizen reporting (Web portal + Telegram Bot with photo/location support).
- Real-time command dashboard with Leaflet map overlays.
- Uber H3 hexagonal spatial indexing for density analysis and patrol prioritization.
- Automated nearest-vehicle dispatch algorithms with OSRM (Open Source Routing Machine) routing.
- Green corridor traffic signal preemption along emergency routes.
- Automated patrol simulation and real-time Socket.IO synchronization.
- Simulated tactical radio communications with text-to-speech (browser Web Speech API and Coqui TTS).

---

## 2. System Architecture & Data Flow

### Architectural Diagram

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   Telegram Bot   │       │ Next.js Dashboard│       │ Patrol Simulator │
│  (Node / Python) │       │ (React + Leaflet)│       │ (Python + OSRM)  │
└────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
         │                          │                          │
         │ POST /api/incidents/     │ REST + Socket.IO         │ POST /api/vehicles/
         │ telegram                 │                          │ position
         ▼                          ▼                          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Flask Backend Service (Port 8000)                    │
│ ┌───────────────────────────┐  ┌─────────────────────────────────────┐ │
│ │ Dispatch Engine (Nearest) │  │ Hex Service (Uber H3 Res-7)         │ │
│ └─────────────┬─────────────┘  └──────────────────┬──────────────────┘ │
│               │                                   │                    │
│ ┌─────────────┴─────────────┐  ┌──────────────────┴──────────────────┐ │
│ │ Route Service (OSRM)      │  │ Green Corridor (Signal Preemption)  │ │
│ └─────────────┬─────────────┘  └──────────────────┬──────────────────┘ │
│               │                                   │                    │
│ ┌─────────────┴─────────────┐  ┌──────────────────┴──────────────────┐ │
│ │ Intelligence Engine       │  │ Radio Comms & TTS (Coqui / Web API) │ │
│ └───────────────────────────┘  └─────────────────────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Raw SQL (psycopg2 pool)
                                    ▼
                         ┌────────────────────┐
                         │ PostgreSQL (civic1)│
                         │ - vehicles         │
                         │ - incidents        │
                         │ - hex_cells        │
                         │ - traffic_signals  │
                         └────────────────────┘
```

### End-to-End Lifecycle: Incident to Attended

1. **Incident Intake**: Citizen files a report via Web Form (`POST /api/incidents`) or Telegram Bot (`POST /api/incidents/telegram`) with coordinates (`lat`, `lng`), type, description, and optional photo.
2. **Hex Identification & Storage**: `services/hex_service.py` calculates H3 cell ID (`get_hex_id_from_latlng(lat, lng)`). Missing hex records are inserted via `ensure_hex_exists(hex_id)`. The incident is saved with status `new`.
3. **Dispatch & Routing**: `services/dispatch_engine.py` filters candidate vehicles (`status IN ('available', 'patrolling')` matching required type), computes Haversine distances, and selects the closest unit. Road driving trajectory is retrieved via `services/route_service.py` (OSRM) with straight-line fallback.
4. **Green Corridor & Radio Alert**: `services/green_corridor_engine.py` flags route hex cells as active green corridors for 600 seconds (10 mins). Traffic signals switch to GREEN. Radio comms are emitted (Control command + Dispatch acknowledgment).
5. **Real-Time Client Broadcast**: Flask-SocketIO broadcasts events (`new_incident`, `vehicle_dispatched`, `route_update`, `radio_comm`, `patrol_alert`) to dashboard operators.
6. **Arrival & Attended Resolution**: When the vehicle enters within 150m of the incident (via position updates) or operator calls `PATCH /api/incidents/:id/attended`: incident becomes `attended`, vehicle transitions to `patrolling`, and green corridors clear.

---

## 3. Project Directory Structure

```
civic-one/
├── backend/                             # Flask API & Socket.IO service
│   ├── app.py                           # App factory, blueprints & socket initialization
│   ├── config.py                        # Environment config & threshold defaults
│   ├── extensions.py                    # SocketIO instance definition
│   ├── requirements.txt                 # Python dependencies
│   ├── .env.example                     # Backend env template
│   ├── routes/                          # REST blueprints
│   │   ├── incidents.py                 # Incidents CRUD, Telegram ingestion & photo proxy
│   │   ├── vehicles.py                  # Deploy, update position, delete fleet units
│   │   ├── hex_grid.py                  # Hexagon polygons & incident density summary
│   │   ├── hex_lookup.py                # Coordinate-to-hex lookup
│   │   ├── dispatches.py                # Active dispatch route queries
│   │   ├── patrol_alerts.py             # Predictive patrol & pre-stationing alerts
│   │   ├── simulation.py                # Batch incident & vehicle simulation endpoints
│   │   ├── radio.py                     # Static radio comms audio & test emitters
│   │   ├── green_corridor.py            # Green corridor hex statuses
│   │   └── traffic_signals.py           # Traffic signal states across hex cells
│   ├── services/                        # Domain computation engines
│   │   ├── dispatch_engine.py           # Nearest vehicle selection, route & corridor trigger
│   │   ├── hex_service.py               # Uber H3 indexing, BBOX hex coverage & DB seed
│   │   ├── route_service.py             # OSRM driving route client with fallback
│   │   ├── intelligence_engine.py       # Density tracking, patrol alerts & ambulance placement
│   │   ├── simulation_engine.py         # Batch incident generator for demo/testing
│   │   ├── green_corridor_engine.py     # Signal preemption & corridor timeout management
│   │   ├── radio_comms.py               # Audio generation & dispatch radio event emission
│   │   ├── tts_service.py               # Coqui TTS synthesis service (optional)
│   │   └── telegram_bot.py              # Python-based Telegram bot implementation
│   ├── sockets/                         # WebSocket events
│   │   └── events.py                    # Socket.IO connection & listeners
│   ├── utils/                           # Core utilities
│   │   ├── db.py                        # psycopg2 pool & query helpers (raw SQL)
│   │   ├── geo.py                       # Haversine distance implementation
│   │   └── hex_labels.py                # Human-readable grid identifiers (A1, B-2)
│   ├── scripts/                         # Autonomous background runners
│   │   ├── run_telegram_bot.py          # Python Telegram bot launcher
│   │   ├── patrol_simulator.py          # Autonomous OSRM road patrol simulator
│   │   ├── traffic_signal_simulator.py  # Background traffic light state cycler
│   │   └── generate_control_audio.py    # Pre-generates radio audio files
│   └── docs/                            # Documentation specifications
│       ├── ALGORITHMS.md                # Mathematical formulas and routing logic
│       ├── API_REFERENCE.md             # REST endpoints and WebSocket events
│       ├── DISPATCH_ALGORITHM.md        # Vehicle assignment algorithm details
│       ├── HEX_GRID.md                  # H3 resolution and bounding box setup
│       ├── INTELLIGENCE_ENGINE.md       # Thresholds and intelligence rules
│       └── project.md                   # Consolidated master documentation
│
├── frontend/                            # Next.js Command Dashboard
│   ├── app/                             # Next.js App Router (layout, page, views)
│   ├── components/                      # MapView (Leaflet), IncidentForm, Panels
│   ├── lib/                             # api.ts (Axios), socket.ts (Socket.IO client)
│   ├── types/                           # TypeScript interfaces
│   ├── .env.example                     # Frontend env template
│   └── README.md                        # Frontend documentation
│
├── telegram-bot/                        # High-throughput Node.js Telegram Bot
│   ├── index.js                         # Node bot polling loop & backend poster
│   ├── package.json                     # Scripts (start, stop-others)
│   ├── .env.example                     # Bot environment template
│   └── README.md                        # Node bot documentation
│
├── .gitignore
└── README.md                            # Root project overview
```

---

## 4. Technology Stack

| Layer | Technologies | Rationale & Responsibility |
|---|---|---|
| **Frontend Framework** | Next.js 16 (React 19, TypeScript) | Server/client component architecture, type safety, fast live rendering |
| **Styling** | Tailwind CSS | Responsive layout and dark command dashboard themes |
| **Map & GIS** | Leaflet, React-Leaflet | Lightweight GIS rendering, polygonal hex overlays, vehicle markers, routes |
| **Real-Time Layer** | Socket.IO / Flask-SocketIO | Bi-directional event dissemination across all operators |
| **Backend Framework** | Flask 3, Werkzeug, Flask-CORS | Modular REST blueprints, lightweight execution footprint |
| **Database** | PostgreSQL | Relational consistency, high concurrency, ACID compliance |
| **DB Driver / Layer** | psycopg2-binary (Raw SQL) | Zero ORM overhead, full control over performance and locking |
| **Spatial Indexing** | Uber H3 (`h3-py`) | Hexagonal discrete global grid system (Resolution 7) |
| **Road Routing** | OSRM (Open Source Routing Machine) | Real-world driving route geometries and road-network distance |
| **Audio & TTS** | Coqui TTS / Web Speech API | Automated synthetic radio dispatches over radio channels |
| **Bot Interfaces** | Python (`python-telegram-bot`) & Node.js (`node-telegram-bot-api`) | Dual implementations for citizen reporting |

---

## 5. Core Features & Classification Matrices

### 5.1 Platform Capabilities Matrix

| Feature | Description |
|---|---|
| **Live Command Map** | Leaflet view showing Chennai H3 hex cells, live incidents, active fleet, route polylines, and corridor highlights. |
| **Multi-Channel Intake** | Web modal for 911/112 dispatchers and Telegram bot for citizen emergency reporting with location and photo. |
| **Smart Nearest Dispatch** | Haversine distance-ranked assignment filtering available/patrolling vehicles of the correct department. |
| **Dynamic Green Corridor** | Hex cells along calculated routes are flagged for emergency preemption; signals switch green for 10 minutes. |
| **Traffic Signal Controller** | Synchronized state simulation: green along active corridor hexes, standard cyclical red/yellow/green elsewhere. |
| **Simulated Tactical Radio** | Audio announcements emitted to operators on dispatch ("Control to Police-1, respond to..."). |
| **Autonomous Patrol Simulator**| Background agent driving vehicles along realistic OSRM roads between assigned hex centers. |
| **Intelligence Engine** | Automated density clustering triggering patrol frequency increases and ambulance pre-positioning suggestions. |
| **Hex Inspector & Lookup** | Interactive reverse lookup converting latitude/longitude to H3 hex IDs and historical incident breakdowns. |
| **Stress Simulation Suite** | Operator controls to deploy test fleets, inject random incident batches, and reset state. |

### 5.2 Incident Classification & Vehicle Dispatch Matrix

| Incident Category | Specific Incident Type | Assigned Department / Vehicle Type |
|---|---|---|
| **Law & Order** | `theft`, `suspicious`, `public_disturbance` | **Police** (`police`) |
| **Emergency / Medical** | `road_accident`, `medical` | **Ambulance** (`ambulance`) |
| **Fire & Disaster** | `fire` | **Fire Truck** (`fire`) |
| **Civic & Sanitation** | `garbage`, `sanitation`, `road_damage`, `pothole` | **Municipal Works** (`municipal`) |
| **Unspecified / Fallback**| `default` | Any available unit (`police`, `ambulance`, `fire`, `municipal`) |

---

## 6. Database Schema & Data Access Layer

### 6.1 Database Access Architecture

The backend intentionally **avoids Object-Relational Mappings (ORMs)** for maximal control and speed. Centralized DB access is defined in `backend/utils/db.py`:
- `get_connection()`: Thread-safe pooled connection via `psycopg2.pool.SimpleConnectionPool`.
- `execute_query(query, params=None)`: Executes `INSERT`, `UPDATE`, `DELETE` operations with transaction commit.
- `fetch_one(query, params=None)`: Returns a single matching row as a dictionary.
- `fetch_all(query, params=None)`: Returns all matching rows as dictionaries.

### 6.2 Relational Tables

#### Table: `vehicles`
Represents the municipal emergency fleet.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key | Unique vehicle identifier (generated via `uuid4`) |
| `type` | `VARCHAR(20)` | NOT NULL | Department type: `police`, `ambulance`, `fire`, `municipal` |
| `latitude` | `DOUBLE PRECISION` | NOT NULL | Current latitude coordinate |
| `longitude` | `DOUBLE PRECISION` | NOT NULL | Current longitude coordinate |
| `status` | `VARCHAR(30)` | NOT NULL | State machine: `available`, `patrolling`, `busy` |
| `current_hex_id` | `VARCHAR(20)` | Foreign Key | H3 Hex ID of current vehicle location |

#### Table: `incidents`
Represents citizen reports and emergency calls.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key | Unique incident identifier |
| `type` | `VARCHAR(80)` | NOT NULL | Category: `road_accident`, `fire`, `theft`, `pothole`, etc. |
| `latitude` | `DOUBLE PRECISION` | NOT NULL | Geographical latitude |
| `longitude` | `DOUBLE PRECISION` | NOT NULL | Geographical longitude |
| `hex_id` | `VARCHAR(20)` | Foreign Key | Associated H3 Hex cell |
| `assigned_vehicle_id` | `UUID` | Foreign Key → `vehicles(id)` | Currently dispatched vehicle (NULL if unassigned) |
| `status` | `VARCHAR(30)` | NOT NULL | Progression state: `new` → `assigned` → `attended` |
| `attended` | `BOOLEAN` | DEFAULT FALSE | Quick resolution flag |
| `report_id` | `VARCHAR(80)` | UNIQUE | User-facing identifier (e.g. `CIV-1042`) |
| `photo_url` | `TEXT` | Nullable | Uploaded photo or Telegram proxy URL |
| `video_url` | `TEXT` | Nullable | Optional video link |
| `voice_url` | `TEXT` | Nullable | Optional voice note link |
| `source` | `VARCHAR(20)` | NOT NULL | Origin: `web` or `telegram` |
| `created_at` | `TIMESTAMPTZ` | DEFAULT NOW() | Timestamp of report |

#### Table: `hex_cells`
Represents H3 geospatial cells partitioned across Chennai.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `hex_id` | `VARCHAR(20)` | Primary Key | Uber H3 64-bit Hex Index string |
| `center_lat` | `DOUBLE PRECISION` | NOT NULL | Centroid latitude of the hexagon |
| `center_lng` | `DOUBLE PRECISION` | NOT NULL | Centroid longitude of the hexagon |
| `incident_count` | `INT` | DEFAULT 0 | Count of incidents within this cell |
| `patrol_priority_score` | `FLOAT` | DEFAULT 0.0 | Dynamic score increased by intelligence triggers |

#### Table: `traffic_signals`
Represents virtual signals mapped per hex cell.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key | Traffic signal identifier |
| `hex_id` | `VARCHAR(20)` | Foreign Key | Associated H3 Hex cell |
| `current_phase` | `VARCHAR(10)` | NOT NULL | Signal state: `GREEN`, `YELLOW`, `RED` |
| `is_preempted` | `BOOLEAN` | DEFAULT FALSE | TRUE when overridden by active Green Corridor |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT NOW() | Timestamp of last phase transition |

---

## 7. Geospatial Architecture & Algorithms

### 7.1 H3 Hexagonal Grid Partitioning

**Implementation:** `backend/services/hex_service.py` & `backend/utils/hex_labels.py`

Uber's H3 discrete global grid system partitions Chennai into uniform hexagons with equal distances to all six neighbors.

- **Bounding Box (Chennai Metropolitan Area)**:
  - `CHENNAI_SOUTH`: `12.80`, `CHENNAI_NORTH`: `13.30`
  - `CHENNAI_WEST`: `79.95`, `CHENNAI_EAST`: `80.35`
- **H3 Resolution**: `7` (area ~5.16 km², edge length ~1.22 km).
- **Key Functions**:
  - `get_hex_id_from_latlng(lat, lng)`: Converts floating-point coordinates to an H3 index.
  - `generate_chennai_hex_ids()`: Generates all cells whose centroids fall within the Chennai bounding box.
  - `ensure_hex_exists(hex_id)`: Idempotently inserts hex metadata into `hex_cells` if missing.
  - `ensure_hex_cells_in_db()`: Bootstrap routine run at startup to populate Chennai cells into PostgreSQL.
- **Human-Readable Labels**: `utils/hex_labels.py` translates H3 IDs into human-readable callsigns (`A1`, `B-2`) for radio comms and UI display.

---

### 7.2 Haversine Great-Circle Distance

**Implementation:** `backend/utils/geo.py`

Computes great-circle distance between two geographic coordinates:

```
a = sin²(Δlat / 2) + cos(lat1) × cos(lat2) × sin²(Δlon / 2)
c = 2 × atan2(√a, √(1 - a))
d = R × c
```
Where $R = 6371.0 \text{ km}$ (Earth radius), and $\Delta\text{lat}, \Delta\text{lon}$ are in radians.

---

### 7.3 Dispatch Engine & Nearest Vehicle Selection

**Implementation:** `backend/services/dispatch_engine.py`

When an incident is reported, the dispatch engine executes:
1. **Type Matching**: Maps incident type to allowed vehicle types (Section 5.2).
2. **Filter**: Selects fleet units where `status IN ('available', 'patrolling')` and type matches.
3. **Nearest Assignment**:
   ```python
   return min(
       available_vehicles,
       key=lambda vehicle: haversine_km(
           incident["latitude"], incident["longitude"],
           vehicle["latitude"], vehicle["longitude"],
       ),
   )
   ```
4. **State Transition**:
   - Vehicle: `available` / `patrolling` → `busy`.
   - Incident: `new` → `assigned` with `assigned_vehicle_id`.
5. **Route & Corridor Trigger**: Initiates OSRM routing and Green Corridor activation.

---

### 7.4 OSRM Routing Service

**Implementation:** `backend/services/route_service.py`

- **Primary Provider**: Open Source Routing Machine (OSRM) driving profile.
- **Request Template**:
  ```http
  GET {OSRM_BASE_URL}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson
  ```
- **Timeout**: 4.0 seconds.
- **Fallback**: If OSRM fails or times out, constructs straight-line GeoJSON LineString between vehicle and incident coordinates.

---

### 7.5 Green Corridor & Traffic Signal Preemption

**Implementation:** `backend/services/green_corridor_engine.py`

- Identifies all H3 hex cells intersected by the dispatch route geometry.
- Hex cells are marked as active green corridor paths; signals in those hexes turn `GREEN`.
- **Duration**: 600 seconds (10 minutes).
- Automatically cleared when the incident is attended.

---

### 7.6 Auto-Mark Attended Proximity Logic

**Implementation:** `backend/routes/vehicles.py` (`update_vehicle_position`)

When a vehicle's position updates:
- Verifies if the vehicle has an assigned incident.
- Computes Haversine distance to the target incident.
- If distance $\le 150 \text{ m}$ (or $50 \text{ m}$ depending on threshold):
  - Incident automatically marked `attended = TRUE`, `status = 'attended'`.
  - Vehicle status transitions back to `patrolling`.
  - Associated green corridor preemption is released.
  - Broadcasts `incident_attended` Socket event.

---

### 7.7 Incident Intelligence Engine & Patrol Scoring

**Implementation:** `backend/services/intelligence_engine.py`

Processes incoming incidents to trigger predictive spatial actions:
- **Incident Density**: When hex `incident_count` $\ge$ `INCIDENT_DENSITY_THRESHOLD` (default: 5):
  - Emits `high_incident_density` patrol alert: *"Increase patrol frequency"*.
  - Increments `patrol_priority_score` by `+1.0`.
- **Accident Cluster**: When accident count in a hex $\ge$ `ACCIDENT_ALERT_THRESHOLD` (default: 3):
  - Emits `ambulance_prestation_suggestion`: *"Consider ambulance pre-stationing nearby"*.

---

### 7.8 Simulated Radio Communications & TTS

**Implementation:** `backend/services/radio_comms.py` & `backend/services/tts_service.py`

Simulates public safety voice dispatches:
1. **Control Command**: *"Control to {vehicle_id}, respond to {incident_type} in grid {hex_name}"*
2. **Dispatch Acknowledgment**: *"Dispatch {vehicle_id} to control, en route to grid {hex_name}"*

- **Browser TTS**: Synthesized by frontend via Web Speech API.
- **Coqui TTS**: When `ENABLE_RADIO_TTS=true`, generates `.wav` audio served at `GET /api/radio/static/:name`.

---

## 8. Comprehensive REST API Reference

All backend endpoints run at base URL `http://localhost:8000`.

### 8.1 Incident Endpoints

| Method | Path | Request Body / Query | Description |
|---|---|---|---|
| `POST` | `/api/incidents` | JSON: `type`, `latitude`, `longitude`, `description?` | Create emergency/civic incident (web) |
| `POST` | `/api/incidents/telegram` | JSON: `latitude`, `longitude`, `type`, `description?`, `photo_url?` | Create incident from Telegram bot |
| `GET` | `/api/incidents` | None | List all incidents |
| `PATCH` | `/api/incidents/<id>/attended` | URL param `<id>` | Mark attended, release vehicle to patrolling |
| `GET` | `/api/incidents/photo` | Query: `?file_id=<telegram_file_id>` | Proxy Telegram photo (requires token) |

### 8.2 Vehicle Fleet Endpoints

| Method | Path | Request Body / Query | Description |
|---|---|---|---|
| `GET` | `/api/vehicles` | None | List all fleet vehicles and statuses |
| `POST` | `/api/vehicles/deploy` | JSON: `type`, `hex_id?`, `latitude?`, `longitude?`, `count?`, `status?` | Deploy vehicles to grid |
| `DELETE`| `/api/vehicles/<id>` | URL param `<id>` | Decommission vehicle |
| `POST` | `/api/vehicles/position` | JSON: `vehicle_id`, `latitude`, `longitude`, `current_hex_id?` | Update position (patrol simulator) |

### 8.3 Hexagonal Grid & Geospatial Endpoints

| Method | Path | Request Body / Query | Description |
|---|---|---|---|
| `GET` | `/api/hex-grid` | None | Get GeoJSON polygon features for all Chennai hexes |
| `GET` | `/api/hex-grid/incidents-summary` | None | Incident counts and category breakdowns per hex |
| `GET` | `/api/hex-lookup/from-coordinates` | Query: `?lat=<float>&lng=<float>` | Lookup hex ID and label from coordinates |

### 8.4 Dispatch, Corridor & Signals Endpoints

| Method | Path | Request Body / Query | Description |
|---|---|---|---|
| `GET` | `/api/dispatches/active` | None | List active dispatches and route polylines |
| `GET` | `/api/green-corridor/active` | None | Active green corridor hex IDs |
| `GET` | `/api/traffic-signals` | None | Current traffic signal phases and preemption states |

### 8.5 Simulation & Intelligence Endpoints

| Method | Path | Request Body / Query | Description |
|---|---|---|---|
| `GET` | `/health` | None | Backend health check (`{ status: "ok" }`) |
| `GET` | `/api/patrol-alerts` | None | List intelligence patrol alerts |
| `POST` | `/api/simulation/config` | JSON: simulation settings | Update simulation parameters |
| `POST` | `/api/simulation/run` | None | Trigger simulated incident batch |
| `POST` | `/api/simulation/reset` | None | Reset simulation state and vehicle positions |
| `GET` | `/api/radio/static/<name>` | URL param `<name>` | Static audio file for radio dispatch |
| `GET` | `/api/radio/test` | None | Emit test `radio_comm` Socket event |

---

## 9. Socket.IO Real-Time Event Architecture

| Event Name | Direction | Payload Structure | Action Triggered |
|---|---|---|---|
| `new_incident` | Server → Client | Full incident object | Map drops new marker, updates incident count |
| `vehicle_dispatched` | Server → Client | `{ incident_id, vehicle, route, green_corridor_hexes }` | Draws route polyline, highlights corridor hexes |
| `route_update` | Server → Client | `{ route, green_corridor_hexes }` | Updates road polyline on map |
| `vehicle_position` | Server → Client | `{ vehicle }` | Updates vehicle marker coordinates on map |
| `vehicle_removed` | Server → Client | `{ vehicle_id }` | Removes vehicle marker from map |
| `incident_attended` | Server → Client | `{ incident_id }` | Removes emergency marker, clears route |
| `patrol_alert` | Server → Client | `{ alert_type, hex_id, message, ... }` | Displays alert banner and plays sound notification |
| `radio_comm` | Server → Client | `{ role, text, audio_filename? }` | Triggers voice speech synthesis |
| `simulation_update` | Server → Client | Simulation metrics object | Updates simulation dashboard panel |

---

## 10. Setup, Execution & Operating Guides

### 10.1 Environment Variables Configuration

#### Backend (`backend/.env`)

```ini
DATABASE_URL=postgresql://postgres:password@localhost:5432/civic1
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
PORT=8000
API_BASE_URL=http://localhost:8000

# Chennai Bounding Box & H3
CHENNAI_SOUTH=12.80
CHENNAI_NORTH=13.30
CHENNAI_WEST=79.95
CHENNAI_EAST=80.35
H3_RESOLUTION=7

# Intelligence Thresholds
INCIDENT_DENSITY_THRESHOLD=5
ACCIDENT_ALERT_THRESHOLD=3

# Routing & Audio
OSRM_BASE_URL=https://router.project-osrm.org
ENABLE_RADIO_TTS=false
```

#### Frontend (`frontend/.env.local`)

```ini
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SOCKET_URL=http://localhost:8000
NEXT_PUBLIC_USE_OFFLINE_TILES=false
```

#### Telegram Bot (`telegram-bot/.env`)

```ini
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
BACKEND_API_URL=http://localhost:8000
```

---

### 10.2 Backend Setup & Execution

```bash
cd backend
python -m venv venv
# Activate virtual environment:
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATABASE_URL and TELEGRAM_BOT_TOKEN
python app.py
```
Backend runs at `http://localhost:8000`.

---

### 10.3 Frontend Setup & Execution

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```
Dashboard runs at `http://localhost:3000`.

---

### 10.4 Telegram Bot Integration (Python & Node.js)

> **Important**: Run only **one** bot instance at a time to prevent HTTP `409 Conflict: terminated by other getUpdates request`.

#### Option A: Python Bot
```bash
cd backend
python scripts/run_telegram_bot.py
```

#### Option B: Node.js Bot
```bash
cd telegram-bot
npm install
npm start
```

#### Resolving 409 Conflict Errors:
1. Stop running bots:
   ```bash
   cd telegram-bot && npm run stop-others
   # Or manually: pkill -f run_telegram_bot && pkill -f telegram-bot
   ```
2. Remove stale lock: `rm /tmp/civicone-telegram-bot.lock`
3. Restart bot: `npm start`

---

### 10.5 Autonomous Patrol Simulator

Simulates patrolling vehicles moving along real OSRM road routes between Chennai hex cells:
```bash
cd backend
python scripts/patrol_simulator.py
```
- Configurable environment options: `PATROL_STEP_SECONDS` (default: 1.5), `PATROL_POINTS_PER_STEP` (default: 3), `OSRM_BASE_URL`.

---

## 11. Production Deployment & Operational Checklist

### 11.1 Deployment Recommendations

1. **Database**: PostgreSQL with connection pooling.
2. **Backend**: Flask with Gunicorn and `eventlet` worker:
   ```bash
   gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 app:app
   ```
3. **Frontend**: Production Next.js build:
   ```bash
   npm run build && npm start
   ```
4. **Services**: Manage background runners (Telegram Bot, Patrol Simulator) with PM2 or systemd:
   ```bash
   pm2 start scripts/patrol_simulator.py --name "patrol-sim" --interpreter python3
   pm2 start telegram-bot/index.js --name "telegram-bot"
   ```

### 11.2 Production Verification Checklist

- [ ] `DATABASE_URL` is set and accessible.
- [ ] `TELEGRAM_BOT_TOKEN` is set with webhook/polling enabled.
- [ ] `API_BASE_URL` is configured for photo proxying.
- [ ] CORS policies allow frontend domain.
- [ ] HTTPS enabled on all endpoints.
- [ ] Only one Telegram bot instance is running.
- [ ] OSRM server connectivity verified.
