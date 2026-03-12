import React from 'react';

const W = 640;
const H = 280;
const PAD = { top: 20, right: 20, bottom: 40, left: 60 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

function formatTick(val) {
  if (Math.abs(val) >= 1000) return val.toFixed(0);
  if (Math.abs(val) >= 1) return val.toFixed(2);
  return val.toFixed(4);
}

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function MeasurementChart({ measurements, unit }) {
  if (!measurements || measurements.length < 2) {
    return (
      <div className="chart-empty">
        {measurements?.length === 1
          ? 'Only one data point — need at least 2 for a chart.'
          : 'No measurement data to chart.'}
      </div>
    );
  }

  const sorted = [...measurements].sort(
    (a, b) => new Date(a.measured_at) - new Date(b.measured_at)
  );

  const values = sorted.map((m) => parseFloat(m.value));
  const times = sorted.map((m) => new Date(m.measured_at).getTime());

  let minVal = Math.min(...values);
  let maxVal = Math.max(...values);
  const valRange = maxVal - minVal || 1;
  minVal -= valRange * 0.1;
  maxVal += valRange * 0.1;

  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const timeRange = maxTime - minTime || 1;

  function x(t) {
    return PAD.left + ((t - minTime) / timeRange) * PLOT_W;
  }
  function y(v) {
    return PAD.top + PLOT_H - ((v - minVal) / (maxVal - minVal)) * PLOT_H;
  }

  const points = sorted.map((m, i) => ({
    cx: x(times[i]),
    cy: y(values[i]),
    value: values[i],
    time: m.measured_at,
  }));

  const polyline = points.map((p) => `${p.cx},${p.cy}`).join(' ');

  // Y-axis ticks (5 ticks)
  const yTicks = [];
  for (let i = 0; i <= 4; i++) {
    const val = minVal + ((maxVal - minVal) * i) / 4;
    yTicks.push({ val, py: y(val) });
  }

  // X-axis ticks (up to 5 evenly spaced)
  const xTickCount = Math.min(5, sorted.length);
  const xTicks = [];
  for (let i = 0; i < xTickCount; i++) {
    const idx = Math.round((i / (xTickCount - 1)) * (sorted.length - 1));
    xTicks.push({ label: formatTime(sorted[idx].measured_at), px: x(times[idx]) });
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      style={{ width: '100%', maxWidth: W, height: 'auto' }}
    >
      {/* Grid lines */}
      {yTicks.map((t, i) => (
        <line
          key={i}
          x1={PAD.left}
          x2={W - PAD.right}
          y1={t.py}
          y2={t.py}
          stroke="var(--border)"
          strokeWidth="0.5"
        />
      ))}

      {/* Y-axis labels */}
      {yTicks.map((t, i) => (
        <text
          key={i}
          x={PAD.left - 8}
          y={t.py + 4}
          textAnchor="end"
          fill="var(--text-muted)"
          fontSize="10"
          fontFamily="inherit"
        >
          {formatTick(t.val)}
        </text>
      ))}

      {/* X-axis labels */}
      {xTicks.map((t, i) => (
        <text
          key={i}
          x={t.px}
          y={H - 8}
          textAnchor="middle"
          fill="var(--text-muted)"
          fontSize="10"
          fontFamily="inherit"
        >
          {t.label}
        </text>
      ))}

      {/* Unit label */}
      <text
        x={12}
        y={PAD.top + PLOT_H / 2}
        textAnchor="middle"
        fill="var(--text-muted)"
        fontSize="10"
        fontFamily="inherit"
        transform={`rotate(-90, 12, ${PAD.top + PLOT_H / 2})`}
      >
        {unit || 'Value'}
      </text>

      {/* Line */}
      <polyline
        points={polyline}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="2"
        strokeLinejoin="round"
      />

      {/* Area fill */}
      <polygon
        points={`${points[0].cx},${y(minVal)} ${polyline} ${points[points.length - 1].cx},${y(minVal)}`}
        fill="var(--accent)"
        fillOpacity="0.08"
      />

      {/* Data points */}
      {points.map((p, i) => (
        <g key={i}>
          <circle
            cx={p.cx}
            cy={p.cy}
            r="4"
            fill="var(--bg-secondary)"
            stroke="var(--accent)"
            strokeWidth="2"
          />
          <title>
            {formatTick(p.value)} {unit || ''} @ {new Date(p.time).toLocaleString()}
          </title>
        </g>
      ))}
    </svg>
  );
}
