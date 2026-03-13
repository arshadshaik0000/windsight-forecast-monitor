"""
Forecast API router — serves horizon-adjusted wind generation forecasts.

Endpoint: GET /api/v1/forecast
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.db.connection import get_db
from backend.models.schemas import ForecastPoint, ForecastResponse
from backend.services.cache import cache
from backend.services.forecast_processor import get_horizon_forecast

logger = logging.getLogger("windsight.api.forecast")
router = APIRouter(prefix="/api/v1", tags=["forecast"])


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    start: datetime = Query(..., description="Start time (ISO 8601 UTC)"),
    end: datetime = Query(..., description="End time (ISO 8601 UTC)"),
    horizon: float = Query(
        default=4.0,
        ge=0,
        le=48,
        description="Forecast horizon in hours (0–48)",
    ),
) -> ForecastResponse:
    """
    Retrieve horizon-adjusted wind generation forecasts.

    For each target half-hour slot in the time range, returns the forecast
    that was published at least `horizon` hours before the target time.
    Uses the most recently published forecast that satisfies this constraint.
    """
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    # Check cache
    cache_params = {"start": str(start), "end": str(end), "horizon": horizon}
    cached = cache.get("forecast", cache_params)
    if cached is not None:
        return cached

    try:
        conn = get_db()
        forecast_data = get_horizon_forecast(conn, start, end, horizon)

        data = [
            ForecastPoint(
                timestamp=row["timestamp"],
                generation_mw=row["generation_mw"],
                publish_time=row["publish_time"],
                horizon_hours=round(row["horizon_hours"], 2),
            )
            for row in forecast_data
        ]

        response = ForecastResponse(
            data=data,
            count=len(data),
            start=start,
            end=end,
            horizon_hours=horizon,
        )

        cache.set("forecast", cache_params, response, ttl=600)
        return response

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Run data ingestion first.",
        )
    except Exception as e:
        logger.error("Forecast query error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
