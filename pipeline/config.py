"""
Pipeline configuration for WindSight data ingestion.

Centralizes all configuration for API endpoints, date ranges,
retry policies, and storage paths.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


# ── API Configuration ──────────────────────────────────────────────────────────

BMRS_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

FUELHH_ENDPOINT = f"{BMRS_BASE_URL}/datasets/FUELHH/stream"
WINDFOR_ENDPOINT = f"{BMRS_BASE_URL}/datasets/WINDFOR/stream"

# ── Date Range ─────────────────────────────────────────────────────────────────

DATA_START_DATE = "2024-01-01"
DATA_END_DATE = "2024-01-31"

# ── Storage Paths ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("WINDSIGHT_DATA_DIR", str(PROJECT_ROOT / "data")))
RAW_DIR = DATA_DIR / "raw"
PARQUET_DIR = DATA_DIR / "parquet"
DB_PATH = Path(os.environ.get("WINDSIGHT_DB_PATH", str(DATA_DIR / "windsight.duckdb")))

# ── Retry Configuration ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class RetryConfig:
    """Exponential backoff retry configuration."""

    max_retries: int = 5
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_factor: float = 2.0
    retry_status_codes: tuple[int, ...] = field(
        default_factory=lambda: (429, 500, 502, 503, 504)
    )


RETRY_CONFIG = RetryConfig()

# ── Ingestion Batch Configuration ──────────────────────────────────────────────

# Fetch data in daily batches to avoid API timeouts and memory pressure
BATCH_SIZE_DAYS = 1

# Maximum concurrent requests (be polite to the BMRS API)
MAX_CONCURRENT_REQUESTS = 2

# Request timeout in seconds
REQUEST_TIMEOUT_SECONDS = 60
