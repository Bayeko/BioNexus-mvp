import React, { useState, useEffect } from 'react';
import { fetchInstruments, createInstrument } from '../api';
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

const INSTRUMENT_TYPES = [
  'HPLC',
  'spectrophotometer',
  'pcr_machine',
  'ph_meter',
  'balance',
  'plate_reader',
];

const CONNECTION_TYPES = ['RS232', 'USB', 'Ethernet', 'WiFi'];

const EMPTY_FORM = {
  name: '',
  instrument_type: '',
  serial_number: '',
  connection_type: 'USB',
  location: '',
};

export default function Instruments() {
  const [instruments, setInstruments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

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

  function openModal() {
    setForm(EMPTY_FORM);
    setFormError(null);
    setShowModal(true);
  }

  function closeModal() {
    setShowModal(false);
    setFormError(null);
  }

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.name || !form.instrument_type || !form.serial_number) {
      setFormError('Name, type, and serial number are required.');
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await createInstrument(form);
      setShowModal(false);
      await load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="loading">Loading instruments...</div>;

  return (
    <div className="page-wrapper">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Connected Instruments</h1>
          <p>All laboratory analyzers connected via BioNexus Box &mdash; real-time status monitoring</p>
        </div>
        <button className="btn btn--primary" onClick={openModal}>+ Register Instrument</button>
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

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Register Instrument</h2>
              <button className="modal-close" onClick={closeModal}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {formError && <div className="form-error">{formError}</div>}

                <label className="form-label">
                  Name *
                  <input
                    className="form-input"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    placeholder="e.g. Agilent 1260 Infinity II"
                  />
                </label>

                <label className="form-label">
                  Type *
                  <select className="form-input" name="instrument_type" value={form.instrument_type} onChange={handleChange}>
                    <option value="">Select type...</option>
                    {INSTRUMENT_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </label>

                <label className="form-label">
                  Serial Number *
                  <input
                    className="form-input"
                    name="serial_number"
                    value={form.serial_number}
                    onChange={handleChange}
                    placeholder="e.g. DEABC12345"
                  />
                </label>

                <label className="form-label">
                  Connection Type
                  <select className="form-input" name="connection_type" value={form.connection_type} onChange={handleChange}>
                    {CONNECTION_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </label>

                <label className="form-label">
                  Location
                  <input
                    className="form-input"
                    name="location"
                    value={form.location}
                    onChange={handleChange}
                    placeholder="e.g. QC Lab - Building A"
                  />
                </label>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn--muted" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={submitting}>
                  {submitting ? 'Registering...' : 'Register'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
