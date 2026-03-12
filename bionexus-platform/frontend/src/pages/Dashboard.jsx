import React, { useState, useEffect, useMemo } from 'react';
import { fetchInstruments, fetchSamples, fetchMeasurements, fetchAuditLogs } from '../api';
import { Link } from 'react-router-dom';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';

/* ── Helpers ─────────────────────────────────────────────── */

function formatDate(iso) {
  if (!iso) return '\u2014';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function relativeTime(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/* ── SVG Sparkline (pure, no deps) ───────────────────────── */

function Sparkline({ data, color = 'var(--accent)', width = 120, height = 32 }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 2;
  const w = width - pad * 2;
  const h = height - pad * 2;

  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * w;
    const y = pad + h - ((v - min) / range) * h;
    return `${x},${y}`;
  });

  const areaPoints = `${pad + 0},${pad + h} ${points.join(' ')} ${pad + w},${pad + h}`;

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <polygon points={areaPoints} fill={color} fillOpacity="0.1" />
      <polyline points={points.join(' ')} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

/* ── Stat Card with icon + sparkline ────────────────────── */

function StatCard({ icon, label, value, sub, sparkData, sparkColor, accentClass }) {
  return (
    <div className="dash-stat-card">
      <div className="dash-stat-top">
        <div className={`dash-stat-icon ${accentClass || ''}`}>{icon}</div>
        <div className="dash-stat-spark">
          <Sparkline data={sparkData} color={sparkColor} />
        </div>
      </div>
      <div className="dash-stat-value">{value}</div>
      <div className="dash-stat-label">{label}</div>
      <div className="dash-stat-sub">{sub}</div>
    </div>
  );
}

/* ── Instrument Status Ring (donut) ──────────────────────── */

function StatusRing({ online, offline, error: errCount, total }) {
  if (total === 0) return <div className="dash-ring-empty">No instruments</div>;
  const r = 40, cx = 50, cy = 50, stroke = 8;
  const circ = 2 * Math.PI * r;
  const segments = [
    { count: online, color: 'var(--status-online)' },
    { count: errCount, color: 'var(--status-error)' },
    { count: offline, color: 'var(--status-offline)' },
  ];
  let offset = 0;

  return (
    <div className="dash-ring-wrap">
      <svg viewBox="0 0 100 100" className="dash-ring-svg">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
        {segments.map((seg, i) => {
          if (seg.count === 0) return null;
          const len = (seg.count / total) * circ;
          const el = (
            <circle
              key={i}
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth={stroke}
              strokeDasharray={`${len} ${circ - len}`}
              strokeDashoffset={-offset}
              strokeLinecap="round"
              transform={`rotate(-90 ${cx} ${cy})`}
            />
          );
          offset += len;
          return el;
        })}
        <text x={cx} y={cy - 4} textAnchor="middle" fill="var(--text-primary)" fontSize="18" fontWeight="700">{total}</text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill="var(--text-muted)" fontSize="9">instruments</text>
      </svg>
      <div className="dash-ring-legend">
        <span className="dash-ring-leg-item"><span className="dash-ring-dot" style={{ background: 'var(--status-online)' }} />{online} online</span>
        {errCount > 0 && <span className="dash-ring-leg-item"><span className="dash-ring-dot" style={{ background: 'var(--status-error)' }} />{errCount} error</span>}
        {offline > 0 && <span className="dash-ring-leg-item"><span className="dash-ring-dot" style={{ background: 'var(--status-offline)' }} />{offline} offline</span>}
      </div>
    </div>
  );
}

/* ── System Health Bar ───────────────────────────────────── */

function HealthBanner({ instruments }) {
  if (instruments.length === 0) return null;
  const hasError = instruments.some(i => i.status === 'error');
  const allOnline = instruments.every(i => i.status === 'online');

  let level, label, desc;
  if (hasError) {
    level = 'error';
    label = 'Alert';
    desc = `${instruments.filter(i => i.status === 'error').length} instrument(s) in error state`;
  } else if (allOnline) {
    level = 'ok';
    label = 'All Systems Normal';
    desc = `${instruments.length} instruments operating normally`;
  } else {
    level = 'warn';
    label = 'Degraded';
    const offCount = instruments.filter(i => i.status === 'offline').length;
    desc = `${offCount} instrument(s) offline`;
  }

  return (
    <div className={`dash-health dash-health--${level}`}>
      <div className="dash-health-dot" />
      <div className="dash-health-text">
        <strong>{label}</strong>
        <span>{desc}</span>
      </div>
    </div>
  );
}

/* ── Instrument List (compact) ───────────────────────────── */

function InstrumentList({ instruments }) {
  if (instruments.length === 0) return <div className="dash-empty-small">No instruments registered</div>;

  return (
    <div className="dash-inst-list">
      {instruments.slice(0, 6).map(inst => (
        <div key={inst.id} className="dash-inst-row">
          <div className="dash-inst-status-dot" style={{
            background: inst.status === 'online' ? 'var(--status-online)'
              : inst.status === 'error' ? 'var(--status-error)'
              : 'var(--status-offline)',
          }} />
          <div className="dash-inst-info">
            <span className="dash-inst-name">{inst.name}</span>
            <span className="dash-inst-type">{inst.instrument_type}</span>
          </div>
          <StatusBadge status={inst.status} />
        </div>
      ))}
      {instruments.length > 6 && (
        <Link to="/instruments" className="dash-inst-more">
          View all {instruments.length} instruments &rarr;
        </Link>
      )}
    </div>
  );
}

/* ── Activity Feed ───────────────────────────────────────── */

function ActivityFeed({ auditLogs, instruments }) {
  const instMap = useMemo(() => {
    const m = {};
    instruments.forEach(i => { m[i.id] = i.name; });
    return m;
  }, [instruments]);

  if (!auditLogs || auditLogs.length === 0) {
    return <div className="dash-empty-small">No recent activity</div>;
  }

  const opIcons = {
    CREATE: '+',
    UPDATE: '\u270E',
    DELETE: '\u2715',
  };
  const opColors = {
    CREATE: 'var(--status-online)',
    UPDATE: 'var(--accent)',
    DELETE: 'var(--status-error)',
  };

  return (
    <div className="dash-activity-list">
      {auditLogs.slice(0, 8).map((log, i) => (
        <div key={log.id || i} className="dash-activity-item">
          <div className="dash-activity-icon" style={{ color: opColors[log.operation] || 'var(--text-muted)' }}>
            {opIcons[log.operation] || '\u2022'}
          </div>
          <div className="dash-activity-body">
            <span className="dash-activity-text">
              <strong style={{ color: opColors[log.operation] }}>{log.operation}</strong>{' '}
              {log.entity_type}
              {log.entity_id ? ` #${log.entity_id}` : ''}
            </span>
            <span className="dash-activity-time">{relativeTime(log.timestamp)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Main Dashboard ──────────────────────────────────────── */

export default function Dashboard() {
  const [instruments, setInstruments] = useState([]);
  const [samples, setSamples] = useState([]);
  const [measurements, setMeasurements] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 5000);
    return () => clearInterval(id);
  }, []);

  async function loadData() {
    try {
      const [inst, samp, meas, audit] = await Promise.all([
        fetchInstruments(),
        fetchSamples(),
        fetchMeasurements(),
        fetchAuditLogs(),
      ]);
      setInstruments(inst);
      setSamples(samp);
      setMeasurements(meas);
      setAuditLogs(audit);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  /* Derived stats */
  const onlineCount = instruments.filter(i => i.status === 'online').length;
  const offlineCount = instruments.filter(i => i.status === 'offline').length;
  const errorCount = instruments.filter(i => i.status === 'error').length;
  const activeSamples = samples.filter(s => s.status === 'pending' || s.status === 'in_progress').length;
  const completedSamples = samples.filter(s => s.status === 'completed').length;

  /* Sparkline data: last 20 measurement values */
  const measurementSparkline = useMemo(() => {
    return measurements.slice(0, 20).map(m => parseFloat(m.value)).filter(v => !isNaN(v)).reverse();
  }, [measurements]);

  /* Sparkline: samples by day (last 7 buckets) */
  const sampleSparkline = useMemo(() => {
    if (samples.length === 0) return [];
    const now = Date.now();
    const buckets = Array(7).fill(0);
    samples.forEach(s => {
      const age = Math.floor((now - new Date(s.created_at).getTime()) / 86400000);
      if (age >= 0 && age < 7) buckets[6 - age]++;
    });
    return buckets;
  }, [samples]);

  /* Recent measurements for table */
  const recentMeasurements = measurements.slice(0, 8);

  const measurementColumns = [
    { key: 'parameter', label: 'Parameter' },
    {
      key: 'value', label: 'Value',
      render: val => { const n = parseFloat(val); return isNaN(n) ? val : n.toFixed(4); },
    },
    { key: 'unit', label: 'Unit' },
    { key: 'measured_at', label: 'Time', render: val => formatDate(val) },
  ];

  if (loading) {
    return (
      <div className="loading">
        <div className="dash-loader" />
        Loading dashboard...
      </div>
    );
  }

  return (
    <div className="dash-page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Laboratory overview and real-time system status</p>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={loadData}>Retry</button>
        </div>
      )}

      {/* Health Banner */}
      <HealthBanner instruments={instruments} />

      {/* Stat Cards */}
      <div className="dash-stats-grid">
        <StatCard
          icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v6m0 8v6M2 12h6m8 0h6" /><circle cx="12" cy="12" r="3" /></svg>}
          label="Instruments"
          value={instruments.length}
          sub={`${onlineCount} online`}
          sparkData={[onlineCount, instruments.length]}
          sparkColor="var(--accent)"
          accentClass="dash-stat-icon--blue"
        />
        <StatCard
          icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 3h6v7l3 8H6l3-8V3z" /><path d="M8 3h8" /></svg>}
          label="Active Samples"
          value={activeSamples}
          sub={`${completedSamples} completed \u00B7 ${samples.length} total`}
          sparkData={sampleSparkline}
          sparkColor="var(--status-pending)"
          accentClass="dash-stat-icon--amber"
        />
        <StatCard
          icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>}
          label="Measurements"
          value={measurements.length}
          sub="total recorded"
          sparkData={measurementSparkline}
          sparkColor="var(--status-online)"
          accentClass="dash-stat-icon--green"
        />
        <StatCard
          icon={<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>}
          label="Audit Events"
          value={auditLogs.length}
          sub="21 CFR Part 11"
          sparkData={[]}
          sparkColor="var(--accent)"
          accentClass="dash-stat-icon--purple"
        />
      </div>

      {/* Two-column layout: Instruments + Activity */}
      <div className="dash-panels">
        {/* Left: Instrument Status */}
        <div className="dash-panel">
          <div className="dash-panel-header">
            <h3>Instrument Status</h3>
            <Link to="/instruments" className="dash-panel-link">View all &rarr;</Link>
          </div>
          <div className="dash-panel-body dash-panel-body--split">
            <StatusRing online={onlineCount} offline={offlineCount} error={errorCount} total={instruments.length} />
            <InstrumentList instruments={instruments} />
          </div>
        </div>

        {/* Right: Recent Activity */}
        <div className="dash-panel">
          <div className="dash-panel-header">
            <h3>Recent Activity</h3>
            <Link to="/audit" className="dash-panel-link">Audit log &rarr;</Link>
          </div>
          <div className="dash-panel-body">
            <ActivityFeed auditLogs={auditLogs} instruments={instruments} />
          </div>
        </div>
      </div>

      {/* Recent Measurements Table */}
      <div className="dash-panel" style={{ marginTop: 0 }}>
        <div className="dash-panel-header">
          <h3>Recent Measurements</h3>
          <Link to="/samples" className="dash-panel-link">All samples &rarr;</Link>
        </div>
        <DataTable
          columns={measurementColumns}
          rows={recentMeasurements}
          emptyMessage="No measurements recorded yet."
        />
      </div>
    </div>
  );
}
