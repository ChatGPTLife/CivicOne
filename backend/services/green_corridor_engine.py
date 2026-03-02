# 2025-02-26
"""
Safe Corridor Engine – turns traffic signals along emergency routes to GREEN.

When an ambulance or emergency vehicle is dispatched, hex cells along the route
are marked as "green corridor". All traffic signals within those hexes are
forced to Special light phase until the vehicle passes or the corridor expires.
"""
from __future__ import annotations

import threading
import time
from typing import Set

# Active green corridor hex IDs. Thread-safe.
_active_hexes: Set[str] = set()
_expires_at: float = 0
_lock = threading.Lock()

# Corridor duration (seconds) – how long signals stay green after dispatch
CORRIDOR_DURATION_S = 600  # 10 minutes


def activate(hex_ids: list[str]) -> None:
    """Activate green corridor for the given hex cells along the route."""
    with _lock:
        global _active_hexes, _expires_at
        _active_hexes = set(hex_ids)
        _expires_at = time.time() + CORRIDOR_DURATION_S


def clear() -> None:
    """Clear the green corridor (e.g. when incident is attended)."""
    with _lock:
        global _active_hexes, _expires_at
        _active_hexes = set()
        _expires_at = 0


def is_hex_in_corridor(hex_id: str) -> bool:
    """Check if a hex cell is in the active green corridor."""
    with _lock:
        if time.time() > _expires_at:
            _active_hexes.clear()
            return False
        return hex_id in _active_hexes


def get_active_hexes() -> list[str]:
    """Return list of hex IDs in the active corridor (for frontend)."""
    with _lock:
        if time.time() > _expires_at:
            _active_hexes.clear()
            return []
        return list(_active_hexes)
