# 2025-02-26
from flask import Blueprint

from utils.db import fetch_all


patrol_alerts_bp = Blueprint("patrol_alerts", __name__, url_prefix="/api/patrol-alerts")


@patrol_alerts_bp.get("")
def get_patrol_alerts():
    alerts = fetch_all(
        """
        SELECT id, hex_id, alert_type, message, created_at
        FROM patrol_alerts
        ORDER BY created_at DESC
        LIMIT 200
        """
    )
    return {
        "alerts": [
            {
                "id": alert["id"],
                "hex_id": alert["hex_id"],
                "alert_type": alert["alert_type"],
                "message": alert["message"],
                "created_at": (
                    alert["created_at"].isoformat()
                    if hasattr(alert["created_at"], "isoformat")
                    else str(alert["created_at"])
                ),
            }
            for alert in alerts
        ]
    }, 200
