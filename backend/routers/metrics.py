"""
Metrics API router — serves forecast accuracy and reliability metrics.

Endpoint: GET /api/v1/metrics
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.db.connection import get_db
from backend.models.schemas import (
    ErrorMetrics,
    HourlyError,
    MetricsResponse,
    ReliabilityMetrics,
)
from backend.services.cache import cache
from backend.services.forecast_processor import (
    compute_error_metrics,
    compute_hourly_errors,
    get_forecast_errors,
    get_reliability_metrics,
)

logger = logging.getLogger("windsight.api.metrics")
router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    start: datetime = Query(..., description="Start time (ISO 8601 UTC)"),
    end: datetime = Query(..., description="End time (ISO 8601 UTC)"),
    horizon: float = Query(
        default=4.0,
        ge=0,
        le=48,
        description="Forecast horizon in hours (0–48)",
    ),
) -> MetricsResponse:
    """
    Compute and return forecast accuracy and wind reliability metrics.

    Includes:
    - Error metrics: MAE, median, P99, RMSE
    - Hourly error breakdown by hour of day (0-23)
    - Wind reliability: P10, P20 generation levels
    """
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    # Check cache
    cache_params = {"start": str(start), "end": str(end), "horizon": horizon}
    cached = cache.get("metrics", cache_params)
    if cached is not None:
        return cached

    try:
        conn = get_db()

        # Compute forecast errors
        errors = get_forecast_errors(conn, start, end, horizon)
        error_stats = compute_error_metrics(errors)
        hourly = compute_hourly_errors(errors)

        # Compute reliability
        reliability = get_reliability_metrics(conn, start, end)

        response = MetricsResponse(
            error_metrics=ErrorMetrics(**error_stats),
            hourly_errors=[HourlyError(**h) for h in hourly],
            reliability=ReliabilityMetrics(**reliability),
            horizon_hours=horizon,
        )

        cache.set("metrics", cache_params, response, ttl=600)
        return response

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Run data ingestion first.",
        )
    except Exception as e:
        logger.error("Metrics query error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
