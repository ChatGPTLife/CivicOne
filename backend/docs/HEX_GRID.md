<!-- 2025-02-26 -->
# H3 Hexagonal Grid

**File:** `services/hex_service.py`

## Overview

Civic-one uses Uber's H3 geospatial indexing system to partition Chennai into hexagonal cells.

## Configuration

| Config | Default | Description |
|--------|---------|--------------|
| CHENNAI_BBOX | south:12.80, north:13.30, west:79.95, east:80.35 | Chennai bounding box |
| H3_RESOLUTION | 7 | Hex resolution (7 ≈ 10 grids per res-8 cell) |

## Key Functions

- **`get_hex_id_from_latlng(lat, lng)`** – Convert lat/lng to H3 cell ID
- **`generate_chennai_hex_ids()`** – All cells whose center lies inside Chennai bbox
- **`ensure_hex_exists(hex_id)`** – Insert hex into DB if missing (for incident FK)
- **`ensure_hex_cells_in_db()`** – Bootstrap all Chennai hexes

## Hex Labels

**File:** `utils/hex_labels.py`

Human-readable labels (A1, B-2, etc.) for radio comms and UI.
