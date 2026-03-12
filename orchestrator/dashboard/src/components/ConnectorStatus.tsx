import React from 'react';
import type { ConnectorInfo } from '../api';

interface ConnectorStatusProps {
  connectors: ConnectorInfo[];
  onEnable: (name: string) => void;
  onDisable: (name: string) => void;
  onReconnect?: (name: string) => void;
}

function ConnectorIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4z" /><path d="M14 17h6M17 14v6" />
    </svg>
  );
}

function statusClass(c: ConnectorInfo): string {
  if (c.enabled && c.configured) return 'ok';
  if (c.enabled) return 'warning';
  return 'off';
}

function statusLabel(c: ConnectorInfo): string {
  if (c.enabled && c.configured) return 'Connected';
  if (c.enabled) return 'Not configured';
  return 'Disabled';
}

export function ConnectorStatus({ connectors, onEnable, onDisable, onReconnect }: ConnectorStatusProps) {
  return (
    <div>
      <div className="page-header">
        <h2>Connectors</h2>
        <p>Manage integrations with external services</p>
      </div>

      {connectors.length === 0 ? (
        <div className="empty-state">
          <p>No connectors available</p>
          <p className="empty-subtitle">Connectors are registered on server startup</p>
        </div>
      ) : (
        <div className="grid-2">
          {connectors.map((c) => (
            <div key={c.name} className="card connector-card">
              <span className={`connector-status ${statusClass(c)}`} />

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
                <div className="connector-icon"><ConnectorIcon /></div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="card-title">{c.displayName}</div>
                  <div className="card-meta" style={{ marginTop: 2 }}>{statusLabel(c)}</div>
                </div>
                <span className="badge badge-muted">{c.toolCount} tools</span>
              </div>

              <div className="card-body">
                <p>{c.description}</p>
                {c.lastHealthCheck && (
                  <p style={{ marginTop: 6, fontSize: 11, color: c.lastHealthCheck.ok ? 'var(--green)' : 'var(--red)' }}>
                    {c.lastHealthCheck.ok ? 'Health check passed' : `Error: ${c.lastHealthCheck.message}`}
                  </p>
                )}
              </div>

              <div className="card-actions">
                {c.enabled ? (
                  <>
                    <button className="btn btn-sm btn-reject" onClick={() => onDisable(c.name)}>
                      Disable
                    </button>
                    {onReconnect && (
                      <button className="btn btn-sm btn-ghost" onClick={() => onReconnect(c.name)}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
                          <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
                        </svg>
                        Reconnect
                      </button>
                    )}
                  </>
                ) : (
                  <button className="btn btn-sm btn-approve" onClick={() => onEnable(c.name)}>
                    Enable
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
