import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { fetchInstruments, fetchSamples, fetchMeasurements } from '../api';
import StatusBadge from '../components/StatusBadge';

/* ── Helpers ──────────────────────────────────────── */

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatValue(val) {
  const n = parseFloat(val);
  return isNaN(n) ? val : n.toFixed(4);
}

/* ── Mini Sparkline (per-instrument) ──────────────── */

function MiniChart({ data, color = 'var(--accent)', width = 200, height = 60 }) {
  if (!data || data.length < 2) {
    return (
      <div className="meas-minichart-empty">
        {data?.length === 1 ? '1 data point' : 'No chart data'}
      </div>
    );
  }

  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = 4;
  const w = width - pad * 2;
  const h = height - pad * 2;

  const points = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * w;
    const y = pad + h - ((v - min) / range) * h;
    return `${x},${y}`;
  });

  const areaPoints = `${pad},${pad + h} ${points.join(' ')} ${pad + w},${pad + h}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: '100%', maxWidth: width, height: 'auto' }}
      className="meas-minichart-svg"
    >
      <polygon points={areaPoints} fill={color} fillOpacity="0.1" />
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Last point highlighted */}
      {values.length > 0 && (
        <circle
          cx={pad + w}
          cy={pad + h - ((values[values.length - 1] - min) / range) * h}
          r="3"
          fill={color}
        />
      )}
    </svg>
  );
}

/* ── Stat Pill ────────────────────────────────────── */

function StatPill({ label, value, color }) {
  return (
    <div className="meas-stat-pill">
      <span className="meas-stat-pill-value" style={color ? { color } : {}}>
        {value}
      </span>
      <span className="meas-stat-pill-label">{label}</span>
    </div>
  );
}

/* ── Parameter Tag ────────────────────────────────── */

function ParamTag({ name, count, isActive, onClick }) {
  return (
    <button
      className={`meas-param-tag ${isActive ? 'meas-param-tag--active' : ''}`}
      onClick={onClick}
    >
      {name}
      <span className="meas-param-tag-count">{count}</span>
    </button>
  );
}

/* ── Instrument Measurement Card ──────────────────── */

const CHART_COLORS = [
  'var(--accent)',
  'var(--status-online)',
  '#0ea5e9',
  '#f59e0b',
  '#6366f1',
  '#ec4899',
];

function InstrumentCard({ instrument, measurements, samples, colorIdx }) {
  const [selectedParam, setSelectedParam] = useState('');

  // Group measurements by parameter
  const paramGroups = useMemo(() => {
    const groups = {};
    measurements.forEach((m) => {
      if (!groups[m.parameter]) groups[m.parameter] = [];
      groups[m.parameter].push({
        value: parseFloat(m.value),
        unit: m.unit,
        time: m.measured_at,
        sample: m.sample,
        hash: m.data_hash,
      });
    });
    return groups;
  }, [measurements]);

  const paramNames = Object.keys(paramGroups);
  const activeParam = selectedParam || paramNames[0] || '';
  const activeData = paramGroups[activeParam] || [];
  const chartColor = CHART_COLORS[colorIdx % CHART_COLORS.length];

  // Stats
  const activeValues = activeData.map((d) => d.value).filter((v) => !isNaN(v));
  const lastValue = activeValues.length > 0 ? activeValues[activeValues.length - 1] : null;
  const avgValue =
    activeValues.length > 0
      ? activeValues.reduce((a, b) => a + b, 0) / activeValues.length
      : null;
  const minValue = activeValues.length > 0 ? Math.min(...activeValues) : null;
  const maxValue = activeValues.length > 0 ? Math.max(...activeValues) : null;
  const unit = activeData.length > 0 ? activeData[0].unit : '';

  // Related samples count
  const sampleIds = new Set(measurements.map((m) => m.sample));

  return (
    <div className="meas-inst-card">
      {/* Header */}
      <div className="meas-inst-header">
        <div className="meas-inst-info">
          <div className="meas-inst-name-row">
            <div
              className="meas-inst-color-bar"
              style={{ background: chartColor }}
            />
            <h3>{instrument.name}</h3>
            <StatusBadge status={instrument.status} />
          </div>
          <div className="meas-inst-meta">
            <span>{instrument.instrument_type}</span>
            <span className="meas-inst-sep">&bull;</span>
            <span>S/N: {instrument.serial_number}</span>
            <span className="meas-inst-sep">&bull;</span>
            <span>{sampleIds.size} sample{sampleIds.size !== 1 ? 's' : ''}</span>
          </div>
        </div>
        <div className="meas-inst-total">
          <span className="meas-inst-total-num">{measurements.length}</span>
          <span className="meas-inst-total-label">measurements</span>
        </div>
      </div>

      {/* Parameter Tabs */}
      {paramNames.length > 0 && (
        <div className="meas-param-bar">
          {paramNames.map((p) => (
            <ParamTag
              key={p}
              name={p}
              count={paramGroups[p].length}
              isActive={p === activeParam}
              onClick={() => setSelectedParam(p)}
            />
          ))}
        </div>
      )}

      {/* Chart + Stats Row */}
      {activeData.length > 0 && (
        <div className="meas-inst-body">
          <div className="meas-inst-chart-wrap">
            <MiniChart data={activeData} color={chartColor} width={280} height={80} />
          </div>
          <div className="meas-inst-stats">
            <StatPill
              label="Latest"
              value={lastValue !== null ? `${formatValue(lastValue)} ${unit}` : '—'}
              color={chartColor}
            />
            <StatPill
              label="Average"
              value={avgValue !== null ? `${formatValue(avgValue)} ${unit}` : '—'}
            />
            <StatPill
              label="Range"
              value={
                minValue !== null
                  ? `${formatValue(minValue)} — ${formatValue(maxValue)}`
                  : '—'
              }
            />
          </div>
        </div>
      )}

      {/* Recent measurements list */}
      <div className="meas-inst-recent">
        <div className="meas-inst-recent-header">Recent measurements</div>
        <div className="meas-inst-recent-list">
          {(activeData.length > 0 ? activeData : measurements)
            .slice(0, 5)
            .map((m, i) => (
              <div key={i} className="meas-inst-recent-row">
                <span className="meas-recent-param">
                  {m.parameter || activeParam}
                </span>
                <span className="meas-recent-value">
                  {formatValue(m.value)} {m.unit || unit}
                </span>
                <span className="meas-recent-time">{formatDate(m.time || m.measured_at)}</span>
                <span className="meas-recent-hash" title={m.hash || m.data_hash}>
                  {(m.hash || m.data_hash || '').slice(0, 8)}...
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}

/* ── Main Page ────────────────────────────────────── */

export default function MeasurementsGlobal() {
  const [instruments, setInstruments] = useState([]);
  const [measurements, setMeasurements] = useState([]);
  const [samples, setSamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 5000);
    return () => clearInterval(id);
  }, []);

  async function loadData() {
    try {
      const [inst, meas, samp] = await Promise.all([
        fetchInstruments(),
        fetchMeasurements(),
        fetchSamples(),
      ]);
      setInstruments(inst);
      setMeasurements(meas);
      setSamples(samp);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Group measurements by instrument
  const measByInstrument = useMemo(() => {
    const map = {};
    measurements.forEach((m) => {
      if (!map[m.instrument]) map[m.instrument] = [];
      map[m.instrument].push(m);
    });
    return map;
  }, [measurements]);

  // Summary stats
  const totalParams = useMemo(() => {
    return new Set(measurements.map((m) => m.parameter)).size;
  }, [measurements]);

  const instrumentsWithData = instruments.filter(
    (inst) => (measByInstrument[inst.id] || []).length > 0
  );
  const instrumentsWithoutData = instruments.filter(
    (inst) => (measByInstrument[inst.id] || []).length === 0
  );

  if (loading) {
    return (
      <div className="loading">
        <div className="dash-loader" />
        Loading measurements...
      </div>
    );
  }

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <h1>Measurements</h1>
        <p>
          All captured measurements grouped by instrument &mdash;{' '}
          {measurements.length} total across {instruments.length} instrument
          {instruments.length !== 1 ? 's' : ''}
        </p>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={loadData}>Retry</button>
        </div>
      )}

      {/* Summary bar */}
      <div className="meas-summary-bar">
        <div className="meas-summary-item">
          <span className="meas-summary-value">{measurements.length}</span>
          <span className="meas-summary-label">Total Measurements</span>
        </div>
        <div className="meas-summary-divider" />
        <div className="meas-summary-item">
          <span className="meas-summary-value">{instrumentsWithData.length}</span>
          <span className="meas-summary-label">Active Instruments</span>
        </div>
        <div className="meas-summary-divider" />
        <div className="meas-summary-item">
          <span className="meas-summary-value">{totalParams}</span>
          <span className="meas-summary-label">Parameters Tracked</span>
        </div>
        <div className="meas-summary-divider" />
        <div className="meas-summary-item">
          <span className="meas-summary-value">{samples.length}</span>
          <span className="meas-summary-label">Samples Linked</span>
        </div>
      </div>

      {/* Instrument cards */}
      <div className="meas-inst-grid">
        {instrumentsWithData.map((inst, idx) => (
          <InstrumentCard
            key={inst.id}
            instrument={inst}
            measurements={measByInstrument[inst.id] || []}
            samples={samples}
            colorIdx={idx}
          />
        ))}
      </div>

      {/* Instruments without data */}
      {instrumentsWithoutData.length > 0 && (
        <div className="meas-no-data-section">
          <h4>Instruments without measurements</h4>
          <div className="meas-no-data-list">
            {instrumentsWithoutData.map((inst) => (
              <div key={inst.id} className="meas-no-data-item">
                <StatusBadge status={inst.status} />
                <span>{inst.name}</span>
                <span className="meas-no-data-type">{inst.instrument_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {measurements.length === 0 && instruments.length === 0 && (
        <div className="parse-empty-state">
          <div className="parse-empty-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <p>No measurements recorded yet.</p>
          <p className="parse-empty-hint">
            Connect instruments and start capturing data.
          </p>
        </div>
      )}
    </div>
  );
}
