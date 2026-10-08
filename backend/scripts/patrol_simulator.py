#!/usr/bin/env python3
# 2025-02-26
"""
Patrol simulator for One City One Number – Chennai.

Moves vehicles with status='patrolling' along real roads using OSRM (open-source routing).
Each vehicle patrols between adjacent hex cells, following the shortest driving route.

Usage:
  From repo root: python backend/scripts/patrol_simulator.py
  Or from backend: python scripts/patrol_simulator.py

Requires: backend running (Flask on port 8000), DATABASE_URL set.
Uses: OSRM (https://router.project-osrm.org) for road-based routing.
"""
from __future__ import annotations

import math
import os
import random
import time
from typing import Any

import h3
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://localhost:5432/civic1",
)
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
OSRM_BASE = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
H3_RESOLUTION = int(os.getenv("H3_RESOLUTION", "7"))
# Tick rate + meters/second along the OSRM polyline (smooth, speed-independent of vertex density)
STEP_SECONDS = float(os.getenv("PATROL_STEP_SECONDS", "0.2"))
PATROL_SPEED_MPS = float(os.getenv("PATROL_SPEED_MPS", "48"))  # ~170 km/h in sim scale
DISPATCH_SPEED_MPS = float(os.getenv("DISPATCH_SPEED_MPS", "75"))  # ~270 km/h emergency sprint

http_session = requests.Session()

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import fetch_all, execute_query


def get_connection():
    return None


