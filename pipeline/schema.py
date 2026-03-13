"""
Database schema definitions for WindSight.

Defines DuckDB table schemas with appropriate indexing for time-series queries.
Designed to be portable to ClickHouse with minimal changes.
"""

import duckdb

from pipeline.config import DB_PATH, DATA_DIR


# ── SQL DDL ────────────────────────────────────────────────────────────────────

ACTUAL_GENERATION_DDL = """
CREATE TABLE IF NOT EXISTS actual_generation (
    start_time      TIMESTAMPTZ NOT NULL,
    settlement_date DATE        NOT NULL,
    settlement_period INTEGER   NOT NULL,
    generation_mw   DOUBLE      NOT NULL,
    fuel_type       VARCHAR     NOT NULL DEFAULT 'WIND',
    PRIMARY KEY (start_time)
);
"""

WIND_FORECAST_DDL = """
CREATE TABLE IF NOT EXISTS wind_forecast (
    start_time      TIMESTAMPTZ NOT NULL,
    publish_time    TIMESTAMPTZ NOT NULL,
    generation_mw   DOUBLE      NOT NULL,
    PRIMARY KEY (start_time, publish_time)
);
"""

# Index for the core horizon query: find latest forecast before (target - horizon)
FORECAST_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_forecast_publish_start
ON wind_forecast (start_time, publish_time DESC);
"""

ACTUAL_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_actual_start_time
ON actual_generation (start_time);
"""


# ── Schema Operations ──────────────────────────────────────────────────────────


def init_database(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """
    Initialize the DuckDB database with all required tables and indexes.

    Args:
        db_path: Path to the DuckDB database file. Uses default if None.

    Returns:
        Active DuckDB connection.
    """
    path = db_path or str(DB_PATH)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(path)

    conn.execute(ACTUAL_GENERATION_DDL)
    conn.execute(WIND_FORECAST_DDL)
    conn.execute(FORECAST_INDEX_DDL)
    conn.execute(ACTUAL_INDEX_DDL)

    return conn


def get_connection(db_path: str | None = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """
    Get a DuckDB connection.

    Args:
        db_path: Path to the DuckDB database file. Uses default if None.
        read_only: If True, opens connection in read-only mode.

    Returns:
        Active DuckDB connection.
    """
    path = db_path or str(DB_PATH)
    return duckdb.connect(path, read_only=read_only)


def drop_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Drop all WindSight tables (for re-ingestion)."""
    conn.execute("DROP TABLE IF EXISTS actual_generation;")
    conn.execute("DROP TABLE IF EXISTS wind_forecast;")
