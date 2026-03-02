# 2025-02-26
from flask import Blueprint, current_app

from utils.db import fetch_all

hex_grid_bp = Blueprint("hex_grid", __name__, url_prefix="/api/hex-grid")


@hex_grid_bp.get("")
def get_hex_grid():
    hex_service = current_app.extensions["hex_service"]
    inserted = hex_service.ensure_hex_cells_in_db()
    cells = hex_service.get_hex_grid_payload()
    return {
        "resolution": hex_service.resolution,
        "inserted": inserted,
        "cells": cells,
    }, 200


@hex_grid_bp.get("/incidents-summary")
def get_hex_incidents_summary():
    """Hex cells with incident count and type breakdown, sorted by incident_count DESC."""
    rows = fetch_all(
        """
        SELECT hc.hex_id, hc.center_lat, hc.center_lng, hc.incident_count, hc.patrol_priority_score
        FROM hex_cells hc
        ORDER BY hc.incident_count DESC, hc.hex_id ASC
        """
    )
    type_rows = fetch_all(
        """
        SELECT hex_id, type, COUNT(*)::int AS cnt
        FROM incidents
        WHERE hex_id IS NOT NULL
        GROUP BY hex_id, type
        """
    )
    types_by_hex = {}
    for r in type_rows:
        hid = r["hex_id"]
        if hid not in types_by_hex:
            types_by_hex[hid] = {}
        types_by_hex[hid][r["type"]] = r["cnt"]

    hex_service = current_app.extensions["hex_service"]
    cells = []
    for r in rows:
        boundary = hex_service._hex_boundary(r["hex_id"])
        cells.append({
            "hex_id": r["hex_id"],
            "polygon": boundary,
            "center": [r["center_lat"], r["center_lng"]],
            "incident_count": r["incident_count"],
            "patrol_priority_score": float(r["patrol_priority_score"]),
            "incident_types": types_by_hex.get(r["hex_id"], {}),
        })
    return {"cells": cells}, 200