def fetch_patrolling_vehicles(conn=None) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, type, latitude, longitude, status, current_hex_id
        FROM vehicles
        WHERE status = %s
        """,
        ("patrolling",),
    )


def dispatch_unassigned_incidents() -> int:
    """Call API to assign nearest vehicle to unassigned incidents."""
    try:
        resp = http_session.post(f"{API_BASE}/api/incidents/dispatch-unassigned", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("dispatched", 0)
    except Exception:
        pass
    return 0


def fetch_busy_vehicles_with_incidents(conn=None) -> list[dict[str, Any]]:
    """Vehicles with status=busy that are assigned to a non-attended incident."""
    return fetch_all(
        """
        SELECT v.id, v.type, v.latitude, v.longitude, v.status, v.current_hex_id,
               i.id AS incident_id, i.latitude AS inc_lat, i.longitude AS inc_lng
        FROM vehicles v
        JOIN incidents i ON i.assigned_vehicle_id = v.id AND (i.attended = FALSE OR i.attended = 0)
        WHERE v.status = %s
        """,
        ("busy",),
    )


def fetch_hex_centers(conn=None) -> dict[str, tuple[float, float]]:
    rows = fetch_all("SELECT hex_id, center_lat, center_lng FROM hex_cells")
    return {r["hex_id"]: (float(r["center_lat"]), float(r["center_lng"])) for r in rows}


def random_point_in_hex(hex_id: str) -> tuple[float, float]:
    """
    Sample a random point inside the given hex by rejection sampling.
    We sample inside the hex's bounding box until latlng_to_cell returns the same id.
    """
    boundary = h3.cell_to_boundary(hex_id)
    lats = [lat for lat, _ in boundary]
    lngs = [lng for _, lng in boundary]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)

    for _ in range(50):  # up to 50 attempts
        lat = random.uniform(min_lat, max_lat)
        lng = random.uniform(min_lng, max_lng)
        if h3.latlng_to_cell(lat, lng, H3_RESOLUTION) == hex_id:
            return lat, lng
    # Fallback: use center of hex if rejection sampling failed
    lat, lng = h3.cell_to_latlng(hex_id)
    return float(lat), float(lng)


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def interpolate_point(
    a: tuple[float, float], b: tuple[float, float], t: float
) -> tuple[float, float]:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def advance_along_route(
    route: list[tuple[float, float]],
    index: int,
    t: float,
    distance_m: float,
) -> tuple[tuple[float, float], int, float, bool]:
    """Walk `distance_m` along `route` from segment `index` at fraction `t`. Returns (point, index, t, done)."""
    if len(route) < 2:
        pt = route[0] if route else (0.0, 0.0)
        return pt, 0, 0.0, True
    remaining = distance_m
    while remaining > 0 and index < len(route) - 1:
        a, b = route[index], route[index + 1]
        seg = haversine_m(a[0], a[1], b[0], b[1])
        if seg < 0.5:
            index += 1
            t = 0.0
            continue
        left = (1.0 - t) * seg
        if remaining < left:
            t = t + remaining / seg
            return interpolate_point(a, b, t), index, t, False
        remaining -= left
        index += 1
        t = 0.0
    return route[-1], len(route) - 1, 0.0, True


def get_osrm_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> list[tuple[float, float]]:
    """Fetch driving route from OSRM. Returns list of (lat, lng) points along the road."""
    url = (
        f"{OSRM_BASE}/route/v1/driving/"
        f"{start_lng},{start_lat};{end_lng},{end_lat}"
        "?overview=full&geometries=geojson"
    )
    try:
        resp = http_session.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        route = data.get("routes", [{}])[0]
        coords = route.get("geometry", {}).get("coordinates", [])
        return [(float(lat), float(lng)) for lng, lat in coords]
    except Exception:
        return [(start_lat, start_lng), (end_lat, end_lng)]


def pick_next_target(
    current_lat: float,
    current_lng: float,
    current_hex_id: str | None,
    hex_centers: dict[str, tuple[float, float]],
) -> tuple[str, float, float]:
    """
    Pick next patrol target INSIDE the current hex box.
    - If we know the current_hex_id, choose a random point within that same hex.
    - If not, pick a random hex from the grid and start patrolling inside it.
    """
    if current_hex_id:
        return current_hex_id, *random_point_in_hex(current_hex_id)

    hex_ids = list(hex_centers.keys())
    if not hex_ids:
        # Fallback: some reasonable default in Chennai
        default_hex = h3.latlng_to_cell(13.0827, 80.2707, H3_RESOLUTION)
        return default_hex, *random_point_in_hex(default_hex)

    next_hex = random.choice(hex_ids)
    lat, lng = random_point_in_hex(next_hex)
    return next_hex, lat, lng


def push_position(
    vehicle_id: str,
    latitude: float,
    longitude: float,
    current_hex_id: str,
) -> bool:
    resp = http_session.post(
        f"{API_BASE}/api/vehicles/position",
        json={
            "vehicle_id": vehicle_id,
            "latitude": latitude,
            "longitude": longitude,
            "current_hex_id": current_hex_id,
        },
        timeout=5,
    )
    return resp.status_code == 200


def main():
    print("Patrol simulator – Chennai (OSRM road-based movement). Ctrl+C to stop.")
    print(
        f"API: {API_BASE}  OSRM: {OSRM_BASE}  Step: {STEP_SECONDS}s  "
        f"patrol {PATROL_SPEED_MPS} m/s  dispatch {DISPATCH_SPEED_MPS} m/s"
    )
    conn = get_connection()
    hex_centers = fetch_hex_centers(conn)
    print(f"Loaded {len(hex_centers)} hex centers.")

    # Per-vehicle state: { "route": [(lat,lng),...], "index": int }
    vehicle_routes: dict[str, dict[str, Any]] = {}

    while True:
        try:
            # 0. Assign unassigned incidents to nearest patrolling/available vehicle
            dispatched = dispatch_unassigned_incidents()
            if dispatched:
                print(f"  Dispatched {dispatched} vehicle(s) to unassigned incident(s)")

            # 1. Move busy (dispatched) vehicles toward their incident
            busy = fetch_busy_vehicles_with_incidents(conn)
            for v in busy:
                vid = str(v["id"])
                lat, lng = float(v["latitude"]), float(v["longitude"])
                inc_lat, inc_lng = float(v["inc_lat"]), float(v["inc_lng"])
                state = vehicle_routes.get(vid)
                if state and state.get("incident_route") and not state.get("done"):
                    pt, idx, t, done = advance_along_route(
                        state["route"],
                        state["index"],
                        state.get("t", 0.0),
                        DISPATCH_SPEED_MPS * STEP_SECONDS,
                    )
                    pt_hex = h3.latlng_to_cell(pt[0], pt[1], H3_RESOLUTION)
                    push_position(vid, pt[0], pt[1], pt_hex)
                    state["index"], state["t"], state["done"] = idx, t, done
                    if done:
                        del vehicle_routes[vid]
                else:
                    geometry = get_osrm_route(lat, lng, inc_lat, inc_lng)
                    if len(geometry) < 2:
                        geometry = [(lat, lng), (inc_lat, inc_lng)]
                    vehicle_routes[vid] = {
                        "route": geometry,
                        "index": 0,
                        "t": 0.0,
                        "done": False,
                        "incident_route": True,
                    }
                    pt, idx, t, done = advance_along_route(
                        geometry, 0, 0.0, DISPATCH_SPEED_MPS * STEP_SECONDS
                    )
                    pt_hex = h3.latlng_to_cell(pt[0], pt[1], H3_RESOLUTION)
                    if push_position(vid, pt[0], pt[1], pt_hex):
                        print(f"  {v['type']} {vid[:8]}… -> incident (road route)")
                    vehicle_routes[vid]["index"] = idx
                    vehicle_routes[vid]["t"] = t
                    vehicle_routes[vid]["done"] = done
                    if done:
                        del vehicle_routes[vid]

            # 2. Move patrolling vehicles
            vehicles = fetch_patrolling_vehicles(conn)
            if not vehicles and not busy:
                print("No patrolling or dispatched vehicles. Deploy some from the /simulation page.")
            if vehicles:
                for v in vehicles:
                    vid = str(v["id"])
                    lat, lng = float(v["latitude"]), float(v["longitude"])
                    current_hex = v.get("current_hex_id")

                    state = vehicle_routes.get(vid)
                    if state and not state.get("incident_route") and not state.get("done"):
                        pt, idx, t, done = advance_along_route(
                            state["route"],
                            state["index"],
                            state.get("t", 0.0),
                            PATROL_SPEED_MPS * STEP_SECONDS,
                        )
                        pt_hex = h3.latlng_to_cell(pt[0], pt[1], H3_RESOLUTION)
                        push_position(vid, pt[0], pt[1], pt_hex)
                        state["index"], state["t"], state["done"] = idx, t, done
                        if done:
                            del vehicle_routes[vid]
                    else:
                        next_hex, tgt_lat, tgt_lng = pick_next_target(
                            lat, lng, current_hex, hex_centers
                        )
                        geometry = get_osrm_route(lat, lng, tgt_lat, tgt_lng)
                        if len(geometry) < 2:
                            geometry = [(lat, lng), (tgt_lat, tgt_lng)]
                        vehicle_routes[vid] = {
                            "route": geometry,
                            "index": 0,
                            "t": 0.0,
                            "done": False,
                        }
                        pt, idx, t, done = advance_along_route(
                            geometry, 0, 0.0, PATROL_SPEED_MPS * STEP_SECONDS
                        )
                        pt_hex = h3.latlng_to_cell(pt[0], pt[1], H3_RESOLUTION)
                        if push_position(vid, pt[0], pt[1], pt_hex):
                            print(f"  {v['type']} {vid[:8]}… -> {next_hex[:12]}… (road route)")
                        vehicle_routes[vid]["index"] = idx
                        vehicle_routes[vid]["t"] = t
                        vehicle_routes[vid]["done"] = done
                        if done:
                            del vehicle_routes[vid]

            time.sleep(STEP_SECONDS)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

    conn.close()


if __name__ == "__main__":
    main()
