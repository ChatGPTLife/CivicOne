# 2025-02-26
import os
import re
import sqlite3
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# State flag for SQLite mode
_USE_SQLITE = False
_SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "civic1.db")


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return database_url


def _get_sqlite_connection():
    conn = sqlite3.connect(_SQLITE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
    conn.create_function("NOW", 0, lambda: datetime.now(timezone.utc).isoformat())
    return conn


def get_connection():
    global _USE_SQLITE
    if _USE_SQLITE:
        return _get_sqlite_connection()

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost:5432/civic1",
    )
    try:
        import psycopg2
        return psycopg2.connect(_normalize_database_url(database_url))
    except Exception as e:
        logger.warning("PostgreSQL connection failed (%s). Falling back to SQLite (%s)", e, _SQLITE_PATH)
        _USE_SQLITE = True
        return _get_sqlite_connection()


def _translate_query_for_sqlite(query: str, params: tuple[Any, ...] | list[Any] | None):
    # Strip Postgres typecasts
    query = query.replace("::int", "").replace("::text", "")

    if not params:
        return query.replace("%s", "?"), None

    params_list = list(params)
    match = re.search(r"(\w+)\s*=\s*ANY\s*\(\s*%s\s*\)", query, re.IGNORECASE)
    if match:
        field = match.group(1)
        # Find which param corresponds to the ANY(%s)
        prefix = query[:match.start()]
        idx = prefix.count("%s")
        val = params_list[idx]
        if isinstance(val, (list, tuple, set)):
            placeholders = ", ".join(["?"] * len(val))
            query = query[:match.start()] + f"{field} IN ({placeholders})" + query[match.end():]
            new_params = list(params_list[:idx]) + list(val) + list(params_list[idx+1:])
            return query.replace("%s", "?"), tuple(new_params)

    return query.replace("%s", "?"), tuple(params_list)


def execute_query(query: str, params: tuple[Any, ...] | list[Any] | None = None) -> int:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        if _USE_SQLITE:
            translated_query, translated_params = _translate_query_for_sqlite(query, params)
            cursor = connection.cursor()
            if translated_params:
                cursor.execute(translated_query, translated_params)
            else:
                cursor.execute(translated_query)
            connection.commit()
            return cursor.rowcount

        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        return cursor.rowcount
    except Exception as error:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise RuntimeError(f"Database query execution failed: {error}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def fetch_one(query: str, params: tuple[Any, ...] | list[Any] | None = None) -> dict | None:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        if _USE_SQLITE:
            translated_query, translated_params = _translate_query_for_sqlite(query, params)
            cursor = connection.cursor()
            if translated_params:
                cursor.execute(translated_query, translated_params)
            else:
                cursor.execute(translated_query)
            row = cursor.fetchone()
            connection.commit()
            return dict(row) if row else None

        from psycopg2.extras import RealDictCursor
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        row = cursor.fetchone()
        connection.commit()
        return dict(row) if row else None
    except Exception as error:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise RuntimeError(f"Database fetch_one failed: {error}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def fetch_all(query: str, params: tuple[Any, ...] | list[Any] | None = None) -> list[dict]:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        if _USE_SQLITE:
            translated_query, translated_params = _translate_query_for_sqlite(query, params)
            cursor = connection.cursor()
            if translated_params:
                cursor.execute(translated_query, translated_params)
            else:
                cursor.execute(translated_query)
            rows = cursor.fetchall()
            connection.commit()
            return [dict(row) for row in rows]

        from psycopg2.extras import RealDictCursor
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        connection.commit()
        return [dict(row) for row in rows]
    except Exception as error:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise RuntimeError(f"Database fetch_all failed: {error}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def execute_insert_returning(
    query: str, params: tuple[Any, ...] | list[Any] | None = None
) -> dict | None:
    """Execute INSERT ... RETURNING and return the first row as dict, or None."""
    connection = None
    cursor = None
    try:
        connection = get_connection()
        if _USE_SQLITE:
            translated_query, translated_params = _translate_query_for_sqlite(query, params)
            cursor = connection.cursor()
            if translated_params:
                cursor.execute(translated_query, translated_params)
            else:
                cursor.execute(translated_query)
            row = cursor.fetchone()
            connection.commit()
            return dict(row) if row else None

        from psycopg2.extras import RealDictCursor
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        row = cursor.fetchone()
        connection.commit()
        return dict(row) if row else None
    except Exception as error:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise RuntimeError(f"Database execute_insert_returning failed: {error}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def ensure_hex_cells_table() -> None:
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS hex_cells (
            hex_id VARCHAR(20) PRIMARY KEY,
            center_lat DOUBLE PRECISION NOT NULL,
            center_lng DOUBLE PRECISION NOT NULL,
            incident_count INT DEFAULT 0,
            patrol_priority_score FLOAT DEFAULT 0.0
        )
        """
    )


def ensure_traffic_signals_table() -> None:
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS traffic_signals (
            id VARCHAR(50) PRIMARY KEY,
            hex_id VARCHAR(20),
            current_phase VARCHAR(10) NOT NULL DEFAULT 'RED',
            is_preempted BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at TEXT
        )
        """
    )


def ensure_vehicles_table() -> None:
    """Create vehicles table if it does not exist (for deploy and patrol simulator)."""
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            id VARCHAR(50) PRIMARY KEY,
            type VARCHAR(20) NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'available',
            current_hex_id VARCHAR(20)
        )
        """
    )
    ensure_default_vehicles()


def ensure_incidents_table() -> None:
    """Create incidents table if it does not exist and add missing columns."""
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id VARCHAR(50) PRIMARY KEY DEFAULT (gen_random_uuid()),
            type VARCHAR(80) NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            hex_id VARCHAR(20),
            assigned_vehicle_id VARCHAR(50),
            status VARCHAR(30) NOT NULL DEFAULT 'new',
            attended BOOLEAN NOT NULL DEFAULT FALSE,
            report_id VARCHAR(80),
            photo_url TEXT,
            hospital_lat DOUBLE PRECISION,
            hospital_lng DOUBLE PRECISION,
            leg_phase VARCHAR(20) DEFAULT 'to_scene',
            photo_file_id TEXT,
            video_url TEXT,
            voice_url TEXT,
            source VARCHAR(20) DEFAULT 'web',
            created_at TEXT DEFAULT (NOW())
        )
        """
    )
    _add_incidents_columns_if_missing()


