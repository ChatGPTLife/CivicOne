# 2025-02-26
import os

import requests
from flask import Blueprint, current_app, request, Response

from extensions import socketio
from utils.db import fetch_all, fetch_one


incidents_bp = Blueprint("incidents", __name__, url_prefix="/api/incidents")

# DB incidents_type_check allows only: crime, fire, medical, accident, civic
TELEGRAM_TYPE_TO_DB = {
    "fire": "fire",
    "medical": "medical",
    "road_accident": "accident",
    "accident": "accident",
    "road_damage": "civic",
    "garbage": "civic",
    "public_safety": "civic",
    "theft": "crime",
    "suspicious": "crime",
    "public_disturbance": "civic",
    "crime": "crime",
    "civic": "civic",
}


def _normalize_incident_type(raw: str) -> str:
    """Map incoming type to allowed DB type."""
    key = (raw or "").strip().lower()
    return TELEGRAM_TYPE_TO_DB.get(key, "civic")


@incidents_bp.post("")
def create_incident():
    payload = request.get_json(silent=True) or {}
    incident_type = payload.get("type")
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    if incident_type is None or latitude is None or longitude is None:
        return {
            "error": "Invalid payload. Required: type, latitude, longitude"
        }, 400

    hex_service = current_app.extensions["hex_service"]
    intelligence_engine = current_app.extensions["intelligence_engine"]
    dispatch_engine = current_app.extensions["dispatch_engine"]

    hex_id = hex_service.get_hex_id_from_latlng(float(latitude), float(longitude))
    hex_service.ensure_hex_exists(hex_id)
    db_type = _normalize_incident_type(str(incident_type))

    incident = fetch_one(
        """
        INSERT INTO incidents (type, latitude, longitude, hex_id, status)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, type, latitude, longitude, hex_id, assigned_vehicle_id, status, created_at
        """,
        (db_type, float(latitude), float(longitude), hex_id, "new"),
    )

    if not incident:
        return {"error": "Failed to create incident"}, 500

    alerts = intelligence_engine.process_incident(incident)
    dispatch_payload = dispatch_engine.dispatch(incident)

    latest_incident = fetch_one(
        """
        SELECT id, type, latitude, longitude, hex_id, assigned_vehicle_id, status, created_at
        FROM incidents
        WHERE id = %s
        """,
        (incident["id"],),
    )

    if not latest_incident:
        return {"error": "Failed to load incident state"}, 500

    created_at = latest_incident["created_at"]
    created_at_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)

    socketio.emit(
        "new_incident",
        {
            "id": latest_incident["id"],
            "type": latest_incident["type"],
            "latitude": latest_incident["latitude"],
            "longitude": latest_incident["longitude"],
            "hex_id": latest_incident["hex_id"],
            "assigned_vehicle_id": str(latest_incident["assigned_vehicle_id"]) if latest_incident.get("assigned_vehicle_id") else None,
            "status": latest_incident["status"],
            "created_at": created_at_iso,
        },
    )

    return {
        "incident": {
            "id": latest_incident["id"],
            "type": latest_incident["type"],
            "latitude": latest_incident["latitude"],
            "longitude": latest_incident["longitude"],
            "hex_id": latest_incident["hex_id"],
            "assigned_vehicle_id": latest_incident["assigned_vehicle_id"],
            "status": latest_incident["status"],
            "created_at": created_at_iso,
        },
        "dispatch": dispatch_payload,
        "alerts": [
            {
                "id": alert["id"],
                "hex_id": alert["hex_id"],
                "alert_type": alert["alert_type"],
                "message": alert["message"],
            }
            for alert in alerts
        ],
    }, 201


@incidents_bp.post("/telegram")
def create_incident_telegram():
    """Accept incident payload from Telegram bot."""
    payload = request.get_json(silent=True) or {}
    incident_type = payload.get("type") or payload.get("category", "")
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    if not incident_type or latitude is None or longitude is None:
        return {"error": "Invalid payload. Required: type/category, latitude, longitude"}, 400

    hex_service = current_app.extensions["hex_service"]
    intelligence_engine = current_app.extensions["intelligence_engine"]
    dispatch_engine = current_app.extensions["dispatch_engine"]

    hex_id = hex_service.get_hex_id_from_latlng(float(latitude), float(longitude))
    hex_service.ensure_hex_exists(hex_id)
    db_type = _normalize_incident_type(str(incident_type))

    incident = fetch_one(
        """
        INSERT INTO incidents (
            type, latitude, longitude, hex_id, status, report_id, photo_file_id, video_url, voice_url, source
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, type, latitude, longitude, hex_id, assigned_vehicle_id, status, report_id, photo_file_id, created_at
        """,
        (
            db_type,
            float(latitude),
            float(longitude),
            hex_id,
            "new",
            payload.get("report_id"),
            payload.get("photo_file_id"),
            payload.get("video_file_id"),
            payload.get("voice_file_id"),
            "telegram",
        ),
    )

    if not incident:
        return {"error": "Failed to create incident"}, 500

    alerts = intelligence_engine.process_incident(incident)
    dispatch_payload = dispatch_engine.dispatch(incident)

    latest = fetch_one(
        """
        SELECT id, type, latitude, longitude, hex_id, assigned_vehicle_id, status, report_id, photo_url, created_at
        FROM incidents WHERE id = %s
        """,
        (incident["id"],),
    )
    if not latest:
        return {"error": "Failed to load incident"}, 500

    created_at = latest["created_at"]
    created_at_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)

    socketio.emit(
        "new_incident",
        {
            "id": str(latest["id"]),
            "type": latest["type"],
            "latitude": latest["latitude"],
            "longitude": latest["longitude"],
            "hex_id": latest["hex_id"],
            "assigned_vehicle_id": str(latest["assigned_vehicle_id"]) if latest.get("assigned_vehicle_id") else None,
            "status": latest["status"],
            "report_id": latest.get("report_id"),
            "photo_url": latest.get("photo_url"),
            "created_at": created_at_iso,
        },
    )

    return {
        "incident": {
            "id": str(latest["id"]),
            "type": latest["type"],
            "latitude": latest["latitude"],
            "longitude": latest["longitude"],
            "hex_id": latest["hex_id"],
            "assigned_vehicle_id": str(latest["assigned_vehicle_id"]) if latest.get("assigned_vehicle_id") else None,
            "status": latest["status"],
            "report_id": latest.get("report_id"),
            "photo_url": latest.get("photo_url"),
            "created_at": created_at_iso,
        },
        "dispatch": dispatch_payload,
        "alerts": [{"id": a["id"], "hex_id": a["hex_id"], "alert_type": a["alert_type"], "message": a["message"]} for a in alerts],
    }, 201


