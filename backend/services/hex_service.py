# 2025-02-26
from __future__ import annotations

from typing import Dict, List, Set

import h3
from h3 import LatLngPoly

from utils.db import execute_query, fetch_all


class HexService:
    def __init__(self, chennai_bbox: Dict[str, float], resolution: int = 7) -> None:
        self.bbox = chennai_bbox
        self.resolution = resolution

    def get_hex_id_from_latlng(self, lat: float, lng: float) -> str:
        return h3.latlng_to_cell(lat, lng, self.resolution)

    def ensure_hex_exists(self, hex_id: str) -> None:
        """Insert hex into hex_cells if missing (for incident FK). Uses ON CONFLICT DO NOTHING."""
        center_lat, center_lng = h3.cell_to_latlng(hex_id)
        execute_query(
            """
            INSERT INTO hex_cells (hex_id, center_lat, center_lng, incident_count, patrol_priority_score)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (hex_id) DO NOTHING
            """,
            (hex_id, float(center_lat), float(center_lng), 0, 0.0),
        )

    def _chennai_bbox_polygon(self) -> LatLngPoly:
        """Chennai bbox as a closed (lat, lng) ring: SW -> SE -> NE -> NW -> SW."""
        s, n = self.bbox["south"], self.bbox["north"]
        w, e = self.bbox["west"], self.bbox["east"]
        outer = [(s, w), (s, e), (n, e), (n, w), (s, w)]
        return LatLngPoly(outer)

    def generate_chennai_hex_ids(self) -> Set[str]:
        """All H3 cells whose center lies inside the Chennai bbox (full coverage, no gaps)."""
        poly = self._chennai_bbox_polygon()
        cells = h3.polygon_to_cells(poly, self.resolution)
        return set(cells)

    def ensure_hex_cells_in_db(self) -> int:
        target_hexes = self.generate_chennai_hex_ids()
        existing_rows = fetch_all("SELECT hex_id FROM hex_cells")
        existing = {row["hex_id"] for row in existing_rows}

        # If DB has hexes at a different resolution, clear and repopulate at current resolution
        for hex_id in existing:
            if h3.get_resolution(hex_id) != self.resolution:
                execute_query("DELETE FROM hex_cells")
                existing = set()
                break

        missing = target_hexes - existing
        if not missing:
            return 0

        for hex_id in missing:
            center_lat, center_lng = h3.cell_to_latlng(hex_id)
            execute_query(
                """
                INSERT INTO hex_cells (hex_id, center_lat, center_lng, incident_count, patrol_priority_score)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (hex_id) DO NOTHING
                """,
                (hex_id, float(center_lat), float(center_lng), 0, 0.0),
            )
        return len(missing)

    def _hex_boundary(self, hex_id: str) -> List[List[float]]:
        boundary = h3.cell_to_boundary(hex_id)
        return [[float(lat), float(lng)] for lat, lng in boundary]

    def get_hex_grid_payload(self) -> List[dict]:
        cells = fetch_all(
            """
            SELECT hex_id, center_lat, center_lng, incident_count, patrol_priority_score
            FROM hex_cells
            ORDER BY hex_id ASC
            """
        )
        return [
            {
                "hex_id": cell["hex_id"],
                "polygon": self._hex_boundary(cell["hex_id"]),
                "center": [cell["center_lat"], cell["center_lng"]],
                "incident_count": cell["incident_count"],
                "patrol_priority_score": float(cell["patrol_priority_score"]),
            }
            for cell in cells
        ]