def _add_incidents_columns_if_missing() -> None:
    if _USE_SQLITE:
        return
    columns_to_add = [
        ("attended", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("report_id", "VARCHAR(80)"),
        ("photo_url", "TEXT"),
        ("hospital_lat", "DOUBLE PRECISION"),
        ("hospital_lng", "DOUBLE PRECISION"),
        ("leg_phase", "VARCHAR(20) DEFAULT 'to_scene'"),
        ("photo_file_id", "TEXT"),
        ("video_url", "TEXT"),
        ("voice_url", "TEXT"),
        ("source", "VARCHAR(20) DEFAULT 'web'"),
    ]
    for col, typ in columns_to_add:
        try:
            execute_query(
                f"ALTER TABLE incidents ADD COLUMN IF NOT EXISTS {col} {typ}"
            )
        except Exception:
            pass


def ensure_default_vehicles() -> None:
    """Seed Chennai emergency fleet if empty so operators immediately see active units."""
    try:
        count_row = fetch_one("SELECT COUNT(*) AS c FROM vehicles")
        if count_row and count_row.get("c", 0) > 0:
            return
    except Exception:
        pass

    default_fleet = [
        # Police Patrol
        ("police", 13.0475, 80.2824, "patrolling"),  # Marina Beach
        ("police", 13.0418, 80.2341, "patrolling"),  # T. Nagar
        ("police", 13.0850, 80.2101, "patrolling"),  # Anna Nagar
        ("police", 13.0067, 80.2030, "patrolling"),  # Guindy
        # Ambulances
        ("ambulance", 13.0826, 80.2750, "available"),  # Rajiv Gandhi Hospital
        ("ambulance", 13.1009, 80.2937, "available"),  # Stanley Medical College
        ("ambulance", 12.9684, 80.2414, "available"),  # OMR Hospital
        # Fire & Rescue
        ("fire", 13.0784, 80.2612, "available"),  # Egmore Fire Station
        ("fire", 13.0336, 80.2677, "available"),  # Mylapore Fire Station
        ("fire", 13.1143, 80.1548, "available"),  # Ambattur Fire Station
        # Municipal Works
        ("municipal", 13.0820, 80.2760, "patrolling"),  # Central Ripon Building
        ("municipal", 13.0012, 80.2565, "patrolling"),  # Adyar Depot
    ]

    for vtype, lat, lng, status in default_fleet:
        try:
            vid = str(uuid.uuid4())
            execute_query(
                "INSERT INTO vehicles (id, type, latitude, longitude, status) VALUES (%s, %s, %s, %s, %s)",
                (vid, vtype, lat, lng, status),
            )
        except Exception as e:
            logger.warning("Failed to seed vehicle %s: %s", vtype, e)
