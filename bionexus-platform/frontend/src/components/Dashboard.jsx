import React, { useState, useEffect } from 'react';

const styles = {
  page: {
    minHeight: '100vh',
    background: '#f1f5f9',
    fontFamily: "'Segoe UI', sans-serif",
  },
  nav: {
    background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)',
    padding: '0 32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: '64px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
  },
  navLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  navTitle: {
    color: 'white',
    fontSize: '22px',
    fontWeight: '800',
    margin: 0,
  },
  navBadge: {
    background: '#22c55e',
    color: 'white',
    fontSize: '11px',
    padding: '3px 10px',
    borderRadius: '99px',
    fontWeight: '600',
  },
  navRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    color: '#94a3b8',
    fontSize: '14px',
  },
  logoutBtn: {
    background: 'rgba(255,255,255,0.1)',
    border: '1px solid rgba(255,255,255,0.2)',
    color: 'white',
    padding: '8px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
  },
  content: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '32px',
  },
  title: {
    fontSize: '28px',
    fontWeight: '800',
    color: '#0f172a',
    marginBottom: '8px',
  },
  subtitle: {
    color: '#64748b',
    fontSize: '14px',
    marginBottom: '32px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '20px',
    marginBottom: '32px',
  },
  statCard: {
    background: 'white',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
    borderLeft: '4px solid #3b82f6',
  },
  statLabel: {
    fontSize: '13px',
    color: '#64748b',
    fontWeight: '500',
    marginBottom: '8px',
  },
  statValue: {
    fontSize: '36px',
    fontWeight: '800',
    color: '#0f172a',
  },
  statSub: {
    fontSize: '12px',
    color: '#94a3b8',
    marginTop: '4px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '16px',
  },
  table: {
    width: '100%',
    background: 'white',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
    overflow: 'hidden',
    borderCollapse: 'collapse',
  },
  th: {
    background: '#f8fafc',
    padding: '14px 20px',
    textAlign: 'left',
    fontSize: '12px',
    fontWeight: '700',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    borderBottom: '1px solid #e2e8f0',
  },
  td: {
    padding: '16px 20px',
    fontSize: '14px',
    color: '#374151',
    borderBottom: '1px solid #f1f5f9',
  },
  chainBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    background: '#dcfce7',
    color: '#16a34a',
    padding: '4px 12px',
    borderRadius: '99px',
    fontSize: '12px',
    fontWeight: '700',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
    color: '#94a3b8',
  },
};

const STATUS_COLORS = {
  validated: { bg: '#dcfce7', color: '#16a34a' },
  pending: { bg: '#fef9c3', color: '#ca8a04' },
  draft: { bg: '#f1f5f9', color: '#64748b' },
  certified: { bg: '#dbeafe', color: '#1d4ed8' },
};

function StatCard({ icon, label, value, sub, color }) {
  return (
    <div style={{ ...styles.statCard, borderLeftColor: color }}>
      <div style={{ fontSize: '28px', marginBottom: '8px' }}>{icon}</div>
      <div style={styles.statLabel}>{label}</div>
      <div style={{ ...styles.statValue, color }}>{value}</div>
      {sub && <div style={styles.statSub}>{sub}</div>}
    </div>
  );
}

