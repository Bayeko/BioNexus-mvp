import React, { useState, useEffect, useCallback } from 'react';
import { fetchAuditLogs } from '../api';
import DataTable from '../components/DataTable';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function ChangesCell({ changes }) {
  const [expanded, setExpanded] = useState(false);
  const json = JSON.stringify(changes, null, 2);
  const preview = JSON.stringify(changes);

  if (!changes || Object.keys(changes).length === 0) {
    return <span className="signature-hash">—</span>;
  }

  return (
    <div>
      <div
        className="changes-preview"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
        title="Click to expand"
      >
        {preview}
      </div>
      {expanded && <div className="changes-expanded">{json}</div>}
    </div>
  );
}

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [entityType, setEntityType] = useState('');
  const [operation, setOperation] = useState('');
  const [userEmail, setUserEmail] = useState('');

  const loadData = useCallback(async () => {
    try {
      const filters = {};
      if (entityType) filters.entity_type = entityType;
      if (operation) filters.operation = operation;
      if (userEmail) filters.user_email = userEmail;
      setLogs(await fetchAuditLogs(filters));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [entityType, operation, userEmail]);

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 5000);
    return () => clearInterval(id);
  }, [loadData]);

  const columns = [
    { key: 'id', label: 'ID' },
    {
      key: 'timestamp',
      label: 'Timestamp',
      render: (val) => formatDate(val),
    },
    { key: 'entity_type', label: 'Entity' },
    { key: 'entity_id', label: 'Entity ID' },
    {
      key: 'operation',
      label: 'Operation',
      render: (val) => <span className={`op-tag op-tag--${val}`}>{val}</span>,
    },
    {
      key: 'user_email',
      label: 'User',
      render: (val) => val || '—',
    },
    {
      key: 'changes',
      label: 'Changes',
      render: (val) => <ChangesCell changes={val} />,
    },
    {
      key: 'signature',
      label: 'Signature',
      render: (val) => (
        <span className="signature-hash" title={val}>
          {val ? val.slice(0, 12) + '...' : '—'}
        </span>
      ),
    },
  ];

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <h1>Audit Trail</h1>
        <p>Immutable, tamper-proof record of all data transactions &mdash; 21 CFR Part 11 compliant</p>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={loadData}>Retry</button>
        </div>
      )}

      <div className="filter-bar">
        <select
          className="filter-select"
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
        >
          <option value="">All Entities</option>
          <option value="Instrument">Instrument</option>
          <option value="Sample">Sample</option>
          <option value="Measurement">Measurement</option>
          <option value="Protocol">Protocol</option>
        </select>

        <select
          className="filter-select"
          value={operation}
          onChange={(e) => setOperation(e.target.value)}
        >
          <option value="">All Operations</option>
          <option value="CREATE">CREATE</option>
          <option value="UPDATE">UPDATE</option>
          <option value="DELETE">DELETE</option>
        </select>

        <input
          className="filter-input"
          type="text"
          placeholder="Filter by user email..."
          value={userEmail}
          onChange={(e) => setUserEmail(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="loading">Loading audit logs...</div>
      ) : (
        <DataTable
          columns={columns}
          rows={logs}
          emptyMessage="No audit records match the current filters."
        />
      )}
    </div>
  );
}
