import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchSample, fetchMeasurements, fetchInstruments } from '../api';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import MeasurementChart from '../components/MeasurementChart';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Measurements() {
  const { sampleId } = useParams();
  const [sample, setSample] = useState(null);
  const [measurements, setMeasurements] = useState([]);
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedParam, setSelectedParam] = useState('');

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [sampleId]);

  async function load() {
    try {
      const [samp, meas, inst] = await Promise.all([
        fetchSample(sampleId),
        fetchMeasurements({ sample: sampleId }),
        fetchInstruments(),
      ]);
      setSample(samp);
      setMeasurements(meas);
      setInstruments(inst);
      setError(null);

      // Auto-select first parameter
      if (meas.length > 0 && !selectedParam) {
        setSelectedParam(meas[0].parameter);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const instrumentMap = {};
  instruments.forEach((i) => {
    instrumentMap[i.id] = i.name;
  });

  // Unique parameters
  const parameters = [...new Set(measurements.map((m) => m.parameter))];

  // Filter chart data by selected parameter
  const chartData = selectedParam
    ? measurements.filter((m) => m.parameter === selectedParam)
    : measurements;

  const chartUnit = chartData.length > 0 ? chartData[0].unit : '';

  const columns = [
    { key: 'parameter', label: 'Parameter' },
    {
      key: 'value',
      label: 'Value',
      render: (val) => {
        const num = parseFloat(val);
        return isNaN(num) ? val : num.toFixed(4);
      },
    },
    { key: 'unit', label: 'Unit' },
    {
      key: 'instrument',
      label: 'Instrument',
      render: (val) => instrumentMap[val] || `#${val}`,
    },
    {
      key: 'measured_at',
      label: 'Measured At',
      render: (val) => formatDate(val),
    },
    {
      key: 'data_hash',
      label: 'Integrity Hash',
      render: (val) => (
        <span className="signature-hash" title={val}>
          {val ? val.slice(0, 12) + '...' : '—'}
        </span>
      ),
    },
  ];

  if (loading) return <div className="loading">Loading measurements...</div>;

  return (
    <div>
      <Link to="/samples" className="back-link">
        &#8592; Back to Samples
      </Link>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={load}>Retry</button>
        </div>
      )}

      {sample && (
        <div className="detail-header">
          <div className="detail-header-row">
            <div className="detail-field">
              <span className="detail-field-label">Sample ID</span>
              <span className="detail-field-value">{sample.sample_id}</span>
            </div>
            <div className="detail-field">
              <span className="detail-field-label">Instrument</span>
              <span className="detail-field-value">
                {instrumentMap[sample.instrument] || `#${sample.instrument}`}
              </span>
            </div>
            <div className="detail-field">
              <span className="detail-field-label">Batch</span>
              <span className="detail-field-value">{sample.batch_number}</span>
            </div>
            <div className="detail-field">
              <span className="detail-field-label">Status</span>
              <span className="detail-field-value">
                <StatusBadge status={sample.status} />
              </span>
            </div>
            <div className="detail-field">
              <span className="detail-field-label">Created</span>
              <span className="detail-field-value">{formatDate(sample.created_at)}</span>
            </div>
          </div>
        </div>
      )}

      <div className="chart-section">
        <div className="chart-header">
          <h3>Measurements Over Time</h3>
          {parameters.length > 1 && (
            <select
              className="filter-select"
              value={selectedParam}
              onChange={(e) => setSelectedParam(e.target.value)}
            >
              {parameters.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          )}
        </div>
        <MeasurementChart measurements={chartData} unit={chartUnit} />
      </div>

      <div className="table-title" style={{ marginBottom: 0 }}>
        All Measurements
      </div>
      <DataTable
        columns={columns}
        rows={measurements}
        emptyMessage="No measurements recorded for this sample."
      />
    </div>
  );
}
