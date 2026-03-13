"""
DuckDB connection management for the backend API.

Provides a connection pool with read-only access for API queries,
ensuring data integrity and supporting concurrent reads.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import duckdb

logger = logging.getLogger("windsight.db")

# ── Default Path ───────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = Path(
    os.environ.get(
        "WINDSIGHT_DB_PATH",
        str(Path(__file__).resolve().parent.parent.parent / "data" / "windsight.duckdb"),
    )
)

# ── Global Connection ──────────────────────────────────────────────────────────

_connection: duckdb.DuckDBPyConnection | None = None


def get_db(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """
    Get or create a DuckDB connection for read-only API queries.

    DuckDB supports concurrent reads with a single connection.
    For production scale, this would be swapped with a ClickHouse
    connection pool via an adapter pattern.

    Args:
        db_path: Override path to the database file.

    Returns:
        Active DuckDB connection.
    """
    global _connection

    if _connection is not None:
        return _connection

    path = db_path or str(DEFAULT_DB_PATH)

    if not Path(path).exists():
        raise FileNotFoundError(
            f"Database not found at {path}. "
            "Run 'python -m pipeline.ingest' first to populate the database."
        )

    _connection = duckdb.connect(path, read_only=True)
    logger.info("Connected to DuckDB at %s (read-only)", path)
    return _connection


def close_db() -> None:
    """Close the DuckDB connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("DuckDB connection closed")
