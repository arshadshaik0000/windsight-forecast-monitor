"""
WindSight Data Ingestion Pipeline.

Fetches wind generation actuals (FUELHH) and forecasts (WINDFOR) from
the BMRS Elexon API, normalizes schemas, and stores data in DuckDB.

Designed for:
  - Fault tolerance (retries with exponential backoff)
  - Incremental ingestion (daily batches)
  - Idempotent re-runs (INSERT OR REPLACE semantics)

Usage:
    python -m pipeline.ingest              # Full ingestion
    python -m pipeline.ingest --dry-run    # Validate API without writing
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import httpx
import pandas as pd

from pipeline.config import (
    BATCH_SIZE_DAYS,
    DATA_DIR,
    DATA_END_DATE,
    DATA_START_DATE,
    FUELHH_ENDPOINT,
    PARQUET_DIR,
    RAW_DIR,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_CONFIG,
    WINDFOR_ENDPOINT,
)
from pipeline.schema import init_database

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("windsight.ingest")


# ── HTTP Client ────────────────────────────────────────────────────────────────


def fetch_with_retry(
    url: str,
    params: dict[str, Any],
    retry_config: type | Any = RETRY_CONFIG,
) -> list[dict[str, Any]]:
    """
    Fetch JSON data from a URL with exponential backoff retry.

    Args:
        url: The API endpoint URL.
        params: Query parameters.
        retry_config: Retry configuration (delays, max retries, etc.)

    Returns:
        Parsed JSON response as a list of records.

    Raises:
        httpx.HTTPStatusError: If all retries are exhausted.
    """
    delay = retry_config.base_delay_seconds

    for attempt in range(1, retry_config.max_retries + 1):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = client.get(url, params=params)
                response.raise_for_status()

                # The stream endpoint returns newline-delimited JSON
                text = response.text.strip()
                if not text:
                    return []

                # Try parsing as JSON array first, then as NDJSON
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        return data
                    return [data]
                except json.JSONDecodeError:
                    records = []
                    for line in text.split("\n"):
                        line = line.strip()
                        if line:
                            records.append(json.loads(line))
                    return records

        except httpx.HTTPStatusError as e:
            if e.response.status_code in retry_config.retry_status_codes:
                logger.warning(
                    "Attempt %d/%d failed (HTTP %d). Retrying in %.1fs...",
                    attempt,
                    retry_config.max_retries,
                    e.response.status_code,
                    delay,
                )
                time.sleep(delay)
                delay = min(delay * retry_config.backoff_factor, retry_config.max_delay_seconds)
            else:
                raise
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning(
                "Attempt %d/%d failed (%s). Retrying in %.1fs...",
                attempt,
                retry_config.max_retries,
                type(e).__name__,
                delay,
            )
            time.sleep(delay)
            delay = min(delay * retry_config.backoff_factor, retry_config.max_delay_seconds)

    raise RuntimeError(f"All {retry_config.max_retries} retry attempts exhausted for {url}")


# ── Date Batching ──────────────────────────────────────────────────────────────


def generate_date_batches(
    start_date: str, end_date: str, batch_days: int = BATCH_SIZE_DAYS
) -> list[tuple[str, str]]:
    """
    Generate date range batches for incremental ingestion.

    Args:
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        batch_days: Number of days per batch.

    Returns:
        List of (batch_start, batch_end) date string tuples.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    batches: list[tuple[str, str]] = []

    current = start
    while current <= end:
        batch_end = min(current + timedelta(days=batch_days - 1), end)
        batches.append((current.strftime("%Y-%m-%d"), batch_end.strftime("%Y-%m-%d")))
        current = batch_end + timedelta(days=1)

    return batches


# ── Actual Generation Ingestion ────────────────────────────────────────────────


def fetch_actual_generation(
    settlement_date: str,
) -> pd.DataFrame:
    """
    Fetch actual wind generation data for a single settlement date.

    Fetches FUELHH dataset and filters for WIND fuel type.

    Args:
        settlement_date: Settlement date (YYYY-MM-DD).

    Returns:
        DataFrame with columns: start_time, settlement_date, settlement_period,
        generation_mw, fuel_type
    """
    params = {
        "settlementDateFrom": settlement_date,
        "settlementDateTo": settlement_date,
        "fuelType": "WIND",
    }

    logger.info("Fetching FUELHH for %s...", settlement_date)
    records = fetch_with_retry(FUELHH_ENDPOINT, params)

    if not records:
        logger.warning("No FUELHH data for %s", settlement_date)
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Normalize column names — API returns camelCase
    column_map = {
        "startTime": "start_time",
        "settlementDate": "settlement_date",
        "settlementPeriod": "settlement_period",
        "generation": "generation_mw",
        "fuelType": "fuel_type",
    }
    df = df.rename(columns=column_map)

    # Keep only required columns
    keep_cols = ["start_time", "settlement_date", "settlement_period", "generation_mw", "fuel_type"]
    available = [c for c in keep_cols if c in df.columns]
    df = df[available]

    # Type conversions
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["settlement_date"] = pd.to_datetime(df["settlement_date"]).dt.date
    df["generation_mw"] = pd.to_numeric(df["generation_mw"], errors="coerce")

    # Filter for WIND only (safety check)
    if "fuel_type" in df.columns:
        df = df[df["fuel_type"].str.upper() == "WIND"]

    logger.info("  → %d WIND records for %s", len(df), settlement_date)
    return df


# ── Forecast Ingestion ─────────────────────────────────────────────────────────


