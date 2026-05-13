/**
 * Veeva Vault QMS admin page.
 *
 * Mounted at /integrations/veeva. Three-tab layout:
 *
 *   Status         live integration mode + push counters
 *   OAuth          OAuth2 Authorization Code flow controls
 *   Push history   recent IntegrationPushLog rows
 *
 * Refined-industrial aesthetic per Labionexus brand canonical: no
 * SaaS-purple gradients, no marketing animations. Status pills use the
 * same color tokens as the rest of the app.
 *
 * The page consumes endpoints already shipped by PR #48
 * (status / log) plus the OAuth endpoints added in this PR
 * (oauth/status, oauth/authorize-url, oauth/callback).
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchVeevaAuthorizeUrl,
  fetchVeevaOAuthStatus,
  fetchVeevaPushLog,
  fetchVeevaStatus,
} from '../api';
import { useToast } from '../components/Toast';

const TABS = [
  { id: 'status', label: 'Status' },
  { id: 'oauth', label: 'OAuth2' },
  { id: 'history', label: 'Push history' },
];

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function StatusPill({ tone, label }) {
  // tone: 'ok' | 'warn' | 'error' | 'muted'
  const palette = {
    ok:    { bg: 'rgba(63, 185, 80, 0.10)', border: 'rgba(63, 185, 80, 0.4)',   fg: '#7ce38b', icon: '✓' },
    warn:  { bg: 'rgba(245, 158, 11, 0.10)', border: 'rgba(245, 158, 11, 0.5)', fg: '#fbbf24', icon: '!' },
    error: { bg: 'rgba(239, 68, 68, 0.10)', border: 'rgba(239, 68, 68, 0.45)',  fg: '#fca5a5', icon: '✕' },
    muted: { bg: 'rgba(120, 120, 130, 0.08)', border: 'rgba(120, 120, 130, 0.3)', fg: '#a0a0a8', icon: '○' },
  }[tone] || { bg: 'transparent', border: 'transparent', fg: 'inherit', icon: '' };

  return (
    <span
      className="veeva-status-pill"
      style={{ background: palette.bg, borderColor: palette.border, color: palette.fg }}
    >
      <span className="veeva-status-pill__icon" aria-hidden>{palette.icon}</span>
      {label}
    </span>
  );
}

function LoadingSkeleton({ rows = 3 }) {
  return (
    <div className="veeva-skeleton">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="veeva-skeleton__row" />
      ))}
    </div>
  );
}

function EmptyState({ icon, title, message }) {
  return (
    <div className="veeva-empty">
      <div className="veeva-empty__icon">{icon}</div>
      <h3 className="veeva-empty__title">{title}</h3>
      <p className="veeva-empty__message">{message}</p>
    </div>
  );
}

// ============================================================================
// Status tab
// ============================================================================

function modeTone(mode, enabled) {
  if (!enabled || mode === 'disabled') return 'muted';
  if (mode === 'mock') return 'warn';
  if (mode === 'sandbox') return 'warn';
  if (mode === 'prod') return 'ok';
  return 'muted';
}

function StatusTab() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchVeevaStatus('veeva');
      setStatus(data);
    } catch (err) {
      // network error: keep previous status, surface via empty state
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <LoadingSkeleton rows={3} />;
  if (!status) {
    return (
      <EmptyState
        icon={(
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="8" x2="12" y2="13" />
            <line x1="12" y1="16" x2="12" y2="16" />
          </svg>
        )}
        title="Cannot reach the status endpoint"
        message="Backend appears unreachable. Check that the Django server is running."
      />
    );
  }

  return (
    <div className="veeva-status-grid">
      <div className="veeva-stat-card">
        <span className="veeva-stat-card__label">Mode</span>
        <StatusPill tone={modeTone(status.mode, status.enabled)} label={status.label} />
        <span className="veeva-stat-card__sub">{status.mode}</span>
      </div>
      <div className="veeva-stat-card">
        <span className="veeva-stat-card__label">Base URL</span>
        <code className="veeva-stat-card__value">{status.base_url || '— not configured —'}</code>
      </div>
      <div className="veeva-stat-card">
        <span className="veeva-stat-card__label">Pushes total</span>
        <span className="veeva-stat-card__big">{status.counts.total}</span>
      </div>
      <div className="veeva-stat-card">
        <span className="veeva-stat-card__label">Success</span>
        <span className="veeva-stat-card__big veeva-stat-card__big--ok">{status.counts.success}</span>
      </div>
      <div className="veeva-stat-card">
        <span className="veeva-stat-card__label">Failed</span>
        <span className="veeva-stat-card__big veeva-stat-card__big--warn">{status.counts.failed}</span>
      </div>
      <div className="veeva-stat-card">
        <span className="veeva-stat-card__label">Dead letter</span>
        <span className="veeva-stat-card__big veeva-stat-card__big--err">{status.counts.dead_letter}</span>
      </div>
    </div>
  );
}

// ============================================================================
// OAuth tab
// ============================================================================

function OAuthTab() {
  const { toast } = useToast();
  const [oauthStatus, setOAuthStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchVeevaOAuthStatus();
      setOAuthStatus(data);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  async function handleStartOAuth() {
    setStarting(true);
    try {
      const { authorize_url } = await fetchVeevaAuthorizeUrl();
      if (!authorize_url) {
        toast.error('Backend did not return an authorize URL.');
        return;
      }
      window.location.assign(authorize_url);
    } catch (err) {
      toast.error(`OAuth start failed: ${err.message}`);
    } finally {
      setStarting(false);
    }
  }

  if (loading) return <LoadingSkeleton rows={2} />;

  if (!oauthStatus?.oauth2_enabled) {
    return (
      <EmptyState
        icon={(
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
        )}
        title="OAuth2 not enabled"
        message="Set VEEVA_AUTH_FLOW=oauth2 in the backend environment to enable the Authorization Code flow."
      />
    );
  }

  const hasToken = oauthStatus.has_active_token;

  return (
    <>
      <div className="veeva-oauth-row">
        <div>
          <h3 className="veeva-oauth-row__title">OAuth2 Authorization Code flow</h3>
          <p className="veeva-oauth-row__desc">
            Active when the operator authorizes Labionexus against the
            Vault tenant. Tokens are refreshed transparently before
            expiry.
          </p>
        </div>
        <StatusPill
          tone={hasToken ? 'ok' : 'muted'}
          label={hasToken ? 'Token active' : 'Not authorized'}
        />
      </div>

      {hasToken && (
        <div className="config-hint" style={{ marginBottom: 16 }}>
          Access token expires at <strong>{formatDate(oauthStatus.token_expires_at)}</strong>.
          The refresh token rotates a new access token automatically before that.
        </div>
      )}

      <div className="veeva-oauth-actions">
        <button
          className="btn btn--primary"
          onClick={handleStartOAuth}
          disabled={starting}
        >
          {starting ? 'Redirecting…' : (hasToken ? 'Re-authorize' : 'Connect via OAuth2')}
        </button>
        <button className="btn btn--muted" onClick={load}>Refresh status</button>
      </div>
    </>
  );
}

// ============================================================================
// History tab
// ============================================================================

function HistoryTab() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchVeevaPushLog({ vendor: 'veeva' })
      .then((list) => setJobs(Array.isArray(list) ? list : list.results || []))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSkeleton rows={4} />;
  if (jobs.length === 0) {
    return (
      <EmptyState
        icon={(
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 2" />
          </svg>
        )}
        title="No push history yet"
        message="Once VEEVA_INTEGRATION_ENABLED=true and a Measurement is captured, the signal pipeline records every push attempt here."
      />
    );
  }

  function statusTone(s) {
    if (s === 'success') return 'ok';
    if (s === 'failed') return 'warn';
    if (s === 'dead_letter') return 'error';
    return 'muted';
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Status</th>
          <th>Target</th>
          <th>Vault id</th>
          <th>Attempts</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {jobs.map((j) => (
          <tr key={j.id}>
            <td>{j.id}</td>
            <td><StatusPill tone={statusTone(j.status)} label={j.status} /></td>
            <td><code>{j.target_object_type}</code></td>
            <td>{j.target_object_id ? <code>{j.target_object_id}</code> : '—'}</td>
            <td>{j.attempts}</td>
            <td>{formatDate(j.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ============================================================================
// Main page
// ============================================================================

export default function VeevaConnect() {
  const [tab, setTab] = useState('status');

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <h1>Veeva Vault QMS</h1>
        <p>
          Configure how Labionexus pushes captured measurements into your
          Veeva Vault QMS tenant. Two authentication flows are supported:
          Session-ID (env-driven, default) and OAuth2 Authorization Code.
        </p>
      </div>

      <nav className="veeva-tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={`veeva-tab ${tab === t.id ? 'veeva-tab--active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="veeva-tab-panel">
        {tab === 'status' && <StatusTab />}
        {tab === 'oauth' && <OAuthTab />}
        {tab === 'history' && <HistoryTab />}
      </div>
    </div>
  );
}
