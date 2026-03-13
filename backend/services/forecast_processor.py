"""
Forecast Processor — Core Horizon Selection Algorithm.

For each target time, selects the latest forecast published at least H hours
before the target time. This is the heart of the forecasting logic.

Algorithm:
    1. For each half-hour target time slot:
       - Filter forecasts where publish_time <= target_time - horizon
       - Select the one with the latest publish_time
    2. Return the matched forecast generation
    3. Skip target times with no matching forecast

This is implemented as an efficient SQL query using DuckDB's window functions
(QUALIFY + ROW_NUMBER) for O(n log n) performance.
"""

from __future__ import annotations

import logging
from datetime import datetime

import duckdb

logger = logging.getLogger("windsight.forecast")


def get_horizon_forecast(
    conn: duckdb.DuckDBPyConnection,
    start: datetime,
    end: datetime,
    horizon_hours: float,
) -> list[dict]:
    """
    Select forecasts for each target time using the horizon constraint.

    For each target time in the range, finds the latest forecast published
    at least `horizon_hours` before that target time.

    Args:
        conn: DuckDB connection.
        start: Start of the time range (UTC).
        end: End of the time range (UTC).
        horizon_hours: Minimum forecast horizon in hours.

    Returns:
        List of dicts with keys: timestamp, generation_mw, publish_time, horizon_hours
    """
    query = """
    WITH ranked_forecasts AS (
        SELECT
            f.start_time AS timestamp,
            f.generation_mw,
            f.publish_time,
            -- Actual horizon in hours between publish and target
            EXTRACT(EPOCH FROM (f.start_time - f.publish_time)) / 3600.0 AS actual_horizon_hours,
            -- Rank by most recent publish_time per target slot
            ROW_NUMBER() OVER (
                PARTITION BY f.start_time
                ORDER BY f.publish_time DESC, f.generation_mw DESC
            ) AS rn
        FROM wind_forecast f
        WHERE f.start_time >= $1
          AND f.start_time <= $2
          AND f.publish_time <= f.start_time - INTERVAL ($3::DOUBLE || ' hours')
    )
    SELECT
        timestamp,
        generation_mw,
        publish_time,
        actual_horizon_hours AS horizon_hours
    FROM ranked_forecasts
    WHERE rn = 1
    ORDER BY timestamp;
    """

    try:
        result = conn.execute(query, [start, end, horizon_hours]).fetchall()
        columns = ["timestamp", "generation_mw", "publish_time", "horizon_hours"]
        return [dict(zip(columns, row)) for row in result]
    except Exception as e:
        logger.error("Forecast query failed: %s", e)
        raise


def get_forecast_errors(
    conn: duckdb.DuckDBPyConnection,
    start: datetime,
    end: datetime,
    horizon_hours: float,
) -> list[dict]:
    """
    Compute forecast errors by joining actuals with horizon-selected forecasts.

    Returns paired (actual, forecast) data for error analysis.

    Args:
        conn: DuckDB connection.
        start: Start of the time range (UTC).
        end: End of the time range (UTC).
        horizon_hours: Minimum forecast horizon in hours.

    Returns:
        List of dicts with: timestamp, actual_mw, forecast_mw, error_mw, abs_error_mw, hour_of_day
    """
    query = """
    WITH ranked_forecasts AS (
        SELECT
            f.start_time AS timestamp,
            f.generation_mw AS forecast_mw,
            f.publish_time,
            ROW_NUMBER() OVER (
                PARTITION BY f.start_time
                ORDER BY f.publish_time DESC, f.generation_mw DESC
            ) AS rn
        FROM wind_forecast f
        WHERE f.start_time >= $1
          AND f.start_time <= $2
          AND f.publish_time <= f.start_time - INTERVAL ($3::DOUBLE || ' hours')
    ),
    best_forecast AS (
        SELECT timestamp, forecast_mw, publish_time
        FROM ranked_forecasts
        WHERE rn = 1
    )
    SELECT
        a.start_time AS timestamp,
        a.generation_mw AS actual_mw,
        bf.forecast_mw,
        (bf.forecast_mw - a.generation_mw) AS error_mw,
        ABS(bf.forecast_mw - a.generation_mw) AS abs_error_mw,
        EXTRACT(HOUR FROM a.start_time) AS hour_of_day
    FROM actual_generation a
    INNER JOIN best_forecast bf ON a.start_time = bf.timestamp
    WHERE a.start_time >= $1
      AND a.start_time <= $2
    ORDER BY a.start_time;
    """

    try:
        result = conn.execute(query, [start, end, horizon_hours]).fetchall()
        columns = ["timestamp", "actual_mw", "forecast_mw", "error_mw", "abs_error_mw", "hour_of_day"]
        return [dict(zip(columns, row)) for row in result]
    except Exception as e:
        logger.error("Error query failed: %s", e)
        raise


