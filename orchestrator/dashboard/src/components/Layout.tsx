import React from 'react';

export type Page = 'approvals' | 'workflows' | 'create' | 'connectors' | 'activity';

interface LayoutProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  connected: boolean;
  pendingCount: number;
  children: React.ReactNode;
}

const NAV_ITEMS: { page: Page; label: string; icon: string }[] = [
  { page: 'approvals', label: 'Approvals', icon: '[ ]' },
  { page: 'workflows', label: 'Workflows', icon: '{~}' },
  { page: 'create', label: 'Create', icon: '[+]' },
  { page: 'connectors', label: 'Connectors', icon: '<->' },
  { page: 'activity', label: 'Activity', icon: '...' },
];

export function Layout({ currentPage, onNavigate, connected, pendingCount, children }: LayoutProps) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>BioNexus</h1>
          <span>Orchestrator v0.1</span>
          <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span className={`connection-dot ${connected ? 'connected' : 'disconnected'}`} />
            <span style={{ color: 'var(--text-muted)' }}>
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        <nav>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.page}
              className={`nav-item ${currentPage === item.page ? 'active' : ''}`}
              onClick={() => onNavigate(item.page)}
            >
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, width: 28 }}>
                {item.icon}
              </span>
              {item.label}
              {item.page === 'approvals' && pendingCount > 0 && (
                <span className="badge badge-amber" style={{ marginLeft: 'auto' }}>
                  {pendingCount}
                </span>
              )}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main">
        {children}
      </main>
    </div>
  );
}
