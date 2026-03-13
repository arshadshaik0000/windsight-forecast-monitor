'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchGeneration,
  fetchForecast,
  fetchMetrics,
} from '@/lib/api';
import type {
  GenerationResponse,
  ForecastResponse,
  MetricsResponse,
} from '@/lib/types';
import TimeSeriesChart from './TimeSeriesChart';
import MetricsPanel from './MetricsPanel';
import DateRangeSelector from './DateRangeSelector';
import HorizonSlider from './HorizonSlider';
import ThemeToggle from './ThemeToggle';
import { useTheme } from './ThemeProvider';

/**
 * Main Dashboard component.
 *
 * Orchestrates data fetching, state management, and renders the
 * complete monitoring interface: controls, metrics, and chart.
 */
export default function Dashboard() {
  const { theme } = useTheme();
  // ── State ───────────────────────────────────────────────────────────────────
  const [startDateTime, setStartDateTime] = useState('2024-01-01T00:00');
  const [endDateTime, setEndDateTime] = useState('2024-01-07T23:30');
  const [horizonHours, setHorizonHours] = useState(4);

  const [generation, setGeneration] = useState<GenerationResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Data Fetching ───────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const start = `${startDateTime}:00Z`;
    const end = `${endDateTime}:00Z`;

    try {
      const [genData, fcData, metricsData] = await Promise.allSettled([
        fetchGeneration(start, end),
        fetchForecast(start, end, horizonHours),
        fetchMetrics(start, end, horizonHours),
      ]);

      // Fault tolerance: show whatever data we got
      if (genData.status === 'fulfilled') {
        setGeneration(genData.value);
      } else {
        console.error('Generation fetch failed:', genData.reason);
      }

      if (fcData.status === 'fulfilled') {
        setForecast(fcData.value);
      } else {
        console.error('Forecast fetch failed:', fcData.reason);
      }

      if (metricsData.status === 'fulfilled') {
        setMetrics(metricsData.value);
      } else {
        console.error('Metrics fetch failed:', metricsData.reason);
      }

      // Only show error if ALL requests failed
      const allFailed =
        genData.status === 'rejected' &&
        fcData.status === 'rejected' &&
        metricsData.status === 'rejected';

      if (allFailed) {
        setError(
          'Unable to connect to the WindSight API. Ensure the backend is running on port 8000.',
        );
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'An unexpected error occurred',
      );
    } finally {
      setIsLoading(false);
    }
  }, [startDateTime, endDateTime, horizonHours]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Render ──────────────────────────────────────────────────────────────────
  const statusClass = error ? 'error' : isLoading ? 'loading' : '';

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="hero-block">
          <div className="app-logo">
            <div className="logo-mark">
              <span className="logo-glyph" />
            </div>
            <div>
              <h1 className="app-title">WindSight</h1>
              <p className="app-subtitle">UK Wind Power Forecast Monitor</p>
            </div>
          </div>
          <div className="header-actions">
            <div className="header-status">
              <span className={`status-dot ${statusClass}`} />
              {isLoading
                ? 'Fetching latest data'
                : error
                  ? 'API unavailable'
                  : `${generation?.count ?? 0} actual · ${forecast?.count ?? 0} forecast points`}
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Controls */}
      <div className="controls-bar">
        <DateRangeSelector
          startDateTime={startDateTime}
          endDateTime={endDateTime}
          onStartChange={setStartDateTime}
          onEndChange={setEndDateTime}
        />
        <HorizonSlider value={horizonHours} onChange={setHorizonHours} />
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <span className="error-icon" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {/* Metrics */}
      <MetricsPanel metrics={metrics} isLoading={isLoading} />

      {/* Chart */}
      <div className="chart-container">
        <div className="chart-header">
          <h2 className="chart-title">Wind Generation — Actual vs Forecast</h2>
          <div className="chart-legend">
            <span className="legend-item">
              <span className="legend-dot actual"></span>
              Actual Generation
            </span>
            <span className="legend-item">
              <span className="legend-dot forecast"></span>
              Forecast ({horizonHours}h horizon)
            </span>
          </div>
        </div>
        {isLoading ? (
          <div className="loading-overlay">
            <div className="loading-spinner" />
            <span className="loading-text">Fetching wind data...</span>
          </div>
        ) : !generation?.data?.length && !forecast?.data?.length ? (
          <div className="empty-state">
            <div className="empty-graphic" aria-hidden="true" />
            <span>No data for this window.</span>
            <span>Adjust the date/time range or run the ingestion pipeline.</span>
          </div>
        ) : (
          <TimeSeriesChart generation={generation} forecast={forecast} theme={theme} />
        )}
      </div>
    </div>
  );
}
