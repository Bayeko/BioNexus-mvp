import React, { useState } from 'react';
import StatusBadge from '../components/StatusBadge';

/* ── Integration Definitions ─────────────────────────────── */

const INTEGRATIONS = [
  {
    id: 'rest-api',
    name: 'REST API',
    category: 'API',
    description: 'Standard REST endpoints for real-time data exchange with any LIMS, ELN or middleware.',
    status: 'active',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M18 20V10M12 20V4M6 20v-6" />
      </svg>
    ),
    endpoints: [
      { method: 'GET', path: '/api/measurements/', desc: 'All measurements (filterable)' },
      { method: 'GET', path: '/api/samples/', desc: 'Sample list with status' },
      { method: 'GET', path: '/api/instruments/', desc: 'Connected instruments' },
      { method: 'GET', path: '/api/audit/', desc: 'Full audit trail (21 CFR Part 11)' },
    ],
    features: ['JSON format', 'Filterable queries', 'Paginated responses', 'SHA-256 data hashes included'],
    docUrl: '/api/',
  },
  {
    id: 'webhooks',
    name: 'Webhooks',
    category: 'Event-driven',
    description: 'Push notifications to your LIMS when data events occur — no polling required.',
    status: 'roadmap',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 00-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
    events: [
      { event: 'measurement.created', desc: 'New measurement received from instrument' },
      { event: 'sample.completed', desc: 'All measurements for a sample are done' },
      { event: 'sample.validated', desc: 'Parsed data validated by reviewer' },
      { event: 'instrument.status_changed', desc: 'Instrument goes online/offline/error' },
    ],
    features: ['HTTPS POST callbacks', 'Retry with exponential backoff', 'HMAC signature verification', 'Event filtering'],
  },
  {
    id: 'csv-export',
    name: 'CSV / PDF Export',
    category: 'File-based',
    description: 'Export data in standard formats for import into legacy LIMS systems (LabWare, STARLIMS).',
    status: 'roadmap',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
    formats: [
      { format: 'CSV', desc: 'Comma-separated values — universal import format' },
      { format: 'PDF', desc: 'Formatted reports with audit trail — for QA review' },
      { format: 'XML', desc: 'Structured data — compatible with Empower, ChromeLeon' },
      { format: 'JSON', desc: 'Native API format — for custom integrations' },
    ],
    features: ['Batch export', 'Date range filtering', 'Instrument grouping', 'Audit trail included'],
  },
  {
    id: 'empower',
    name: 'Waters Empower',
    category: 'LIMS / CDS',
    description: 'Direct integration with Waters Empower for HPLC/UPLC data exchange.',
    status: 'roadmap',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M8 12l2 2 4-4" />
      </svg>
    ),
    mapping: [
      { bionexus: 'Instrument', empower: 'System', direction: 'sync' },
      { bionexus: 'Sample ID', empower: 'Sample Set', direction: 'push' },
      { bionexus: 'Measurement', empower: 'Result', direction: 'push' },
      { bionexus: 'Audit Log', empower: 'Audit Trail', direction: 'push' },
    ],
    features: ['Empower Web API', 'Automatic field mapping', 'Bi-directional sync', 'GxP compliant transfer'],
  },
  {
    id: 'labware',
    name: 'LabWare LIMS',
    category: 'LIMS / CDS',
    description: 'Integration module for LabWare LIMS — exchange samples, results and audit data.',
    status: 'roadmap',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    ),
    features: ['REST + SOAP support', 'Sample lifecycle sync', 'Result auto-import', 'Configurable field mapping'],
  },
  {
    id: 'veeva',
    name: 'Veeva Vault QMS',
    category: 'QMS',
    description: 'Push Labionexus quality events and measurement context into Veeva Vault QMS for centralized batch release workflows.',
    status: 'roadmap',
    roadmapLabel: 'Q3 2026',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 8V7l-3-2-3 2v1l-2-1-3 2v1L8 9l-3 2v1L3 12v9h18v-9l-2-1V8z" />
        <path d="M9 22V12h6v10" />
      </svg>
    ),
    mapping: [
      { bionexus: 'Measurement', empower: 'quality_event__v', direction: 'push' },
      { bionexus: 'AuditLog signature', empower: 'audit_attachment__v', direction: 'push' },
      { bionexus: 'CertifiedReport PDF', empower: 'document__v', direction: 'push' },
      { bionexus: 'Operator ID', empower: 'reported_by__v', direction: 'push' },
      { bionexus: 'Lot number', empower: 'lot__v', direction: 'push' },
    ],
    features: [
      'OAuth2 against Veeva Vault sandbox + production',
      'VQL-backed object lookups',
      'Signed payloads (HMAC-SHA256) with retry + dead-letter',
      'Field mapping respects 21 CFR Part 11 §11.10 attribution',
    ],
  },
  {
    id: 'benchling',
    name: 'Benchling ELN',
    category: 'ELN',
    description: 'Push instrument data and results directly into Benchling notebooks.',
    status: 'roadmap',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
        <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
      </svg>
    ),
    features: ['Benchling API v2', 'Auto-attach results to entries', 'Structured data tables', 'Link instrument runs'],
  },
];