def compute_error_metrics(errors: list[dict]) -> dict:
    """
    Compute aggregate error statistics from forecast errors.

    Args:
        errors: List of error dicts from get_forecast_errors.

    Returns:
        Dict with MAE, median absolute error, P99 error, RMSE, and sample count.
    """
    if not errors:
        return {
            "mean_absolute_error": 0.0,
            "median_absolute_error": 0.0,
            "p99_error": 0.0,
            "rmse": 0.0,
            "sample_count": 0,
        }

    abs_errors = sorted([e["abs_error_mw"] for e in errors])
    n = len(abs_errors)

    mae = sum(abs_errors) / n
    median_idx = n // 2
    median = abs_errors[median_idx] if n % 2 == 1 else (abs_errors[median_idx - 1] + abs_errors[median_idx]) / 2
    p99_idx = min(int(n * 0.99), n - 1)
    p99 = abs_errors[p99_idx]
    rmse = (sum(e["abs_error_mw"] ** 2 for e in errors) / n) ** 0.5

    return {
        "mean_absolute_error": round(mae, 2),
        "median_absolute_error": round(median, 2),
        "p99_error": round(p99, 2),
        "rmse": round(rmse, 2),
        "sample_count": n,
    }


def compute_hourly_errors(errors: list[dict]) -> list[dict]:
    """
    Compute MAE grouped by hour of day.

    Args:
        errors: List of error dicts from get_forecast_errors.

    Returns:
        List of dicts with hour, mae, sample_count for each hour 0-23.
    """
    from collections import defaultdict

    hourly: dict[int, list[float]] = defaultdict(list)
    for e in errors:
        hourly[int(e["hour_of_day"])].append(e["abs_error_mw"])

    result = []
    for hour in range(24):
        errs = hourly.get(hour, [])
        result.append({
            "hour": hour,
            "mae": round(sum(errs) / len(errs), 2) if errs else 0.0,
            "sample_count": len(errs),
        })
    return result


def get_reliability_metrics(
    conn: duckdb.DuckDBPyConnection,
    start: datetime,
    end: datetime,
) -> dict:
    """
    Compute wind generation reliability metrics (P10, P20, etc.)

    These quantiles indicate how much wind power can reliably meet demand:
    - P10: 90% of the time, generation exceeds this level
    - P20: 80% of the time, generation exceeds this level

    Args:
        conn: DuckDB connection.
        start: Start of the time range (UTC).
        end: End of the time range (UTC).

    Returns:
        Dict with reliability metrics.
    """
    query = """
    SELECT
        PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY generation_mw) AS p10,
        PERCENTILE_CONT(0.20) WITHIN GROUP (ORDER BY generation_mw) AS p20,
        AVG(generation_mw) AS mean_gen,
        MEDIAN(generation_mw) AS median_gen,
        MAX(generation_mw) AS max_gen
    FROM actual_generation
    WHERE start_time >= $1
      AND start_time <= $2;
    """

    result = conn.execute(query, [start, end]).fetchone()
    if result is None or result[0] is None:
        return {
            "p10_generation_mw": 0.0,
            "p20_generation_mw": 0.0,
            "mean_generation_mw": 0.0,
            "median_generation_mw": 0.0,
            "max_generation_mw": 0.0,
            "capacity_factor": 0.0,
        }

    p10, p20, mean_gen, median_gen, max_gen = result

    # UK installed wind capacity ~30 GW (approximate for capacity factor)
    installed_capacity_mw = 30000.0
    capacity_factor = mean_gen / installed_capacity_mw if installed_capacity_mw > 0 else 0.0

    return {
        "p10_generation_mw": round(p10, 2),
        "p20_generation_mw": round(p20, 2),
        "mean_generation_mw": round(mean_gen, 2),
        "median_generation_mw": round(median_gen, 2),
        "max_generation_mw": round(max_gen, 2),
        "capacity_factor": round(capacity_factor, 4),
    }
