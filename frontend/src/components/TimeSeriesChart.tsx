'use client';

import React, { useMemo, useRef, useEffect, useState } from 'react';
import type { GenerationResponse, ForecastResponse } from '@/lib/types';

/**
 * Dynamic import for ECharts to avoid SSR issues.
 * We use the core echarts API directly for maximum control.
 */

interface TimeSeriesChartProps {
  generation: GenerationResponse | null;
  forecast: ForecastResponse | null;
  theme: 'light' | 'dark';
}

/**
 * Interactive time series chart using Apache ECharts.
 *
 * Features:
 * - Dual Y-axis with actual (blue) and forecast (green) lines
 * - DataZoom for interactive range selection
 * - Rich tooltips with cross-series comparison
 * - Responsive resizing
 * - Smooth animations
 */
export default function TimeSeriesChart({
  generation,
  forecast,
  theme,
}: TimeSeriesChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<any>(null);
  const [echartsLib, setEchartsLib] = useState<any>(null);

  // ── Dynamic Import ECharts ────────────────────────────────────────────────
  useEffect(() => {
    import('echarts').then((mod) => setEchartsLib(mod));
  }, []);

  // ── Chart Data ──────────────────────────────────────────────────────────────
  const chartData = useMemo(() => {
    const actualData = (generation?.data ?? []).map((d) => [d.timestamp, d.generation_mw]);
    const forecastData = (forecast?.data ?? []).map((d) => [d.timestamp, d.generation_mw]);
    return { actualData, forecastData };
  }, [generation, forecast]);

  // ── Initialize & Update Chart ────────────────────────────────────────────────
  useEffect(() => {
    if (!echartsLib || !chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echartsLib.init(chartRef.current, undefined, {
        renderer: 'canvas',
      });
    }

    const chart = chartInstance.current;

    const styles = getComputedStyle(document.documentElement);
    const colorActual = styles.getPropertyValue('--chart-actual').trim() || '#4da3ff';
    const colorForecast = styles.getPropertyValue('--chart-forecast').trim() || '#5ad6a0';
    const colorAxis = styles.getPropertyValue('--chart-axis').trim() || '#7a8ca3';
    const colorGrid = styles.getPropertyValue('--chart-grid').trim() || 'rgba(122,140,163,0.25)';
    const colorTooltipBg = styles.getPropertyValue('--chart-tooltip-bg').trim() || 'rgba(16,20,32,0.95)';
    const colorTooltipBorder = styles.getPropertyValue('--chart-tooltip-border').trim() || 'rgba(122,140,163,0.35)';
    const colorBg = styles.getPropertyValue('--chart-surface').trim() || 'transparent';
    const colorZoomTrack = styles.getPropertyValue('--chart-zoom-track').trim() || 'rgba(122,140,163,0.25)';
    const colorZoomHandle = styles.getPropertyValue('--chart-zoom-handle').trim() || colorActual;
    const textPrimary = styles.getPropertyValue('--text-primary').trim() || '#e8edf5';
    const textMuted = styles.getPropertyValue('--text-muted').trim() || '#6b768a';

    const option = {
      backgroundColor: colorBg || 'transparent',
      grid: {
        top: 24,
        right: 32,
        bottom: 82,
        left: 74,
        containLabel: false,
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: colorTooltipBg,
        borderColor: colorTooltipBorder,
        borderWidth: 1,
        textStyle: {
          color: textPrimary,
          fontFamily: 'Inter, sans-serif',
          fontSize: 12,
        },
        axisPointer: {
          type: 'cross',
          lineStyle: {
            color: colorActual,
            opacity: 0.35,
          },
          crossStyle: {
            color: colorActual,
            opacity: 0.3,
          },
        },
        formatter: (params: any) => {
          if (!params || params.length === 0) return '';
          const time = new Date(params[0].value[0]).toLocaleString('en-GB', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'UTC',
          });
          let html = `<div style="font-weight:600;margin-bottom:6px">${time} UTC</div>`;
          params.forEach((p: any) => {
            const val = p.value[1] != null ? `${Number(p.value[1]).toLocaleString()} MW` : 'N/A';
            html += `<div style="display:flex;align-items:center;gap:6px;margin-top:3px">
              <span style="width:8px;height:8px;border-radius:50%;background:${p.color};display:inline-block"></span>
              <span style="flex:1">${p.seriesName}</span>
              <span style="font-weight:600;font-family:'JetBrains Mono',monospace">${val}</span>
            </div>`;
          });
          return html;
        },
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: colorAxis, opacity: 0.4 } },
        axisTick: { lineStyle: { color: colorAxis, opacity: 0.3 } },
        axisLabel: {
          color: textMuted,
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          formatter: (value: number) => {
            const d = new Date(value);
            return `${d.getUTCDate()}/${d.getUTCMonth() + 1}\n${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
          },
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        name: 'MW',
        nameTextStyle: {
          color: textMuted,
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          padding: [0, 40, 0, 0],
        },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: textMuted,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          formatter: (val: number) => val >= 1000 ? `${(val / 1000).toFixed(1)}k` : String(val),
        },
        splitLine: {
          lineStyle: {
            color: colorGrid,
            type: 'dashed',
          },
        },
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
        },
        {
          type: 'slider',
          start: 0,
          end: 100,
          height: 30,
          bottom: 10,
          borderColor: colorZoomTrack,
          backgroundColor: 'transparent',
          fillerColor: colorZoomTrack,
          handleStyle: {
            color: colorZoomHandle,
            borderWidth: 0,
            shadowBlur: 6,
            shadowColor: `${colorZoomHandle}55`,
          },
          textStyle: {
            color: textMuted,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
          },
          dataBackground: {
            lineStyle: { color: colorActual, opacity: 0.25 },
            areaStyle: { color: colorActual, opacity: 0.08 },
          },
        },
      ],
      series: [
        {
          name: 'Actual Generation',
          type: 'line',
          data: chartData.actualData,
          smooth: 0.2,
          symbol: 'none',
          lineStyle: {
            color: colorActual,
            width: 2.4,
          },
          areaStyle: {
            color: colorActual,
            opacity: 0.14,
          },
        },
        {
          name: 'Forecast',
          type: 'line',
          data: chartData.forecastData,
          smooth: 0.2,
          symbol: 'none',
          lineStyle: {
            color: colorForecast,
            width: 2.2,
            type: 'dashed',
          },
          areaStyle: {
            color: colorForecast,
            opacity: 0.12,
          },
        },
      ],
      animation: true,
      animationDuration: 800,
      animationEasing: 'cubicOut',
    };

    chart.setOption(option, { notMerge: true });

    // Responsive resize
    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [echartsLib, chartData, theme]);

  // ── Cleanup ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      chartInstance.current?.dispose();
      chartInstance.current = null;
    };
  }, []);

  return (
    <div
      ref={chartRef}
      style={{ width: '100%', height: '450px', minHeight: '300px' }}
    />
  );
}