const STATUS_MAP = {
  active: { label: 'Active', className: 'online' },
  configured: { label: 'Configured', className: 'pending' },
  roadmap: { label: 'Roadmap', className: 'offline' },
};

/* ── Integration Card ─────────────────────────────────────── */

function IntegrationCard({ integration, onSelect, isSelected }) {
  const st = STATUS_MAP[integration.status] || STATUS_MAP.roadmap;
  // Integrations with a roadmap window publish a more specific label
  // (e.g. "Q3 2026") to differentiate "tracked roadmap" from "wishlist".
  const badgeLabel = integration.roadmapLabel
    ? `${st.label} · ${integration.roadmapLabel}`
    : st.label;

  return (
    <div
      className={`integ-card ${isSelected ? 'integ-card--selected' : ''}`}
      onClick={() => onSelect(integration.id)}
    >
      <div className="integ-card-header">
        <div className="integ-card-icon">{integration.icon}</div>
        <div className="integ-card-meta">
          <h3 className="integ-card-name">{integration.name}</h3>
          <span className="integ-card-category">{integration.category}</span>
        </div>
        <StatusBadge status={st.className} label={badgeLabel} />
      </div>
      <p className="integ-card-desc">{integration.description}</p>
      <div className="integ-card-features">
        {integration.features.slice(0, 3).map((f, i) => (
          <span key={i} className="integ-feature-tag">{f}</span>
        ))}
      </div>
    </div>
  );
}

/* ── Detail Panel ─────────────────────────────────────────── */

