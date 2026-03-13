'use client';

import React from 'react';
import type { MetricsResponse } from '@/lib/types';

interface MetricsPanelProps {
  metrics: MetricsResponse | null;
  isLoading: boolean;
}

/**
 * Metrics panel displaying forecast accuracy and reliability metrics.
 * Shows KPI cards for MAE, median error, P99, RMSE, and wind reliability.
 */
export default function MetricsPanel({ metrics, isLoading }: MetricsPanelProps) {
  if (isLoading) {
    return (
      <div className="metrics-grid">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="metric-card">
            <div className="metric-label">Loading...</div>
            <div className="metric-value" style={{ opacity: 0.2 }}>
              —
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!metrics) return null;

  const { error_metrics, reliability } = metrics;

  const cards = [
    {
      label: 'Mean Absolute Error',
      value: error_metrics.mean_absolute_error.toLocaleString(),
      unit: 'MW',
      detail: `${error_metrics.sample_count} samples`,
    },
    {
      label: 'Median Absolute Error',
      value: error_metrics.median_absolute_error.toLocaleString(),
      unit: 'MW',
      detail: 'Typical deviation magnitude',
    },
    {
      label: 'P99 Error',
      value: error_metrics.p99_error.toLocaleString(),
      unit: 'MW',
      detail: '99th percentile error',
    },
    {
      label: 'RMSE',
      value: error_metrics.rmse.toLocaleString(),
      unit: 'MW',
      detail: 'Root mean squared error',
    },
    {
      label: 'Reliable Supply (P10)',
      value: reliability.p10_generation_mw.toLocaleString(),
      unit: 'MW',
      detail: 'Wind exceeds this 90% of time',
    },
    {
      label: 'Capacity Factor',
      value: (reliability.capacity_factor * 100).toFixed(1),
      unit: '%',
      detail: `Mean: ${reliability.mean_generation_mw.toLocaleString()} MW`,
    },
  ];

  return (
    <div className="metrics-grid">
      {cards.map((card) => (
        <div key={card.label} className="metric-card">
          <div className="metric-label">{card.label}</div>
          <div className="metric-value">
            {card.value}
            <span className="metric-unit">{card.unit}</span>
          </div>
          <div className="metric-detail">{card.detail}</div>
        </div>
      ))}
    </div>
  );
}
