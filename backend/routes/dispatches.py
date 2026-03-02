# 2025-02-26
from __future__ import annotations

from flask import Blueprint, current_app

from utils.db import fetch_all


dispatches_bp = Blueprint("dispatches", __name__, url_prefix="/api/dispatches")


@dispatches_bp.get("/active")
def list_active_dispatches():
    """
    Return currently active dispatches with recomputed routes.

    Used by the frontend on initial load so that the glowing dispatch route
    persists across page refreshes.
    """
    rows = fetch_all(
        """
        SELECT
            i.id AS incident_id,
            i.type AS incident_type,
            i.latitude AS inc_lat,
            i.longitude AS inc_lng,
            i.hex_id AS inc_hex_id,
            i.assigned_vehicle_id,
            i.status AS incident_status,
            i.created_at AS incident_created_at,
            v.id AS vehicle_id,
            v.type AS vehicle_type,
            v.latitude AS veh_lat,
            v.longitude AS veh_lng,
            v.status AS vehicle_status,
            v.current_hex_id
        FROM incidents i
        JOIN vehicles v ON i.assigned_vehicle_id = v.id
        WHERE i.attended = FALSE
        """
    )

    if not rows:
        return {"dispatches": []}, 200

    dispatch_engine = current_app.extensions["dispatch_engine"]
    route_service = dispatch_engine.route_service
    hex_service = current_app.extensions["hex_service"]

    dispatches = []
    for r in rows:
        route = route_service.get_route(
            start_lat=float(r["veh_lat"]),
            start_lng=float(r["veh_lng"]),
            end_lat=float(r["inc_lat"]),
            end_lng=float(r["inc_lng"]),
        )
        green_corridor_hexes = list(
            {
                hex_service.get_hex_id_from_latlng(lat=pt[0], lng=pt[1])
                for pt in route.get("geometry", [])
            }
        )

        vehicle_payload = {
            "id": str(r["vehicle_id"]),
            "type": r["vehicle_type"],
            "latitude": float(r["veh_lat"]),
            "longitude": float(r["veh_lng"]),
            "status": r["vehicle_status"],
            "current_hex_id": r["current_hex_id"],
        }

        dispatch_payload = {
            "incident_id": str(r["incident_id"]),
            "vehicle": vehicle_payload,
            "route": route,
            "green_corridor_hexes": green_corridor_hexes,
        }

        dispatches.append(dispatch_payload)

    return {"dispatches": dispatches}, 200