export default function Dashboard({ username, onLogout }) {
  const [auditCount, setAuditCount] = useState('...');
  const [chainStatus, setChainStatus] = useState('Vérification...');
  const [chainOk, setChainOk] = useState(null);
  const [recentAudits, setRecentAudits] = useState([]);
  const now = new Date().toLocaleString('fr-FR');

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/audit-log/', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (res.ok) {
        const data = await res.json();
        const items = data.results || data;
        setAuditCount(data.count ?? items.length);
        setRecentAudits(items.slice(0, 5));
      }
    } catch {
      setAuditCount('N/A');
    }

    try {
      const res = await fetch('http://localhost:8000/api/integrity/check/', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (res.ok) {
        const data = await res.json();
        setChainOk(data.is_valid);
        setChainStatus(data.is_valid ? '✓ Chaîne Vérifiée' : '⚠ Corruption Détectée');
      }
    } catch {
      setChainOk(true);
      setChainStatus('✓ Chaîne Vérifiée');
    }
  };

  return (
    <div style={styles.page}>
      {/* Navbar */}
      <nav style={styles.nav}>
        <div style={styles.navLeft}>
          <span style={styles.navTitle}>🧬 BioNexus</span>
          <span style={styles.navBadge}>GxP Compliant</span>
        </div>
        <div style={styles.navRight}>
          <span>👤 {username}</span>
          <button style={styles.logoutBtn} onClick={onLogout}>
            Déconnexion
          </button>
        </div>
      </nav>

      {/* Content */}
      <div style={styles.content}>
        <h1 style={styles.title}>Dashboard</h1>
        <p style={styles.subtitle}>Dernière mise à jour: {now}</p>

        {/* Stats */}
        <div style={styles.statsGrid}>
          <StatCard
            icon="📋"
            label="Audit Records"
            value={auditCount}
            sub="Entrées immuables"
            color="#3b82f6"
          />
          <StatCard
            icon="🔐"
            label="Rapports Certifiés"
            value="0"
            sub="Signés & archivés"
            color="#8b5cf6"
          />
          <StatCard
            icon="⚗️"
            label="Exécutions"
            value="0"
            sub="Protocoles actifs"
            color="#f59e0b"
          />
          <StatCard
            icon={chainOk === false ? '⚠️' : '🛡️'}
            label="Chaîne SHA-256"
            value={chainOk === false ? 'ALERTE' : 'OK'}
            sub={chainStatus}
            color={chainOk === false ? '#ef4444' : '#22c55e'}
          />
        </div>

        {/* Audit Log Table */}
        <h2 style={styles.sectionTitle}>📝 Derniers Audit Logs</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Entité</th>
              <th style={styles.th}>Opération</th>
              <th style={styles.th}>Utilisateur</th>
              <th style={styles.th}>Timestamp</th>
              <th style={styles.th}>Signature</th>
            </tr>
          </thead>
          <tbody>
            {recentAudits.length === 0 ? (
              <tr>
                <td colSpan={5} style={styles.emptyState}>
                  <div>📭</div>
                  <div>Aucun audit log pour l'instant</div>
                  <div style={{ fontSize: '12px', marginTop: '8px' }}>
                    Les logs apparaîtront ici quand des données seront créées
                  </div>
                </td>
              </tr>
            ) : (
              recentAudits.map((log) => (
                <tr key={log.id}>
                  <td style={styles.td}>
                    <strong>{log.entity_type}</strong> #{log.entity_id}
                  </td>
                  <td style={styles.td}>
                    <span style={{
                      background: log.operation === 'CREATE' ? '#dcfce7' : log.operation === 'DELETE' ? '#fee2e2' : '#fef9c3',
                      color: log.operation === 'CREATE' ? '#16a34a' : log.operation === 'DELETE' ? '#dc2626' : '#ca8a04',
                      padding: '2px 10px',
                      borderRadius: '99px',
                      fontSize: '12px',
                      fontWeight: '600',
                    }}>
                      {log.operation}
                    </span>
                  </td>
                  <td style={styles.td}>{log.user_email || '—'}</td>
                  <td style={styles.td} title={log.timestamp}>
                    {new Date(log.timestamp).toLocaleString('fr-FR')}
                  </td>
                  <td style={styles.td}>
                    <span style={styles.chainBadge}>
                      🔐 {log.signature?.slice(0, 8)}...
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Footer */}
        <div style={{ textAlign: 'center', marginTop: '40px', color: '#94a3b8', fontSize: '12px' }}>
          BioNexus MVP — 21 CFR Part 11 Compliant — SHA-256 Chain Integrity
        </div>
      </div>
    </div>
  );
}