@incidents_bp.get("")
def list_incidents():
    """List all incidents."""
    rows = fetch_all(
        """
        SELECT id, type, latitude, longitude, hex_id, assigned_vehicle_id, status, attended,
               report_id, photo_url, photo_file_id, video_url, voice_url, source, created_at
        FROM incidents
        ORDER BY created_at DESC
        """
    )
    base = os.getenv("API_BASE_URL", "").rstrip("/") or (request.host_url or "").rstrip("/") or f"http://localhost:{os.getenv('PORT', '8000')}"
    incidents = []
    for r in rows:
        created = r.get("created_at")
        photo_file_id = r.get("photo_file_id")
        photo_url = r.get("photo_url")
        if photo_file_id:
            photo_url = f"{base}/api/incidents/photo?file_id={photo_file_id}"
        incidents.append({
            "id": str(r["id"]),
            "type": r["type"],
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "hex_id": r["hex_id"],
            "assigned_vehicle_id": str(r["assigned_vehicle_id"]) if r.get("assigned_vehicle_id") else None,
            "status": r["status"],
            "attended": bool(r.get("attended", False)),
            "report_id": r.get("report_id"),
            "photo_url": photo_url,
            "video_url": r.get("video_url"),
            "voice_url": r.get("voice_url"),
            "source": r.get("source", "web"),
            "created_at": created.isoformat() if created and hasattr(created, "isoformat") else str(created or ""),
        })
    return {"incidents": incidents}


@incidents_bp.get("/photo")
def proxy_telegram_photo():
    """Proxy Telegram file by file_id. Requires TELEGRAM_BOT_TOKEN."""
    file_id = request.args.get("file_id")
    if not file_id:
        return {"error": "file_id required"}, 400
    from config import Config
    token = Config.TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return {"error": "Telegram bot not configured"}, 503
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            return {"error": "File not found"}, 404
        path = data.get("result", {}).get("file_path")
        if not path:
            return {"error": "No file path"}, 404
        file_r = requests.get(
            f"https://api.telegram.org/file/bot{token}/{path}",
            stream=True,
            timeout=10,
        )
        file_r.raise_for_status()
        return Response(
            file_r.iter_content(chunk_size=8192),
            mimetype="image/jpeg",
            headers={"Content-Disposition": "inline"},
        )
    except requests.RequestException as e:
        return {"error": str(e)}, 502


@incidents_bp.post("/dispatch-unassigned")
def dispatch_unassigned():
    """Assign nearest vehicle to any unassigned incidents. Called by patrol simulator."""
    rows = fetch_all(
        "SELECT id, type, latitude, longitude, hex_id FROM incidents WHERE attended = FALSE AND assigned_vehicle_id IS NULL"
    )
    if not rows:
        return {"dispatched": 0}, 200
    dispatch_engine = current_app.extensions["dispatch_engine"]
    count = 0
    for r in rows:
        incident = dict(r)
        incident["id"] = str(incident["id"])
        result = dispatch_engine.dispatch(incident)
        if result.get("vehicle"):
            count += 1
    return {"dispatched": count}, 200


@incidents_bp.patch("/<incident_id>/attended")
def mark_attended(incident_id: str):
    """Mark incident as attended and set assigned vehicle status to patrolling."""
    try:
        from utils.db import execute_query, fetch_one
        row = fetch_one(
            "SELECT assigned_vehicle_id FROM incidents WHERE id = %s",
            (incident_id,),
        )
        if not row:
            return {"error": "Incident not found"}, 404
        n = execute_query(
            "UPDATE incidents SET attended = TRUE, status = %s WHERE id = %s",
            ("resolved", incident_id),
        )
        if n == 0:
            return {"error": "Incident not found"}, 404
        vehicle_id = row.get("assigned_vehicle_id")
        if vehicle_id:
            execute_query(
                "UPDATE vehicles SET status = %s WHERE id = %s",
                ("patrolling", vehicle_id),
            )
            vehicle = fetch_one(
                "SELECT id, type, latitude, longitude, status, current_hex_id FROM vehicles WHERE id = %s",
                (vehicle_id,),
            )
            if vehicle:
                vehicle_payload = {
                    "id": str(vehicle["id"]),
                    "type": vehicle["type"],
                    "latitude": float(vehicle["latitude"]),
                    "longitude": float(vehicle["longitude"]),
                    "status": "patrolling",
                    "current_hex_id": vehicle["current_hex_id"],
                }
                socketio.emit("vehicle_position", {"vehicle": vehicle_payload})
        try:
            from services.green_corridor_engine import clear
            clear()
        except Exception:
            pass
        socketio.emit("incident_attended", {"incident_id": incident_id})
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}, 500
