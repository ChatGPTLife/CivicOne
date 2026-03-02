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
# Smaller step + 1 point per step = smoother \"gliding\" movement
STEP_SECONDS = float(os.getenv("PATROL_STEP_SECONDS", "0.4"))
POINTS_PER_STEP = int(os.getenv("PATROL_POINTS_PER_STEP", "1"))  # Route points to advance per tick


def get_connection():
    url = DATABASE_URL
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return psycopg2.connect(url)


def fetch_patrolling_vehicles(conn) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, type, latitude, longitude, status, current_hex_id
            FROM vehicles
            WHERE status = %s
            """,
            ("patrolling",),
        )
        return [dict(r) for r in cur.fetchall()]


def dispatch_unassigned_incidents() -> int:
    """Call API to assign nearest vehicle to unassigned incidents."""
    try:
        resp = requests.post(f"{API_BASE}/api/incidents/dispatch-unassigned", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("dispatched", 0)
    except Exception:
        pass
    return 0


def fetch_busy_vehicles_with_incidents(conn) -> list[dict[str, Any]]:
    """Vehicles with status=busy that are assigned to a non-attended incident."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT v.id, v.type, v.latitude, v.longitude, v.status, v.current_hex_id,
                   i.id AS incident_id, i.latitude AS inc_lat, i.longitude AS inc_lng
            FROM vehicles v
            JOIN incidents i ON i.assigned_vehicle_id = v.id AND i.attended = FALSE
            WHERE v.status = %s
            """,
            ("busy",),
        )
        return [dict(r) for r in cur.fetchall()]


def fetch_hex_centers(conn) -> dict[str, tuple[float, float]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT hex_id, center_lat, center_lng FROM hex_cells")
        return {r["hex_id"]: (float(r["center_lat"]), float(r["center_lng"])) for r in cur.fetchall()}


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


def get_osrm_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> list[tuple[float, float]]:
    """Fetch driving route from OSRM. Returns list of (lat, lng) points along the road."""
    url = (
        f"{OSRM_BASE}/route/v1/driving/"
        f"{start_lng},{start_lat};{end_lng},{end_lat}"
        "?overview=full&geometries=geojson"
    )
    try:
        resp = requests.get(url, timeout=8)
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
    resp = requests.post(
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
    print(f"API: {API_BASE}  OSRM: {OSRM_BASE}  Step: {STEP_SECONDS}s")
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
                if state and state.get("incident_route") and state["index"] < len(state["route"]):
                    route = state["route"]
                    idx = state["index"]
                    advance = min(POINTS_PER_STEP, len(route) - idx)
                    new_idx = idx + advance
                    pt = route[new_idx - 1]
                    pt_hex = h3.latlng_to_cell(pt[0], pt[1], H3_RESOLUTION)
                    if push_position(vid, pt[0], pt[1], pt_hex):
                        pass
                    state["index"] = new_idx
                    if state["index"] >= len(route):
                        del vehicle_routes[vid]
                else:
                    geometry = get_osrm_route(lat, lng, inc_lat, inc_lng)
                    if len(geometry) < 2:
                        geometry = [(lat, lng), (inc_lat, inc_lng)]
                    vehicle_routes[vid] = {"route": geometry, "index": 1, "incident_route": True}
                    if len(geometry) > 1:
                        pt = geometry[1]
                        pt_hex = h3.latlng_to_cell(pt[0], pt[1], H3_RESOLUTION)
                        if push_position(vid, pt[0], pt[1], pt_hex):
                            print(f"  {v['type']} {vid[:8]}… -> incident (road route)")

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
                    if state and state["index"] < len(state["route"]):
                        # Continue along current route
                        route = state["route"]
                        idx = state["index"]
                        advance = min(POINTS_PER_STEP, len(route) - idx)
                        new_idx = idx + advance
                        pt = route[new_idx - 1]
                        pt_hex = h3.latlng_to_cell(pt[0], pt[1], H3_RESOLUTION)
                        if push_position(vid, pt[0], pt[1], pt_hex):
                            pass
                        state["index"] = new_idx
                        if state["index"] >= len(route):
                            del vehicle_routes[vid]
                    else:
                        # Need new route: current position -> next hex center
                        next_hex, tgt_lat, tgt_lng = pick_next_target(
                            lat, lng, current_hex, hex_centers
                        )
                        geometry = get_osrm_route(lat, lng, tgt_lat, tgt_lng)
                        if len(geometry) < 2:
                            geometry = [(lat, lng), (tgt_lat, tgt_lng)]
                        # Skip first point (we're already there), start from index 1
                        vehicle_routes[vid] = {"route": geometry, "index": 1}
                        if len(geometry) > 1:
                            pt = geometry[1]
                            pt_hex = h3.latlng_to_cell(pt[0], pt[1], H3_RESOLUTION)
                            if push_position(vid, pt[0], pt[1], pt_hex):
                                print(f"  {v['type']} {vid[:8]}… -> {next_hex[:12]}… (road route)")
                            vehicle_routes[vid]["index"] = 2

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
