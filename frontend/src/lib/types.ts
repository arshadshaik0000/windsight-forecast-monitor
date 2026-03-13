/**
 * WindSight API type definitions.
 * Mirrors backend Pydantic models for type-safe API consumption.
 */

// ── Generation Types ──────────────────────────────────────────────────────────

export interface GenerationPoint {
  timestamp: string;
  generation_mw: number;
}

export interface GenerationResponse {
  data: GenerationPoint[];
  count: number;
  start: string;
  end: string;
}

// ── Forecast Types ────────────────────────────────────────────────────────────

export interface ForecastPoint {
  timestamp: string;
  generation_mw: number;
  publish_time: string;
  horizon_hours: number;
}

export interface ForecastResponse {
  data: ForecastPoint[];
  count: number;
  start: string;
  end: string;
  horizon_hours: number;
}

// ── Metrics Types ─────────────────────────────────────────────────────────────

export interface ErrorMetrics {
  mean_absolute_error: number;
  median_absolute_error: number;
  p99_error: number;
  rmse: number;
  sample_count: number;
}

export interface HourlyError {
  hour: number;
  mae: number;
  sample_count: number;
}

export interface ReliabilityMetrics {
  p10_generation_mw: number;
  p20_generation_mw: number;
  mean_generation_mw: number;
  median_generation_mw: number;
  max_generation_mw: number;
  capacity_factor: number;
}

export interface MetricsResponse {
  error_metrics: ErrorMetrics;
  hourly_errors: HourlyError[];
  reliability: ReliabilityMetrics;
  horizon_hours: number;
}

// ── Dashboard State ───────────────────────────────────────────────────────────

export interface DashboardState {
  startDateTime: string;
  endDateTime: string;
  horizonHours: number;
  isLoading: boolean;
  error: string | null;
}
