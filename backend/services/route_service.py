# 2025-02-26
from __future__ import annotations

import time
from typing import Dict, List

import requests


class RouteService:
    def __init__(self, osrm_base_url: str) -> None:
        self.osrm_base_url = osrm_base_url.rstrip("/")

    def _fallback_route(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
    ) -> Dict:
        return {
            "distance_m": None,
            "duration_s": None,
            "geometry": [[start_lat, start_lng], [end_lat, end_lng]],
            "source": "fallback",
        }

    def get_route(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
    ) -> Dict:
        url = (
            f"{self.osrm_base_url}/route/v1/driving/"
            f"{start_lng},{start_lat};{end_lng},{end_lat}"
            "?overview=full&geometries=geojson"
        )
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=8)
                response.raise_for_status()
                data = response.json()
                routes = data.get("routes", [])
                if not routes:
                    raise ValueError("No routes returned")
                route = routes[0]
                coordinates: List[List[float]] = route.get("geometry", {}).get("coordinates", [])
                if len(coordinates) < 2:
                    raise ValueError("Route geometry too short")

                return {
                    "distance_m": route.get("distance"),
                    "duration_s": route.get("duration"),
                    "geometry": [[lat, lng] for lng, lat in coordinates],
                    "source": "osrm",
                }
            except Exception:
                if attempt < 2:
                    time.sleep(0.3 * (attempt + 1))
        return self._fallback_route(start_lat, start_lng, end_lat, end_lng)
