# 2025-02-26
from __future__ import annotations

from typing import Dict, List

from extensions import socketio
from utils.db import execute_query, fetch_all
from utils.geo import haversine_km


class DispatchEngine:
    def __init__(self, route_service, hex_service) -> None:
        self.route_service = route_service
        self.hex_service = hex_service

    def _nearest_vehicle(self, incident: dict) -> dict | None:
        incident_type = (incident.get("type") or "").lower()

        # Choose appropriate vehicle types based on incident type
        if incident_type in ("theft", "suspicious", "public_disturbance", "public_safety_issue"):
            wanted_types = ("police",)
        elif incident_type in ("road_accident", "medical"):
            wanted_types = ("ambulance",)
        elif incident_type == "fire":
            wanted_types = ("fire",)
        elif incident_type in ("garbage_issue", "garbage", "sanitation"):
            wanted_types = ("municipal",)
        elif incident_type in ("road_damage", "pothole_damage"):
            wanted_types = ("municipal",)
        else:
            wanted_types = ("police", "ambulance", "fire", "municipal")

        dispatchable_vehicles = fetch_all(
            """
            SELECT id, type, latitude, longitude, status, current_hex_id
            FROM vehicles
            WHERE status IN ('available', 'patrolling') AND type = ANY(%s)
            """,
            (list(wanted_types),),
        )
        if not dispatchable_vehicles:
            return None

        return min(
            dispatchable_vehicles,
            key=lambda vehicle: haversine_km(
                incident["latitude"],
                incident["longitude"],
                vehicle["latitude"],
                vehicle["longitude"],
            ),
        )

    def _extract_route_hexes(self, route_geometry: List[List[float]]) -> List[str]:
        route_hexes = {
            self.hex_service.get_hex_id_from_latlng(lat=point[0], lng=point[1])
            for point in route_geometry
        }
        return list(route_hexes)

    def dispatch(self, incident: dict) -> Dict:
        vehicle = self._nearest_vehicle(incident)
        if vehicle is None:
            payload = {
                "incident_id": incident["id"],
                "vehicle": None,
                "message": "No available vehicles",
            }
            socketio.emit("vehicle_dispatched", payload)
            return payload

        route = self.route_service.get_route(
            start_lat=vehicle["latitude"],
            start_lng=vehicle["longitude"],
            end_lat=incident["latitude"],
            end_lng=incident["longitude"],
        )
        green_corridor_hexes = self._extract_route_hexes(route["geometry"])

        # Activate green corridor – signals along route turn GREEN
        try:
            from services.green_corridor_engine import activate
            activate(green_corridor_hexes)
        except Exception:
            pass

        vehicle_prev_status = vehicle.get("status") or "available"

        execute_query(
            "UPDATE vehicles SET status = %s, current_hex_id = %s WHERE id = %s",
            ("busy", incident["hex_id"], vehicle["id"]),
        )
        execute_query(
            "UPDATE incidents SET assigned_vehicle_id = %s, status = %s WHERE id = %s",
            (vehicle["id"], "assigned", incident["id"]),
        )

        vehicle["status"] = "busy"

        # Simulated radio comms: control + dispatch (when patrolling -> busy)
        try:
            from services.radio_comms import trigger_radio_comms
            trigger_radio_comms(
                vehicle_id=vehicle["id"],
                vehicle_prev_status=vehicle_prev_status,
                incident_type=incident.get("type", ""),
                hex_id=incident.get("hex_id", ""),
            )
        except Exception:
            pass
        vehicle["current_hex_id"] = incident["hex_id"]

        vehicle_payload = {
            "id": vehicle["id"],
            "type": vehicle["type"],
            "latitude": vehicle["latitude"],
            "longitude": vehicle["longitude"],
            "status": vehicle["status"],
            "current_hex_id": vehicle["current_hex_id"],
        }

        dispatch_payload = {
            "incident_id": incident["id"],
            "vehicle": vehicle_payload,
            "route": route,
            "green_corridor_hexes": green_corridor_hexes,
        }

        socketio.emit("vehicle_dispatched", dispatch_payload)
        socketio.emit(
            "route_update",
            {
                "incident_id": incident["id"],
                "vehicle_id": vehicle["id"],
                "route": route,
                "green_corridor_hexes": green_corridor_hexes,
            },
        )

        return dispatch_payload
