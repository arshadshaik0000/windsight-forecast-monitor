"""
Pydantic models for API request validation and response serialization.

These schemas define the contract between the backend API and frontend clients.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# ── Response Models ────────────────────────────────────────────────────────────


class GenerationPoint(BaseModel):
    """A single actual generation data point."""

    timestamp: datetime = Field(..., description="UTC timestamp")
    generation_mw: float = Field(..., description="Wind generation in MW")


class ForecastPoint(BaseModel):
    """A single forecast data point (after horizon selection)."""

    timestamp: datetime = Field(..., description="Target time (UTC)")
    generation_mw: float = Field(..., description="Forecast generation in MW")
    publish_time: datetime = Field(..., description="When forecast was published")
    horizon_hours: float = Field(..., description="Actual forecast horizon in hours")


class GenerationResponse(BaseModel):
    """Response for /api/v1/generation endpoint."""

    data: list[GenerationPoint]
    count: int
    start: datetime
    end: datetime


class ForecastResponse(BaseModel):
    """Response for /api/v1/forecast endpoint."""

    data: list[ForecastPoint]
    count: int
    start: datetime
    end: datetime
    horizon_hours: float


class ErrorMetrics(BaseModel):
    """Forecast error metrics summary."""

    mean_absolute_error: float = Field(..., description="MAE in MW")
    median_absolute_error: float = Field(..., description="Median absolute error in MW")
    p99_error: float = Field(..., description="99th percentile absolute error in MW")
    rmse: float = Field(..., description="Root mean squared error in MW")
    sample_count: int = Field(..., description="Number of data points")


class HourlyError(BaseModel):
    """Forecast error for a specific hour of day."""

    hour: int
    mae: float
    sample_count: int


class HorizonError(BaseModel):
    """Forecast error at a specific horizon."""

    horizon_hours: float
    mae: float
    sample_count: int


class ReliabilityMetrics(BaseModel):
    """Wind generation reliability metrics."""

    p10_generation_mw: float = Field(..., description="10th percentile generation (MW)")
    p20_generation_mw: float = Field(..., description="20th percentile generation (MW)")
    mean_generation_mw: float = Field(..., description="Mean generation (MW)")
    median_generation_mw: float = Field(..., description="Median generation (MW)")
    max_generation_mw: float = Field(..., description="Maximum generation (MW)")
    capacity_factor: float = Field(..., description="Capacity factor (0-1)")


class MetricsResponse(BaseModel):
    """Response for /api/v1/metrics endpoint."""

    error_metrics: ErrorMetrics
    hourly_errors: list[HourlyError]
    reliability: ReliabilityMetrics
    horizon_hours: float


class HealthResponse(BaseModel):
    """Response for /health endpoint."""

    status: str = "ok"
    database: str = "connected"
    actual_records: int = 0
    forecast_records: int = 0
