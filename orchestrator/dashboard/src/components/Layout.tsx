import React from 'react';

export type Page = 'approvals' | 'workflows' | 'create' | 'connectors' | 'activity';

interface LayoutProps {
  currentPage: Page;
  onNavigate: (page: Page) => void;
  connected: boolean;
  pendingCount: number;
  children: React.ReactNode;
}

const NAV_ITEMS: { page: Page; label: string }[] = [
  { page: 'approvals', label: 'Approvals' },
  { page: 'workflows', label: 'Workflows' },
  { page: 'create', label: 'Create' },
  { page: 'connectors', label: 'Connectors' },
  { page: 'activity', label: 'Activity' },
];

function NavIcon({ page }: { page: Page }) {
  const props = { width: 18, height: 18, fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  switch (page) {
    case 'approvals':
      return <svg {...props} viewBox="0 0 24 24"><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" /></svg>;
    case 'workflows':
      return <svg {...props} viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></svg>;
    case 'create':
      return <svg {...props} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>;
    case 'connectors':
      return <svg {...props} viewBox="0 0 24 24"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4z" /><path d="M14 17h6M17 14v6" /></svg>;
    case 'activity':
      return <svg {...props} viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>;
  }
}

export function Layout({ currentPage, onNavigate, connected, pendingCount, children }: LayoutProps) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-row">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <rect width="24" height="24" rx="6" fill="var(--accent)" fillOpacity="0.15" />
              <path d="M12 6L17 9.5V16.5L12 20L7 16.5V9.5L12 6Z" stroke="var(--accent)" strokeWidth="1.5" fill="none" />
              <circle cx="12" cy="13" r="2.5" fill="var(--accent)" fillOpacity="0.6" />
            </svg>
            <h1>Bio<span>Nexus</span></h1>
          </div>
          <div className="sidebar-version">Orchestrator v0.1</div>
          <div className="sidebar-connection">
            <span className={`connection-dot ${connected ? 'connected' : 'disconnected'}`} />
            {connected ? 'Live' : 'Disconnected'}
          </div>
        </div>

        <nav>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.page}
              className={`nav-item ${currentPage === item.page ? 'active' : ''}`}
              onClick={() => onNavigate(item.page)}
            >
              <NavIcon page={item.page} />
              {item.label}
              {item.page === 'approvals' && pendingCount > 0 && (
                <span className="nav-badge">{pendingCount}</span>
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
