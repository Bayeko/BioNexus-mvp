import React, { useState, useEffect } from 'react';
import { fetchInstruments } from '../api';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

const COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'instrument_type', label: 'Type' },
  { key: 'serial_number', label: 'Serial Number' },
  { key: 'connection_type', label: 'Connection' },
  {
    key: 'status',
    label: 'Status',
    render: (val) => <StatusBadge status={val} />,
  },
  {
    key: 'updated_at',
    label: 'Last Updated',
    render: (val) => formatDate(val),
  },
];

export default function Instruments() {
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  async function load() {
    try {
      setInstruments(await fetchInstruments());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="loading">Loading instruments...</div>;

  return (
    <div>
      <div className="page-header">
        <h1>Instruments</h1>
        <p>Laboratory instruments connected via BioNexus Box</p>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={load}>Retry</button>
        </div>
      )}

      <DataTable
        columns={COLUMNS}
        rows={instruments}
        emptyMessage="No instruments registered yet."
      />
    </div>
  );
}
