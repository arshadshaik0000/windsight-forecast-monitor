'use client';

import React from 'react';

interface DateRangeSelectorProps {
  startDateTime: string;
  endDateTime: string;
  onStartChange: (dateTime: string) => void;
  onEndChange: (dateTime: string) => void;
}

/**
 * Date range selector for choosing the analysis window.
 * Constrains to January 2024 data range (UTC, 30-min granularity).
 */
export default function DateRangeSelector({
  startDateTime,
  endDateTime,
  onStartChange,
  onEndChange,
}: DateRangeSelectorProps) {
  return (
    <>
      <div className="control-group">
        <label className="control-label" htmlFor="start-date">
          Start Time (UTC)
        </label>
        <input
          id="start-date"
          type="datetime-local"
          className="control-input"
          value={startDateTime}
          min="2024-01-01T00:00"
          max="2024-01-31T23:30"
          step={1800}
          onChange={(e) => onStartChange(e.target.value)}
        />
        <span className="control-hint">UTC · 30-min steps</span>
      </div>
      <div className="control-group">
        <label className="control-label" htmlFor="end-date">
          End Time (UTC)
        </label>
        <input
          id="end-date"
          type="datetime-local"
          className="control-input"
          value={endDateTime}
          min="2024-01-01T00:00"
          max="2024-01-31T23:30"
          step={1800}
          onChange={(e) => onEndChange(e.target.value)}
        />
        <span className="control-hint">UTC · 30-min steps</span>
      </div>
    </>
  );
}
