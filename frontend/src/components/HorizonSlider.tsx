'use client';

import React from 'react';

interface HorizonSliderProps {
  value: number;
  onChange: (value: number) => void;
}

/**
 * Forecast horizon slider (0–48 hours).
 *
 * Controls how far ahead the forecast must have been published
 * relative to the target time.
 */
export default function HorizonSlider({ value, onChange }: HorizonSliderProps) {
  return (
    <div className="control-group horizon-slider-container">
      <label className="control-label" htmlFor="horizon-slider">
        Forecast Horizon (hours before target)
        <span className="horizon-value">{value}h</span>
      </label>
      <input
        id="horizon-slider"
        type="range"
        className="horizon-slider"
        min={0}
        max={48}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="slider-labels">
        <span>0h (nowcast)</span>
        <span>12h</span>
        <span>24h</span>
        <span>36h</span>
        <span>48h</span>
      </div>
    </div>
  );
}
