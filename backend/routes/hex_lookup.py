# 2025-02-26
from flask import Blueprint, current_app, request

from utils.db import fetch_one


hex_lookup_bp = Blueprint("hex_lookup", __name__, url_prefix="/api/hex-lookup")


@hex_lookup_bp.get("/from-coordinates")
def hex_from_coordinates():
    """Return which hex box a lat/lng falls into (by hex_id)."""
    try:
        lat = float(request.args.get("lat", ""))
        lng = float(request.args.get("lng", ""))
    except ValueError:
        return {"error": "lat and lng query params are required and must be numbers"}, 400

    hex_service = current_app.extensions["hex_service"]
    hex_id = hex_service.get_hex_id_from_latlng(lat, lng)

    row = fetch_one(
        "SELECT hex_id, center_lat, center_lng, incident_count, patrol_priority_score "
        "FROM hex_cells WHERE hex_id = %s",
        (hex_id,),
    )
    if not row:
        # Hex not yet in DB: insert a blank record so management page stays consistent
        center_lat, center_lng = lat, lng
        from utils.db import execute_query

        execute_query(
            """
            INSERT INTO hex_cells (hex_id, center_lat, center_lng, incident_count, patrol_priority_score)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (hex_id) DO NOTHING
            """,
            (hex_id, center_lat, center_lng, 0, 0.0),
        )
        row = {"hex_id": hex_id, "center_lat": center_lat, "center_lng": center_lng, "incident_count": 0, "patrol_priority_score": 0.0}

    return {
        "hex_id": row["hex_id"],
        "center": [row["center_lat"], row["center_lng"]],
        "incident_count": row["incident_count"],
        "patrol_priority_score": float(row["patrol_priority_score"]),
    }, 200

