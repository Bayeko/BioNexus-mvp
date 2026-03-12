import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchSamples, fetchInstruments } from '../api';
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

export default function Samples() {
  const navigate = useNavigate();
  const [samples, setSamples] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [statusFilter, setStatusFilter] = useState('');
  const [instrumentFilter, setInstrumentFilter] = useState('');
  const [batchFilter, setBatchFilter] = useState('');

  const instrumentMap = {};
  instruments.forEach((inst) => {
    instrumentMap[inst.id] = inst.name;
  });

  const loadData = useCallback(async () => {
    try {
      const filters = {};
      if (statusFilter) filters.status = statusFilter;
      if (instrumentFilter) filters.instrument = instrumentFilter;
      if (batchFilter) filters.batch_number = batchFilter;

      const [samp, inst] = await Promise.all([
        fetchSamples(filters),
        fetchInstruments(),
      ]);
      setSamples(samp);
      setInstruments(inst);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, instrumentFilter, batchFilter]);

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 5000);
    return () => clearInterval(id);
  }, [loadData]);

  const columns = [
    { key: 'sample_id', label: 'Sample ID' },
    {
      key: 'instrument',
      label: 'Instrument',
      render: (val) => instrumentMap[val] || `#${val}`,
    },
    { key: 'batch_number', label: 'Batch' },
    {
      key: 'status',
      label: 'Status',
      render: (val) => <StatusBadge status={val} />,
    },
    { key: 'created_by', label: 'Created By' },
    {
      key: 'created_at',
      label: 'Created',
      render: (val) => formatDate(val),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Sample Tracking</h1>
        <p>Track samples through the laboratory workflow</p>
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
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>

        <select
          className="filter-select"
          value={instrumentFilter}
          onChange={(e) => setInstrumentFilter(e.target.value)}
        >
          <option value="">All Instruments</option>
          {instruments.map((inst) => (
            <option key={inst.id} value={inst.id}>
              {inst.name}
            </option>
          ))}
        </select>

        <input
          className="filter-input"
          type="text"
          placeholder="Batch number..."
          value={batchFilter}
          onChange={(e) => setBatchFilter(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="loading">Loading samples...</div>
      ) : (
        <DataTable
          columns={columns}
          rows={samples}
          onRowClick={(row) => navigate(`/samples/${row.id}/measurements`)}
          emptyMessage="No samples match the current filters."
        />
      )}
    </div>
  );
}
