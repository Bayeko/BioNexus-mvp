import React from 'react';
import type { ConnectorInfo } from '../api';

interface ConnectorStatusProps {
  connectors: ConnectorInfo[];
  onEnable: (name: string) => void;
  onDisable: (name: string) => void;
}

export function ConnectorStatus({ connectors, onEnable, onDisable }: ConnectorStatusProps) {
  return (
    <div>
      <h2>Connectors</h2>

      <div className="grid-2">
        {connectors.map((c) => (
          <div key={c.name} className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span
                  className="connection-dot"
                  style={{
                    background: c.enabled && c.configured
                      ? 'var(--green)'
                      : c.enabled
                        ? 'var(--amber)'
                        : 'var(--text-muted)',
                  }}
                />
                <span className="card-title">{c.displayName}</span>
              </div>
              <span className="badge badge-muted">{c.toolCount} tools</span>
            </div>

            <div className="card-body">
              <p>{c.description}</p>
              {c.lastHealthCheck && (
                <p style={{ marginTop: 4, fontSize: 11 }}>
                  Health: {c.lastHealthCheck.ok ? 'OK' : c.lastHealthCheck.message}
                </p>
              )}
            </div>

            <div className="card-actions">
              {c.enabled ? (
                <button className="btn btn-sm btn-reject" onClick={() => onDisable(c.name)}>
                  Disable
                </button>
              ) : (
                <button className="btn btn-sm btn-approve" onClick={() => onEnable(c.name)}>
                  Enable
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
