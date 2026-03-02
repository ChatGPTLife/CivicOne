# 2025-02-26
"""Green corridor API – status of active emergency route."""
from flask import Blueprint

green_corridor_bp = Blueprint("green_corridor", __name__, url_prefix="/api/green-corridor")


@green_corridor_bp.get("")
def status():
    """Return active green corridor hex IDs (signals along route are GREEN)."""
    try:
        from services.green_corridor_engine import get_active_hexes
        hex_ids = get_active_hexes()
        return {"active": len(hex_ids) > 0, "hex_ids": hex_ids}, 200
    except Exception:
        return {"active": False, "hex_ids": []}, 200
