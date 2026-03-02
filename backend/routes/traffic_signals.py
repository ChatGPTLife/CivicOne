# 2025-02-26
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal, List

from flask import Blueprint, current_app


Phase = Literal["GREEN", "YELLOW", "RED"]


@dataclass
class TrafficSignal:
    id: str
    name: str
    latitude: float
    longitude: float
    green_s: int = 35
    yellow_s: int = 4
    red_s: int = 35
    offset_s: int = 0

    @property
    def cycle_s(self) -> int:
        return self.green_s + self.yellow_s + self.red_s

    def phase_at(self, t: float) -> Phase:
        position = (int(t) + self.offset_s) % self.cycle_s
        if position < self.green_s:
            return "GREEN"
        if position < self.green_s + self.yellow_s:
            return "YELLOW"
        return "RED"


def _real_chennai_signals() -> List[TrafficSignal]:
    """
    Real-life traffic signals at major Chennai intersections.
    Coordinates from known junctions and major road intersections.
    """
    # (name, lat, lng, offset_s for phase stagger)
    junctions = [
        ("Kathipara Junction", 13.0073, 80.2037, 0),
        ("Koyambedu Roundtana", 13.0761, 80.1992, 12),
        ("Guindy Kathipara", 13.0108, 80.2037, 24),
        ("Egmore Station", 13.0774, 80.2609, 5),
        ("Chennai Central", 13.0825, 80.2757, 18),
        ("Anna Nagar Roundtana", 13.0878, 80.2070, 30),
        ("T Nagar Pondy Bazaar", 13.0417, 80.2330, 8),
        ("Adyar Ananda Bhavan", 13.0040, 80.2558, 22),
        ("Velachery Main Rd", 12.9792, 80.2209, 14),
        ("Thiruvanmiyur MRTS", 12.9848, 80.2573, 6),
        ("Sholinganallur OMR", 12.9010, 80.2274, 28),
        ("Poonamallee High Rd", 13.0487, 80.1105, 10),
        ("Tambaram GST Rd", 12.9229, 80.1275, 20),
        ("Chromepet Phoenix", 12.9510, 80.1400, 2),
        ("Ambattur OT", 13.1143, 80.1548, 16),
        ("Madhavaram Milk Colony", 13.1379, 80.2490, 26),
        ("Perungudi OMR", 12.9705, 80.2414, 4),
        ("Saidapet Guindy", 13.0212, 80.2252, 32),
        ("Ashok Nagar", 13.0382, 80.2121, 11),
        ("Washermanpet", 13.1113, 80.2911, 24),
        ("Ennore Highway", 13.2144, 80.3216, 7),
        ("Anna Salai Nandanam", 13.0280, 80.2280, 19),
        ("OMR Thoraipakkam", 12.9350, 80.2280, 13),
        ("ECR Thiruvanmiyur", 12.9820, 80.2580, 1),
        ("GNT Road Red Hills", 13.1650, 80.2450, 15),
        ("Avadi Main Rd", 13.1150, 80.1010, 9),
        ("Purasawalkam", 13.0920, 80.2620, 23),
        ("Mylapore Tank", 13.0320, 80.2650, 17),
        ("Besant Nagar", 13.0060, 80.2680, 3),
        ("Vadapalani", 13.0520, 80.2120, 27),
        ("Porur", 13.0350, 80.1560, 21),
        ("Medavakkam", 12.9180, 80.1980, 5),
        ("Pallavaram", 12.9680, 80.1510, 29),
        ("Vandalur", 12.8920, 80.0810, 31),
    ]
    signals: List[TrafficSignal] = []
    for idx, (name, lat, lng, offset) in enumerate(junctions, start=1):
        signals.append(
            TrafficSignal(
                id=f"sig_{idx}",
                name=name,
                latitude=lat,
                longitude=lng,
                offset_s=offset,
            )
        )
    return signals


TRAFFIC_SIGNALS: List[TrafficSignal] = _real_chennai_signals()


traffic_signals_bp = Blueprint("traffic_signals", __name__, url_prefix="/api/traffic-signals")


@traffic_signals_bp.get("")
def list_signals():
    """
    Return all traffic signals with current phase.
    Signals in green corridor hexes are forced to GREEN.
    """
    now = time.time()
    green_corridor_hexes = set()
    hex_service = current_app.extensions.get("hex_service")
    try:
        from services.green_corridor_engine import get_active_hexes
        green_corridor_hexes = set(get_active_hexes())
    except Exception:
        pass

    result = []
    for sig in TRAFFIC_SIGNALS:
        phase = sig.phase_at(now)

        # Green corridor: if signal is in a corridor hex, force GREEN
        if hex_service and green_corridor_hexes:
            try:
                sig_hex = hex_service.get_hex_id_from_latlng(sig.latitude, sig.longitude)
                if sig_hex in green_corridor_hexes:
                    phase = "GREEN"
            except Exception:
                pass

        result.append(
            {
                "id": sig.id,
                "name": sig.name,
                "latitude": sig.latitude,
                "longitude": sig.longitude,
                "phase": phase,
            }
        )
    return {"signals": result}, 200
