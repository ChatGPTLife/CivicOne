# 2025-02-26
from __future__ import annotations

from typing import List

from extensions import socketio
from utils.db import execute_query, fetch_one


class IncidentIntelligenceEngine:
    def __init__(self, incident_density_threshold: int = 5, accident_alert_threshold: int = 3):
        self.incident_density_threshold = incident_density_threshold
        self.accident_alert_threshold = accident_alert_threshold

    def _emit_alert(self, alert: dict) -> None:
        created_at = alert.get("created_at")
        created_at_iso = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
        socketio.emit(
            "patrol_alert",
            {
                "id": alert["id"],
                "hex_id": alert["hex_id"],
                "alert_type": alert["alert_type"],
                "message": alert["message"],
                "created_at": created_at_iso,
            },
        )

    def process_incident(self, incident: dict) -> List[dict]:
        alerts: List[dict] = []
        hex_cell = fetch_one("SELECT hex_id FROM hex_cells WHERE hex_id = %s", (incident["hex_id"],))

        if hex_cell:
            count_row = fetch_one(
                "SELECT COUNT(*)::int AS count FROM incidents WHERE hex_id = %s",
                (incident["hex_id"],),
            )
            current_count = count_row["count"] if count_row else 0

            execute_query(
                "UPDATE hex_cells SET incident_count = %s WHERE hex_id = %s",
                (current_count, incident["hex_id"]),
            )

            if current_count >= self.incident_density_threshold:
                execute_query(
                    """
                    UPDATE hex_cells
                    SET patrol_priority_score = patrol_priority_score + %s
                    WHERE hex_id = %s
                    """,
                    (1.0, incident["hex_id"]),
                )
                alert = fetch_one(
                    """
                    INSERT INTO patrol_alerts (hex_id, alert_type, message)
                    VALUES (%s, %s, %s)
                    RETURNING id, hex_id, alert_type, message, created_at
                    """,
                    (
                        incident["hex_id"],
                        "high_incident_density",
                        f"High incident density in hex {incident['hex_id']}. Increase patrol frequency.",
                    ),
                )
                if alert:
                    alerts.append(alert)

        if incident["type"] == "accident":
            accident_count_row = fetch_one(
                """
                SELECT COUNT(*)::int AS count
                FROM incidents
                WHERE hex_id = %s AND type = %s
                """,
                (incident["hex_id"], "accident"),
            )
            accident_count = accident_count_row["count"] if accident_count_row else 0

            if accident_count >= self.accident_alert_threshold:
                alert = fetch_one(
                    """
                    INSERT INTO patrol_alerts (hex_id, alert_type, message)
                    VALUES (%s, %s, %s)
                    RETURNING id, hex_id, alert_type, message, created_at
                    """,
                    (
                        incident["hex_id"],
                        "ambulance_prestation_suggestion",
                        f"Repeated accidents detected in hex {incident['hex_id']}. Consider ambulance pre-stationing nearby.",
                    ),
                )
                if alert:
                    alerts.append(alert)

        for alert in alerts:
            self._emit_alert(alert)

        return alerts
