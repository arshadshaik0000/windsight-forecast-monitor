/**
 * WindSight API client.
 * Handles all HTTP communication with the FastAPI backend.
 */

import type {
  GenerationResponse,
  ForecastResponse,
  MetricsResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling and timeout.
 */
async function apiFetch<T>(
  endpoint: string,
  params: Record<string, string | number>,
): Promise<T> {
  const url = new URL(`${API_BASE}${endpoint}`);
  Object.entries(params).forEach(([key, val]) =>
    url.searchParams.set(key, String(val)),
  );

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url.toString(), {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) {
      const errorBody = await response.text().catch(() => 'Unknown error');
      throw new Error(`API error ${response.status}: ${errorBody}`);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Request timed out. The server may be processing a large query.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Fetch actual wind generation data for a time range.
 */
export async function fetchGeneration(
  start: string,
  end: string,
): Promise<GenerationResponse> {
  return apiFetch<GenerationResponse>('/api/v1/generation', { start, end });
}

/**
 * Fetch horizon-adjusted wind generation forecasts.
 */
export async function fetchForecast(
  start: string,
  end: string,
  horizon: number,
): Promise<ForecastResponse> {
  return apiFetch<ForecastResponse>('/api/v1/forecast', {
    start,
    end,
    horizon,
  });
}

/**
 * Fetch forecast accuracy and reliability metrics.
 */
export async function fetchMetrics(
  start: string,
  end: string,
  horizon: number,
): Promise<MetricsResponse> {
  return apiFetch<MetricsResponse>('/api/v1/metrics', {
    start,
    end,
    horizon,
  });
}