function DetailPanel({ integration }) {
  if (!integration) {
    return (
      <div className="integ-detail integ-detail--empty">
        <div className="integ-detail-placeholder">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="48" height="48">
            <path d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <p>Select an integration to view details</p>
        </div>
      </div>
    );
  }

  const st = STATUS_MAP[integration.status] || STATUS_MAP.roadmap;

  return (
    <div className="integ-detail">
      <div className="integ-detail-header">
        <div className="integ-detail-icon">{integration.icon}</div>
        <div>
          <h2>{integration.name}</h2>
          <span className="integ-card-category">{integration.category}</span>
        </div>
        <StatusBadge status={st.className} label={st.label} />
      </div>

      <p className="integ-detail-desc">{integration.description}</p>

      {/* Features */}
      <div className="integ-detail-section">
        <h4>Features</h4>
        <div className="integ-features-grid">
          {integration.features.map((f, i) => (
            <div key={i} className="integ-feature-item">
              <span className="integ-feature-check">&#10003;</span>
              {f}
            </div>
          ))}
        </div>
      </div>

      {/* API Endpoints */}
      {integration.endpoints && (
        <div className="integ-detail-section">
          <h4>Available Endpoints</h4>
          <div className="integ-endpoints">
            {integration.endpoints.map((ep, i) => (
              <div key={i} className="integ-endpoint-row">
                <span className={`integ-method integ-method--${ep.method.toLowerCase()}`}>{ep.method}</span>
                <code className="integ-path">{ep.path}</code>
                <span className="integ-endpoint-desc">{ep.desc}</span>
              </div>
            ))}
          </div>
          {integration.docUrl && (
            <a href={integration.docUrl} target="_blank" rel="noopener noreferrer" className="btn btn--primary" style={{ marginTop: 12, display: 'inline-block' }}>
              Open API Browser &rarr;
            </a>
          )}
        </div>
      )}

      {/* Webhook Events */}
      {integration.events && (
        <div className="integ-detail-section">
          <h4>Webhook Events</h4>
          <div className="integ-endpoints">
            {integration.events.map((ev, i) => (
              <div key={i} className="integ-endpoint-row">
                <code className="integ-path">{ev.event}</code>
                <span className="integ-endpoint-desc">{ev.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export Formats */}
      {integration.formats && (
        <div className="integ-detail-section">
          <h4>Export Formats</h4>
          <div className="integ-endpoints">
            {integration.formats.map((fmt, i) => (
              <div key={i} className="integ-endpoint-row">
                <span className="integ-method integ-method--get">{fmt.format}</span>
                <span className="integ-endpoint-desc">{fmt.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Field Mapping (Empower) */}
      {integration.mapping && (
        <div className="integ-detail-section">
          <h4>Field Mapping</h4>
          <table className="integ-mapping-table">
            <thead>
              <tr>
                <th>BioNexus</th>
                <th></th>
                <th>{integration.name}</th>
              </tr>
            </thead>
            <tbody>
              {integration.mapping.map((m, i) => (
                <tr key={i}>
                  <td><code>{m.bionexus}</code></td>
                  <td className="integ-mapping-arrow">
                    {m.direction === 'sync' ? '\u2194' : '\u2192'}
                  </td>
                  <td><code>{m.empower}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Roadmap notice */}
      {integration.status === 'roadmap' && (
        <div className="integ-roadmap-notice">
          <strong>Roadmap</strong> — This integration is planned for a future release.
          Contact us to discuss your specific requirements and timeline.
        </div>
      )}
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────── */

export default function Integrations() {
  const [selectedId, setSelectedId] = useState('rest-api');
  const selected = INTEGRATIONS.find(i => i.id === selectedId) || null;

  const activeCount = INTEGRATIONS.filter(i => i.status === 'active').length;
  const roadmapCount = INTEGRATIONS.filter(i => i.status === 'roadmap').length;

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <h1>Integrations</h1>
        <p>
          Connect BioNexus with your LIMS, ELN and middleware &mdash;
          {' '}<strong>{activeCount} active</strong>, {roadmapCount} on roadmap
        </p>
      </div>

      {/* Architecture diagram */}
      <div className="integ-arch-banner">
        <div className="integ-arch-flow">
          <div className="integ-arch-node integ-arch-node--instrument">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
              <path d="M12 2v6m0 8v6M2 12h6m8 0h6" /><circle cx="12" cy="12" r="3" />
            </svg>
            <span>Instruments</span>
          </div>
          <div className="integ-arch-arrow">&rarr;</div>
          <div className="integ-arch-node integ-arch-node--box">
            <strong>BioNexus Box</strong>
            <span>RS232 / USB</span>
          </div>
          <div className="integ-arch-arrow">&rarr;</div>
          <div className="integ-arch-node integ-arch-node--platform">
            <strong>BioNexus Platform</strong>
            <span>REST API + SHA-256</span>
          </div>
          <div className="integ-arch-arrow">&rarr;</div>
          <div className="integ-arch-node integ-arch-node--lims">
            <span>LIMS / ELN</span>
            <span style={{ fontSize: 11, opacity: 0.7 }}>Empower, LabWare, Benchling...</span>
          </div>
        </div>
      </div>

      {/* Split layout: cards + detail */}
      <div className="integ-layout">
        <div className="integ-cards-list">
          {INTEGRATIONS.map(integ => (
            <IntegrationCard
              key={integ.id}
              integration={integ}
              onSelect={setSelectedId}
              isSelected={selectedId === integ.id}
            />
          ))}
        </div>
        <DetailPanel integration={selected} />
      </div>
    </div>
  );
}
