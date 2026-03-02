# 2025-02-26
"""Hex ID to human-readable label mapping (matches frontend buildHexLabelMap)."""

from utils.db import fetch_all

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_label_cache: dict[str, str] | None = None


def _index_to_hex_label(index: int) -> str:
    letter = _ALPHABET[index % 26]
    group = index // 26
    return letter if group == 0 else f"{letter}-{group}"


def get_hex_label(hex_id: str) -> str:
    """Return human-readable label for hex_id (e.g. 'A1', 'B-2')."""
    global _label_cache
    if _label_cache is None:
        rows = fetch_all("SELECT hex_id FROM hex_cells ORDER BY hex_id ASC")
        _label_cache = {
            row["hex_id"]: _index_to_hex_label(idx)
            for idx, row in enumerate(rows)
        }
    return _label_cache.get(hex_id, hex_id[:8] if hex_id else "?")
