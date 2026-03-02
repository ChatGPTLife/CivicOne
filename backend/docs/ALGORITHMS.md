<!-- 2025-02-26 -->
# Civic-one Backend Algorithms

## Haversine Distance (Great-Circle)

**File:** `utils/geo.py`

Computes the shortest distance between two points on Earth (great-circle distance in km).

### Formula

```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1−a))
d = R × c
```

Where:
- `R` = Earth radius = 6371 km
- `Δlat`, `Δlon` in radians

### Usage

- Vehicle-to-incident distance for nearest-vehicle dispatch
- Auto-mark attended: vehicle within 150 m of incident

---

## Dispatch Algorithm

**File:** `services/dispatch_engine.py`

### Vehicle Type Matching

| Incident Type | Vehicle Types |
|---------------|---------------|
| theft, suspicious, public_disturbance | police |
| road_accident, medical | ambulance |
| fire | fire |
| garbage, sanitation, road_damage, pothole | municipal |
| default | police, ambulance, fire, municipal |

### Nearest Vehicle Selection

1. Filter vehicles: `status IN ('available', 'patrolling')` and matching type
2. Compute Haversine distance from each vehicle to incident
3. Assign vehicle with **minimum distance**

### Status Transitions

- Vehicle: `available`/`patrolling` → `busy`
- Incident: `new` → `assigned`

---

## Routing (OSRM)

**File:** `services/route_service.py`

- **Primary:** OSRM (Open Source Routing Machine) – road-based shortest path
- **Fallback:** Straight-line geometry if OSRM fails or times out (4s)

### OSRM API

```
GET {OSRM_BASE_URL}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson
```

---

## Green Corridor

**File:** `services/green_corridor_engine.py`

- Hex cells along the dispatch route are marked as "green corridor"
- Traffic signals in those hexes turn GREEN
- Duration: 600 seconds (10 minutes)
- Cleared when incident is marked attended
