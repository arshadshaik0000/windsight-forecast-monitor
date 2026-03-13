"""
Generation API router — serves actual wind generation data.

Endpoint: GET /api/v1/generation
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.db.connection import get_db
from backend.models.schemas import GenerationPoint, GenerationResponse
from backend.services.cache import cache

logger = logging.getLogger("windsight.api.generation")
router = APIRouter(prefix="/api/v1", tags=["generation"])


@router.get("/generation", response_model=GenerationResponse)
async def get_generation(
    start: datetime = Query(..., description="Start time (ISO 8601 UTC)"),
    end: datetime = Query(..., description="End time (ISO 8601 UTC)"),
) -> GenerationResponse:
    """
    Retrieve actual wind generation data for a time range.

    Returns half-hourly actual wind generation readings from BMRS FUELHH,
    optimized for time-series chart rendering.
    """
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    # Check cache
    cache_params = {"start": str(start), "end": str(end)}
    cached = cache.get("generation", cache_params)
    if cached is not None:
        return cached

    try:
        conn = get_db()
        query = """
        SELECT start_time AS timestamp, generation_mw
        FROM actual_generation
        WHERE start_time >= $1 AND start_time <= $2
        ORDER BY start_time;
        """
        rows = conn.execute(query, [start, end]).fetchall()

        data = [
            GenerationPoint(timestamp=row[0], generation_mw=row[1])
            for row in rows
        ]

        response = GenerationResponse(
            data=data,
            count=len(data),
            start=start,
            end=end,
        )

        cache.set("generation", cache_params, response, ttl=600)
        return response

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Run data ingestion first.",
        )
    except Exception as e:
        logger.error("Generation query error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
