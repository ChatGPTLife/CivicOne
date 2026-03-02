# 2025-02-26
from __future__ import annotations

import random
from typing import Dict

from extensions import socketio
from utils.db import execute_query, fetch_one


class SimulationEngine:
    def __init__(self, hex_service, dispatch_engine, intelligence_engine) -> None:
        self.hex_service = hex_service
        self.dispatch_engine = dispatch_engine
        self.intelligence_engine = intelligence_engine
        self.config: Dict = {
            "incident_type": "crime",
            "count": 5,
            "time_window": 15,
        }

    def update_config(self, payload: Dict) -> Dict:
        self.config.update(payload)
        return self.config

    def _random_point_for_hex(self, hex_id: str) -> tuple[float, float]:
        cell = fetch_one(
            "SELECT center_lat, center_lng FROM hex_cells WHERE hex_id = %s",
            (hex_id,),
        )
        if cell:
            return cell["center_lat"], cell["center_lng"]

        center_lat, center_lng = random.uniform(12.9, 13.2), random.uniform(80.0, 80.3)
        return center_lat, center_lng

    def run(self, payload: Dict | None = None) -> Dict:
        payload = payload or {}
        run_config = {**self.config, **payload}

        scenario = run_config.get("scenario", "surge")
        count = int(run_config.get("count", 1))
        incident_type = run_config.get("incident_type", "crime")
        target_hex = run_config.get("hex_id")

        if scenario == "vehicle_unavailability":
            execute_query("UPDATE vehicles SET status = %s", ("busy",))
            result = {"scenario": scenario, "updated_vehicles": "all_marked_busy"}
            socketio.emit("simulation_update", result)
            return result

        if scenario == "congestion":
            result = {
                "scenario": scenario,
                "message": "Congestion simulation active; corridor travel expected to slow down.",
            }
            socketio.emit("simulation_update", result)
            return result

        generated_incidents = []
        for _ in range(count):
            lat, lng = self._random_point_for_hex(target_hex) if target_hex else (
                random.uniform(12.9, 13.2),
                random.uniform(80.0, 80.3),
            )

            hex_id = self.hex_service.get_hex_id_from_latlng(lat, lng)
            incident = fetch_one(
                """
                INSERT INTO incidents (type, latitude, longitude, hex_id, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, type, latitude, longitude, hex_id, assigned_vehicle_id, status, created_at
                """,
                (incident_type, lat, lng, hex_id, "new"),
            )

            if not incident:
                continue

            self.intelligence_engine.process_incident(incident)
            dispatch_payload = self.dispatch_engine.dispatch(incident)

            generated_incidents.append(
                {
                    "id": incident["id"],
                    "type": incident["type"],
                    "latitude": incident["latitude"],
                    "longitude": incident["longitude"],
                    "hex_id": incident["hex_id"],
                    "dispatch": dispatch_payload,
                }
            )

        result = {
            "scenario": scenario,
            "count": count,
            "incidents": generated_incidents,
        }
        socketio.emit("simulation_update", result)
        return result

    def reset(self) -> Dict:
        execute_query("DELETE FROM incidents")
        execute_query("UPDATE vehicles SET status = %s", ("available",))
        execute_query(
            "UPDATE hex_cells SET incident_count = %s, patrol_priority_score = %s",
            (0, 0.0),
        )

        result = {"status": "simulation_reset"}
        socketio.emit("simulation_update", result)
        return result