def fetch_wind_forecast(settlement_date: str) -> pd.DataFrame:
    """
    Fetch wind generation forecast data for a single settlement date.

    Fetches WINDFOR dataset filtered by TARGET start time (not publish time).
    The BMRS WINDFOR endpoint does not reliably filter by startTime, so we
    expand the publishDateTime window back 48 hours to capture late-December
    publishes that target the first January slots.

    Args:
        settlement_date: Settlement date (YYYY-MM-DD).

    Returns:
        DataFrame with columns: start_time, publish_time, generation_mw
    """
    date_obj = datetime.strptime(settlement_date, "%Y-%m-%d")
    publish_from = (date_obj - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00Z")
    publish_to = f"{settlement_date}T23:59:59Z"

    params = {
        "publishDateTimeFrom": publish_from,
        "publishDateTimeTo": publish_to,
    }

    logger.info("Fetching WINDFOR for %s...", settlement_date)
    records = fetch_with_retry(WINDFOR_ENDPOINT, params)

    if not records:
        logger.warning("No WINDFOR data for %s", settlement_date)
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Normalize column names
    column_map = {
        "startTime": "start_time",
        "publishTime": "publish_time",
        "generation": "generation_mw",
    }
    df = df.rename(columns=column_map)

    # Keep only required columns
    keep_cols = ["start_time", "publish_time", "generation_mw"]
    available = [c for c in keep_cols if c in df.columns]
    df = df[available]

    # Type conversions
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    df["generation_mw"] = pd.to_numeric(df["generation_mw"], errors="coerce")

    logger.info("  → %d forecast records for %s", len(df), settlement_date)
    return df


# ── DuckDB Loading ─────────────────────────────────────────────────────────────


def load_actual_generation(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """
    Load actual generation data into DuckDB, handling duplicates via INSERT OR REPLACE.

    Args:
        conn: Active DuckDB connection.
        df: DataFrame with actual generation data.

    Returns:
        Number of rows inserted.
    """
    if df.empty:
        return 0

    conn.execute(
        """
        INSERT OR REPLACE INTO actual_generation
        SELECT * FROM df
        """
    )
    return len(df)


def load_wind_forecast(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> int:
    """
    Load wind forecast data into DuckDB, handling duplicates via INSERT OR REPLACE.

    Args:
        conn: Active DuckDB connection.
        df: DataFrame with forecast data.

    Returns:
        Number of rows inserted.
    """
    if df.empty:
        return 0

    conn.execute(
        """
        INSERT OR REPLACE INTO wind_forecast
        SELECT * FROM df
        """
    )
    return len(df)


# ── Parquet Export ──────────────────────────────────────────────────────────────


def save_parquet(df: pd.DataFrame, name: str, date: str) -> Path:
    """Save a DataFrame as a Parquet file for archival/reprocessing."""
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    path = PARQUET_DIR / f"{name}_{date}.parquet"
    df.to_parquet(path, index=False, engine="pyarrow")
    return path


# ── Main Pipeline ──────────────────────────────────────────────────────────────


def run_ingestion(dry_run: bool = False) -> dict[str, int]:
    """
    Execute the full data ingestion pipeline.

    Steps:
        1. Initialize DuckDB schema
        2. Generate date batches for January 2024
        3. For each batch: fetch, normalize, store
        4. Report summary statistics

    Args:
        dry_run: If True, fetches and validates data without writing to DB.

    Returns:
        Dictionary with ingestion statistics.
    """
    logger.info("=" * 60)
    logger.info("WindSight Data Ingestion Pipeline")
    logger.info("  Date range: %s → %s", DATA_START_DATE, DATA_END_DATE)
    logger.info("  Dry run: %s", dry_run)
    logger.info("=" * 60)

    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize database
    conn: duckdb.DuckDBPyConnection | None = None
    if not dry_run:
        conn = init_database()
        logger.info("Database initialized at %s", conn)

    batches = generate_date_batches(DATA_START_DATE, DATA_END_DATE)
    logger.info("Processing %d daily batches...", len(batches))

    total_actual = 0
    total_forecast = 0
    errors: list[str] = []

    for batch_start, batch_end in batches:
        try:
            # Fetch actual generation
            actual_df = fetch_actual_generation(batch_start)
            if not actual_df.empty:
                save_parquet(actual_df, "actual", batch_start)
                if not dry_run and conn is not None:
                    total_actual += load_actual_generation(conn, actual_df)

            # Fetch forecast
            forecast_df = fetch_wind_forecast(batch_start)
            if not forecast_df.empty:
                save_parquet(forecast_df, "forecast", batch_start)
                if not dry_run and conn is not None:
                    total_forecast += load_wind_forecast(conn, forecast_df)

        except Exception as e:
            error_msg = f"Error processing {batch_start}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            # Continue with next batch — fault tolerance
            continue

    # Summary
    stats = {
        "actual_records": total_actual,
        "forecast_records": total_forecast,
        "batches_processed": len(batches) - len(errors),
        "errors": len(errors),
    }

    logger.info("=" * 60)
    logger.info("Ingestion Complete")
    logger.info("  Actual records:   %d", stats["actual_records"])
    logger.info("  Forecast records: %d", stats["forecast_records"])
    logger.info("  Batches OK:       %d / %d", stats["batches_processed"], len(batches))
    if errors:
        logger.warning("  Errors: %d", len(errors))
        for err in errors:
            logger.warning("    • %s", err)
    logger.info("=" * 60)

    if conn is not None:
        conn.close()

    return stats


# ── CLI Entrypoint ─────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entrypoint for the ingestion pipeline."""
    parser = argparse.ArgumentParser(description="WindSight Data Ingestion Pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate data without writing to the database",
    )
    args = parser.parse_args()

    stats = run_ingestion(dry_run=args.dry_run)
    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
