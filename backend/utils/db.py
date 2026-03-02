# 2025-02-26
import os
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return database_url


def get_connection():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost:5432/civic1",
    )
    return psycopg2.connect(_normalize_database_url(database_url))


def execute_query(query: str, params: tuple[Any, ...] | list[Any] | None = None) -> int:
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        return cursor.rowcount
    except psycopg2.Error as error:
        if connection:
            connection.rollback()
        raise RuntimeError(f"Database query execution failed: {error.pgerror or str(error)}")
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
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        row = cursor.fetchone()
        connection.commit()
        return dict(row) if row else None
    except psycopg2.Error as error:
        if connection:
            connection.rollback()
        raise RuntimeError(f"Database fetch_one failed: {error.pgerror or str(error)}")
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
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        connection.commit()
        return [dict(row) for row in rows]
    except psycopg2.Error as error:
        if connection:
            connection.rollback()
        raise RuntimeError(f"Database fetch_all failed: {error.pgerror or str(error)}")
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
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        row = cursor.fetchone()
        connection.commit()
        return dict(row) if row else None
    except psycopg2.Error as error:
        if connection:
            connection.rollback()
        raise RuntimeError(f"Database execute_insert_returning failed: {error.pgerror or str(error)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def ensure_vehicles_table() -> None:
    """Create vehicles table if it does not exist (for deploy and patrol simulator)."""
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            type VARCHAR(20) NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'available',
            current_hex_id VARCHAR(20)
        )
        """
    )


def ensure_incidents_table() -> None:
    """Create incidents table if it does not exist and add missing columns."""
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            type VARCHAR(80) NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            hex_id VARCHAR(20),
            assigned_vehicle_id UUID REFERENCES vehicles(id),
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
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    _add_incidents_columns_if_missing()


def _add_incidents_columns_if_missing() -> None:
    """Add attended, report_id, photo_url, etc. if they don't exist."""
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
        execute_query(
            f"ALTER TABLE incidents ADD COLUMN IF NOT EXISTS {col} {typ}"
        )
