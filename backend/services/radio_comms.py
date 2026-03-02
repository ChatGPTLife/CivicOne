# 2025-02-26
"""Simulated radio communications between control and dispatch."""

from __future__ import annotations

import logging

from extensions import socketio

from utils.hex_labels import get_hex_label

logger = logging.getLogger(__name__)

_INCIDENT_TYPE_TO_SPEECH = {
    "fire": "fire incident",
    "medical": "medical emergency",
    "accident": "road accident",
    "crime": "crime report",
    "civic": "civic issue",
}


def _incident_type_for_speech(incident_type: str) -> str:
    key = (incident_type or "").strip().lower()
    return _INCIDENT_TYPE_TO_SPEECH.get(key, key.replace("_", " ") or "incident")


def _vehicle_id_short(vehicle_id) -> str:
    """Short vehicle ID for radio (e.g. last 6 chars)."""
    vid = str(vehicle_id)
    return vid[-6:] if len(vid) > 6 else vid


def trigger_radio_comms(
    vehicle_id,
    vehicle_prev_status: str,
    incident_type: str,
    hex_id: str,
):
    """
    Emit radio comms from main request thread (reliable delivery).
    Control speaks first, then dispatch (when status was patrolling -> busy).
    """
    try:
        hex_name = get_hex_label(hex_id)
    except Exception as e:
        logger.warning("hex_labels failed: %s, using hex_id", e)
        hex_name = (hex_id or "?")[:8]

    incident_speech = _incident_type_for_speech(incident_type)
    vid_short = _vehicle_id_short(vehicle_id)

    # 1. Control: "Control to {vehicle_id}, respond to {type} in {hex_name}"
    control_text = f"Control to {vid_short}, respond to {incident_speech} in grid {hex_name}"
    socketio.emit("radio_comm", {"role": "control", "text": control_text})

    # 2. Dispatch (only when status changed from patrolling to busy)
    if vehicle_prev_status and vehicle_prev_status.lower() == "patrolling":
        dispatch_text = f"Dispatch {vid_short} to control, en route to grid {hex_name}"
        socketio.emit("radio_comm", {"role": "dispatch", "text": dispatch_text})
