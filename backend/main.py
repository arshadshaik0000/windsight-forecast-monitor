"""
WindSight Forecast Monitor — FastAPI Application.

Production-grade REST API for wind power forecast monitoring.
Serves actual generation data, horizon-adjusted forecasts, and
forecast accuracy metrics.

Architecture:
    - FastAPI with async endpoints
    - DuckDB for time-series storage (read-only for API)
    - LRU cache for sub-200ms response times
    - CORS enabled for frontend consumption
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.connection import close_db, get_db
from backend.models.schemas import HealthResponse
from backend.routers import forecast, generation, metrics
from backend.services.cache import cache

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("windsight.app")


# ── Lifespan ───────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Startup: Initialize database connection and warm cache.
    Shutdown: Close database connection and clear cache.
    """
    logger.info("Starting WindSight API...")

    try:
        conn = get_db()
        actual_count = conn.execute("SELECT COUNT(*) FROM actual_generation").fetchone()
        forecast_count = conn.execute("SELECT COUNT(*) FROM wind_forecast").fetchone()
        logger.info(
            "Database connected — %d actual records, %d forecast records",
            actual_count[0] if actual_count else 0,
            forecast_count[0] if forecast_count else 0,
        )
    except FileNotFoundError:
        logger.warning(
            "Database not found. Run 'python -m pipeline.ingest' to populate data."
        )
    except Exception as e:
        logger.warning("Database connection failed: %s", e)

    yield

    logger.info("Shutting down WindSight API...")
    close_db()
    cache.invalidate()
    logger.info("Shutdown complete.")


# ── Application ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="WindSight Forecast Monitor API",
    description=(
        "REST API for monitoring UK wind power forecast accuracy. "
        "Provides actual wind generation data, horizon-adjusted forecasts, "
        "and comprehensive accuracy metrics."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────

_default_origins = {
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
}

_env_origins = os.getenv("WINDSIGHT_FRONTEND_ORIGINS", "")
for origin in _env_origins.split(","):
    origin = origin.strip()
    if origin:
        _default_origins.add(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_default_origins),
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(generation.router)
app.include_router(forecast.router)
app.include_router(metrics.router)


# ── Health Check ───────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """
    System health check.

    Returns database connectivity status and record counts for
    monitoring and load balancer health checks.
    """
    try:
        conn = get_db()
        actual = conn.execute("SELECT COUNT(*) FROM actual_generation").fetchone()
        forecast = conn.execute("SELECT COUNT(*) FROM wind_forecast").fetchone()
        return HealthResponse(
            status="ok",
            database="connected",
            actual_records=actual[0] if actual else 0,
            forecast_records=forecast[0] if forecast else 0,
        )
    except Exception:
        return HealthResponse(status="degraded", database="disconnected")


@app.get("/api/v1/cache/stats", tags=["system"])
async def cache_stats() -> dict:
    """Return cache performance statistics."""
    return cache.stats
