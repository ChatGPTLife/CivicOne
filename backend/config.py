# 2025-02-26
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost:5432/civic1",
    )

    CHENNAI_BBOX = {
        "south": float(os.getenv("CHENNAI_SOUTH", "12.80")),
        "north": float(os.getenv("CHENNAI_NORTH", "13.30")),
        "west": float(os.getenv("CHENNAI_WEST", "79.95")),
        "east": float(os.getenv("CHENNAI_EAST", "80.35")),
    }
    # Resolution 7: each hex ~7× larger than res 8 (~10 current grids → 1 grid box)
    H3_RESOLUTION = int(os.getenv("H3_RESOLUTION", "7"))

    INCIDENT_DENSITY_THRESHOLD = int(os.getenv("INCIDENT_DENSITY_THRESHOLD", "5"))
    ACCIDENT_ALERT_THRESHOLD = int(os.getenv("ACCIDENT_ALERT_THRESHOLD", "3"))

    OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
