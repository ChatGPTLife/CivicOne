# 2025-02-26
from flask import Blueprint, current_app, request

from extensions import socketio
from utils.db import execute_insert_returning, execute_query, fetch_all, fetch_one
from utils.geo import haversine_km

# Distance threshold (km) to auto-mark incident as attended when vehicle arrives.
# Slightly generous (150 m) so minor OSRM / GPS offsets still count as \"arrived\".
ARRIVAL_THRESHOLD_KM = 0.15

HOSPITALS = [
    {"id": "H1", "name": "Rajiv Gandhi Govt Hospital", "lat": 13.0826, "lng": 80.2750},
    {"id": "H2", "name": "Stanley Medical College", "lat": 13.1009, "lng": 80.2937},
    {"id": "H3", "name": "OMR Private Hospital", "lat": 12.9684, "lng": 80.2414},
]


def _nearest_hospital(lat: float, lng: float) -> dict | None:
    if not HOSPITALS:
        return None
    return min(HOSPITALS, key=lambda h: haversine_km(lat, lng, h["lat"], h["lng"]))

vehicles_bp = Blueprint("vehicles", __name__, url_prefix="/api/vehicles")


@vehicles_bp.get("")
def list_vehicles():
    rows = fetch_all(
        "SELECT id, type, latitude, longitude, status, current_hex_id FROM vehicles ORDER BY type, id"
    )
    vehicles = [
        {
            "id": str(r["id"]),
            "type": r["type"],
            "latitude": float(r["latitude"]),
            "longitude": float(r["longitude"]),
            "status": r["status"],
            "current_hex_id": r["current_hex_id"],
        }
        for r in rows
    ]
    return {"vehicles": vehicles}, 200


@vehicles_bp.post("/deploy")
def deploy_vehicles():
    payload = request.get_json(silent=True) or {}
    vehicle_type = payload.get("type", "police")
    if vehicle_type not in ("police", "ambulance", "fire", "municipal"):
        return {"error": "Invalid type. Use police, ambulance, fire, or municipal."}, 400

    count = max(1, min(int(payload.get("count", 1)), 50))
    status = payload.get("status", "patrolling")

    hex_service = current_app.extensions["hex_service"]
    hex_id = payload.get("hex_id")
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    if hex_id:
        cell = fetch_one(
            "SELECT center_lat, center_lng FROM hex_cells WHERE hex_id = %s",
            (hex_id,),
        )
        if not cell:
            return {"error": f"Hex id not found: {hex_id}"}, 404
        latitude = float(cell["center_lat"])
        longitude = float(cell["center_lng"])
    elif latitude is not None and longitude is not None:
        latitude = float(latitude)
        longitude = float(longitude)
        hex_id = hex_service.get_hex_id_from_latlng(latitude, longitude)
    else:
        # Default: deploy at Chennai center
        latitude, longitude = 13.0827, 80.2707
        hex_id = hex_service.get_hex_id_from_latlng(latitude, longitude)

    deployed = []
    for _ in range(count):
        row = execute_insert_returning(
            """
            INSERT INTO vehicles (type, latitude, longitude, status, current_hex_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, type, latitude, longitude, status, current_hex_id
            """,
            (vehicle_type, latitude, longitude, status, hex_id),
        )
        if row:
            vehicle = {
                "id": str(row["id"]),
                "type": row["type"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "status": row["status"],
                "current_hex_id": row["current_hex_id"],
            }
            deployed.append(vehicle)
            socketio.emit("vehicle_position", {"vehicle": vehicle})

    return {"deployed": len(deployed), "vehicles": deployed}, 201


@vehicles_bp.delete("/<vehicle_id>")
def delete_vehicle(vehicle_id: str):
    """Remove a vehicle from the map. Unassigns any incidents first."""
    row = fetch_one(
        "SELECT id FROM vehicles WHERE id = %s",
        (vehicle_id,),
    )
    if not row:
        return {"error": "Vehicle not found"}, 404

    # Unassign any incidents assigned to this vehicle
    execute_query(
        "UPDATE incidents SET assigned_vehicle_id = NULL, status = %s WHERE assigned_vehicle_id = %s",
        ("new", vehicle_id),
    )
    execute_query("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
    socketio.emit("vehicle_removed", {"vehicle_id": vehicle_id})

    return {"ok": True, "deleted": vehicle_id}, 200


@vehicles_bp.post("/position")
def update_vehicle_position():
    """Update a vehicle's position (for patrol simulator). Emits vehicle_position via socket."""
    payload = request.get_json(silent=True) or {}
    vehicle_id = payload.get("vehicle_id")
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    current_hex_id = payload.get("current_hex_id")
    if not vehicle_id or latitude is None or longitude is None:
        return {"error": "vehicle_id, latitude, longitude required"}, 400
    latitude = float(latitude)
    longitude = float(longitude)
    execute_query(
        "UPDATE vehicles SET latitude = %s, longitude = %s, current_hex_id = %s WHERE id = %s",
        (latitude, longitude, current_hex_id or None, vehicle_id),
    )
    row = fetch_one(
        "SELECT id, type, latitude, longitude, status, current_hex_id FROM vehicles WHERE id = %s",
        (vehicle_id,),
    )
    if not row:
        return {"error": "Vehicle not found"}, 404
    vehicle = {
        "id": str(row["id"]),
        "type": row["type"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "status": row["status"],
        "current_hex_id": row["current_hex_id"],
    }
    socketio.emit("vehicle_position", {"vehicle": vehicle})

    # Auto-mark / route logic when vehicle reaches incident or hospital
    incidents = fetch_all(
        """
        SELECT id, latitude, longitude, type, leg_phase, hospital_lat, hospital_lng
        FROM incidents
        WHERE assigned_vehicle_id = %s AND attended = FALSE
        """,
        (vehicle_id,),
    )
    for inc in incidents:
        inc_type = (inc["type"] or "").lower()
        leg_phase = (inc.get("leg_phase") or "to_scene").lower()

        # Incidents that require hospital handoff
        is_ambulance_case = inc_type in ("road_accident", "medical")

        # Distance to scene
        dist_to_scene = haversine_km(latitude, longitude, inc["latitude"], inc["longitude"])

        if is_ambulance_case and vehicle["type"] == "ambulance":
            # Leg 1: reach scene, then compute and start route to nearest hospital
            if leg_phase == "to_scene" and dist_to_scene <= ARRIVAL_THRESHOLD_KM:
                hospital = _nearest_hospital(inc["latitude"], inc["longitude"])
                if hospital:
                    execute_query(
                        "UPDATE incidents SET hospital_lat = %s, hospital_lng = %s, leg_phase = %s WHERE id = %s",
                        (hospital["lat"], hospital["lng"], "to_hospital", inc["id"]),
                    )
                    dispatch_engine = current_app.extensions["dispatch_engine"]
                    route = dispatch_engine.route_service.get_route(
                        start_lat=latitude,
                        start_lng=longitude,
                        end_lat=hospital["lat"],
                        end_lng=hospital["lng"],
                    )
                    green_corridor_hexes = dispatch_engine._extract_route_hexes(route["geometry"])
                    try:
                        from services.green_corridor_engine import activate
                        activate(green_corridor_hexes)
                    except Exception:
                        pass
                    socketio.emit(
                        "route_update",
                        {
                            "incident_id": inc["id"],
                            "vehicle_id": vehicle_id,
                            "route": route,
                            "green_corridor_hexes": green_corridor_hexes,
                        },
                    )
                    break

            # Leg 2: travelling to hospital – mark attended when we arrive there
            if leg_phase == "to_hospital" and inc.get("hospital_lat") is not None and inc.get("hospital_lng") is not None:
                dist_to_hospital = haversine_km(
                    latitude,
                    longitude,
                    float(inc["hospital_lat"]),
                    float(inc["hospital_lng"]),
                )
                if dist_to_hospital <= ARRIVAL_THRESHOLD_KM:
                    execute_query(
                        "UPDATE incidents SET attended = TRUE, status = %s WHERE id = %s",
                        ("resolved", inc["id"]),
                    )
                    execute_query(
                        "UPDATE vehicles SET status = %s WHERE id = %s",
                        ("patrolling", vehicle_id),
                    )
                    try:
                        from services.green_corridor_engine import clear
                        clear()
                    except Exception:
                        pass
                    socketio.emit("incident_attended", {"incident_id": str(inc["id"])})
                    break
        else:
            # Non-ambulance cases: mark attended at scene
            if dist_to_scene <= ARRIVAL_THRESHOLD_KM:
                execute_query(
                    "UPDATE incidents SET attended = TRUE, status = %s WHERE id = %s",
                        ("resolved", inc["id"]),
                )
                execute_query(
                    "UPDATE vehicles SET status = %s WHERE id = %s",
                    ("patrolling", vehicle_id),
                )
                try:
                    from services.green_corridor_engine import clear
                    clear()
                except Exception:
                    pass
                socketio.emit("incident_attended", {"incident_id": str(inc["id"])})
                break

    return {"vehicle": vehicle}, 200
