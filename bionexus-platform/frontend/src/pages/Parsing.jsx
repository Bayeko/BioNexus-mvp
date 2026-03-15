import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchParsings,
  fetchParsing,
  uploadParsingFile,
  validateParsing,
  rejectParsing,
} from '../api';
import StatusBadge from '../components/StatusBadge';

function formatDate(iso) {
  if (!iso) return '\u2014';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function ConfidenceBadge({ value }) {
  const pct = Math.round(value * 100);
  const cls =
    pct >= 90
      ? 'confidence-high'
      : pct >= 70
        ? 'confidence-mid'
        : 'confidence-low';
  return <span className={`confidence-badge ${cls}`}>{pct}%</span>;
}

/* ---- Upload Zone ---- */

function UploadZone({ onUploaded, uploading, setUploading }) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);

  async function handleFiles(files) {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadParsingFile(files[0]);
      onUploaded(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  function onDragOver(e) {
    e.preventDefault();
    setDragOver(true);
  }

  function onDragLeave() {
    setDragOver(false);
  }

  function onFileSelect(e) {
    handleFiles(e.target.files);
    e.target.value = '';
  }

  return (
    <div
      className={`parse-upload-zone ${dragOver ? 'parse-upload-zone--active' : ''}`}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
    >
      <div className="parse-upload-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </div>
      <div className="parse-upload-text">
        {uploading ? (
          <span>Uploading & extracting...</span>
        ) : (
          <>
            <span>Drop instrument file here or </span>
            <label className="parse-upload-btn">
              browse
              <input
                type="file"
                style={{ display: 'none' }}
                onChange={onFileSelect}
                accept=".csv,.txt,.xlsx,.pdf,.json"
              />
            </label>
          </>
        )}
      </div>
      <div className="parse-upload-hint">
        CSV, TXT, XLSX, PDF, JSON &mdash; Automatic format recognition
      </div>
      {error && <div className="parse-upload-error">{error}</div>}
    </div>
  );
}

/* ---- Data Viewer (extracted / confirmed) ---- */

function DataViewer({ data, editable, onChange }) {
  if (!data) return <div className="parse-empty">No data</div>;

  const { equipment_records = [], sample_records = [], extraction_warnings = [] } = data;

  return (
    <div className="parse-data-viewer">
      {extraction_warnings.length > 0 && (
        <div className="parse-warnings">
          {extraction_warnings.map((w, i) => (
            <div key={i} className="parse-warning-item">
              <span className="parse-warning-icon">!</span>
              {w}
            </div>
          ))}
        </div>
      )}

      {equipment_records.length > 0 && (
        <div className="parse-section">
          <h4>Equipment Records ({equipment_records.length})</h4>
          <div className="parse-cards">
            {equipment_records.map((eq, i) => (
              <div key={i} className="parse-card">
                <div className="parse-card-header">
                  <span className="parse-card-id">{eq.equipment_id}</span>
                  <StatusBadge status={eq.status || 'active'} />
                </div>
                <div className="parse-card-field">
                  <label>Name</label>
                  {editable ? (
                    <input
                      value={eq.name || ''}
                      onChange={(e) => {
                        const updated = { ...data };
                        updated.equipment_records[i] = {
                          ...eq,
                          name: e.target.value,
                        };
                        onChange(updated);
                      }}
                    />
                  ) : (
                    <span>{eq.name}</span>
                  )}
                </div>
                <div className="parse-card-field">
                  <label>Type</label>
                  <span>{eq.type}</span>
                </div>
                <div className="parse-card-field">
                  <label>Location</label>
                  {editable ? (
                    <input
                      value={eq.location || ''}
                      onChange={(e) => {
                        const updated = { ...data };
                        updated.equipment_records[i] = {
                          ...eq,
                          location: e.target.value,
                        };
                        onChange(updated);
                      }}
                    />
                  ) : (
                    <span>{eq.location}</span>
                  )}
                </div>
                <div className="parse-card-field">
                  <label>Serial</label>
                  <span className="parse-mono">{eq.serial_number}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {sample_records.length > 0 && (
        <div className="parse-section">
          <h4>Sample Records ({sample_records.length})</h4>
          <div className="parse-cards">
            {sample_records.map((s, i) => (
              <div key={i} className="parse-card">
                <div className="parse-card-header">
                  <span className="parse-card-id">{s.sample_id}</span>
                  <span className="parse-card-type">{s.type}</span>
                </div>
                <div className="parse-card-field">
                  <label>Name</label>
                  {editable ? (
                    <input
                      value={s.name || ''}
                      onChange={(e) => {
                        const updated = { ...data };
                        updated.sample_records[i] = {
                          ...s,
                          name: e.target.value,
                        };
                        onChange(updated);
                      }}
                    />
                  ) : (
                    <span>{s.name}</span>
                  )}
                </div>
                <div className="parse-card-field">
                  <label>Collected By</label>
                  <span>{s.collected_by}</span>
                </div>
                <div className="parse-card-row">
                  <div className="parse-card-field">
                    <label>Temp</label>
                    <span>{s.storage_temperature}&deg;C</span>
                  </div>
                  <div className="parse-card-field">
                    <label>Quantity</label>
                    <span>
                      {s.quantity} {s.quantity_unit}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Detail / Review Panel ---- */

function ReviewPanel({ item, onClose, onAction }) {
  const [editData, setEditData] = useState(null);
  const [notes, setNotes] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [acting, setActing] = useState(false);
  const [showReject, setShowReject] = useState(false);

  const isPending = item.state === 'pending';
  const reviewData = editData || item.extracted_data;

  async function handleValidate() {
    setActing(true);
    try {
      await validateParsing(item.id, reviewData, notes);
      onAction();
    } catch (err) {
      alert('Validation error: ' + err.message);
    } finally {
      setActing(false);
    }
  }

  async function handleReject() {
    setActing(true);
    try {
      await rejectParsing(item.id, rejectReason);
      onAction();
    } catch (err) {
      alert('Rejection error: ' + err.message);
    } finally {
      setActing(false);
    }
  }

  return (
    <div className="parse-review-panel">
      <div className="parse-review-header">
        <div>
          <h3>{item.filename}</h3>
          <div className="parse-review-meta">
            <StatusBadge status={item.state} />
            <ConfidenceBadge value={item.extraction_confidence} />
            <span className="parse-review-model">{item.extraction_model}</span>
            <span className="parse-review-hash">{item.file_hash}</span>
          </div>
        </div>
        <button className="parse-close-btn" onClick={onClose}>
          &times;
        </button>
      </div>

      <div className="parse-review-body">
        <div className="parse-review-section">
          <div className="parse-review-section-header">
            <h4>
              {isPending
                ? 'Extracted Data (Review & Edit)'
                : item.state === 'validated'
                  ? 'Confirmed Data'
                  : 'Extracted Data (Rejected)'}
            </h4>
            {isPending && !editData && (
              <button
                className="btn-small"
                onClick={() =>
                  setEditData(JSON.parse(JSON.stringify(item.extracted_data)))
                }
              >
                Edit
              </button>
            )}
            {editData && (
              <button
                className="btn-small btn-small--muted"
                onClick={() => setEditData(null)}
              >
                Reset
              </button>
            )}
          </div>
          <DataViewer
            data={
              item.state === 'validated'
                ? item.confirmed_data || item.extracted_data
                : reviewData
            }
            editable={isPending && !!editData}
            onChange={setEditData}
          />
        </div>

        {isPending && (
          <div className="parse-review-actions">
            <div className="parse-review-notes">
              <label>Validation Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Optional notes for audit trail..."
                rows={2}
              />
            </div>

            {showReject ? (
              <div className="parse-reject-form">
                <input
                  type="text"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Reason for rejection..."
                  className="parse-reject-input"
                />
                <div className="parse-reject-btns">
                  <button
                    className="btn btn--danger"
                    onClick={handleReject}
                    disabled={acting || !rejectReason}
                  >
                    Confirm Reject
                  </button>
                  <button
                    className="btn btn--muted"
                    onClick={() => setShowReject(false)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="parse-action-btns">
                <button
                  className="btn btn--primary"
                  onClick={handleValidate}
                  disabled={acting}
                >
                  {acting ? 'Validating...' : 'Validate & Approve'}
                </button>
                <button
                  className="btn btn--danger-outline"
                  onClick={() => setShowReject(true)}
                  disabled={acting}
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        )}

        {item.state === 'validated' && item.validation_notes && (
          <div className="parse-validated-notes">
            <strong>Validation Notes:</strong> {item.validation_notes}
          </div>
        )}
        {item.state === 'rejected' && item.validation_notes && (
          <div className="parse-rejected-notes">
            <strong>Rejection Reason:</strong> {item.validation_notes}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---- Main Parsing Page ---- */

export default function Parsing() {
  const [parsings, setParsings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stateFilter, setStateFilter] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [uploading, setUploading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const filters = {};
      if (stateFilter) filters.state = stateFilter;
      const data = await fetchParsings(filters);
      setParsings(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [stateFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleUploaded(result) {
    if (result.duplicate) {
      setSelectedItem(null);
    }
    await loadData();
    if (result.id) {
      try {
        const full = await fetchParsing(result.id);
        setSelectedItem(full);
      } catch {
        // ignore
      }
    }
  }

  async function handleAction() {
    setSelectedItem(null);
    await loadData();
  }

  async function handleRowClick(item) {
    try {
      const full = await fetchParsing(item.id);
      setSelectedItem(full);
    } catch {
      setSelectedItem(item);
    }
  }

  const pendingCount = parsings.filter((p) => p.state === 'pending').length;

  return (
    <div className="parse-page">
      <div className="page-header">
        <h1>Smart Parser &amp; Validation</h1>
        <p>
          Upload instrument data files for automatic format recognition, review
          and validate before acceptance into the audit trail
        </p>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={loadData}>Retry</button>
        </div>
      )}

      {/* Upload zone */}
      <UploadZone
        onUploaded={handleUploaded}
        uploading={uploading}
        setUploading={setUploading}
      />

      {/* Pipeline summary */}
      <div className="parse-pipeline">
        <div className="parse-pipeline-step parse-pipeline-step--upload">
          <div className="parse-pipeline-num">1</div>
          <div className="parse-pipeline-label">Upload</div>
          <div className="parse-pipeline-desc">Instrument file</div>
        </div>
        <div className="parse-pipeline-arrow">&rarr;</div>
        <div className="parse-pipeline-step parse-pipeline-step--ai">
          <div className="parse-pipeline-num">2</div>
          <div className="parse-pipeline-label">Smart Extract</div>
          <div className="parse-pipeline-desc">Format recognition</div>
        </div>
        <div className="parse-pipeline-arrow">&rarr;</div>
        <div className="parse-pipeline-step parse-pipeline-step--review">
          <div className="parse-pipeline-num">3</div>
          <div className="parse-pipeline-label">Human Review</div>
          <div className="parse-pipeline-desc">
            {pendingCount > 0 ? `${pendingCount} pending` : 'All reviewed'}
          </div>
        </div>
        <div className="parse-pipeline-arrow">&rarr;</div>
        <div className="parse-pipeline-step parse-pipeline-step--audit">
          <div className="parse-pipeline-num">4</div>
          <div className="parse-pipeline-label">Audit Trail</div>
          <div className="parse-pipeline-desc">21 CFR Part 11</div>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <select
          className="filter-select"
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value)}
        >
          <option value="">All States</option>
          <option value="pending">Pending Review</option>
          <option value="validated">Validated</option>
          <option value="rejected">Rejected</option>
        </select>
        <button className="btn btn--small" onClick={loadData}>
          Refresh
        </button>
      </div>

      {/* Split layout: list + detail */}
      <div className="parse-layout">
        <div className="parse-list">
          {loading ? (
            <div className="loading">Loading parsings...</div>
          ) : parsings.length === 0 ? (
            <div className="parse-empty-state">
              <div className="parse-empty-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                  <polyline points="13 2 13 9 20 9" />
                </svg>
              </div>
              <p>No parsing records yet.</p>
              <p className="parse-empty-hint">
                Upload an instrument file above to start.
              </p>
            </div>
          ) : (
            parsings.map((item) => (
              <div
                key={item.id}
                className={`parse-list-item ${selectedItem?.id === item.id ? 'parse-list-item--selected' : ''}`}
                onClick={() => handleRowClick(item)}
              >
                <div className="parse-list-top">
                  <span className="parse-list-filename">{item.filename}</span>
                  <StatusBadge status={item.state} />
                </div>
                <div className="parse-list-bottom">
                  <ConfidenceBadge value={item.extraction_confidence} />
                  <span className="parse-list-date">
                    {formatDate(item.extracted_at)}
                  </span>
                  <span className="parse-list-hash">{item.file_hash}</span>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="parse-detail">
          {selectedItem ? (
            <ReviewPanel
              item={selectedItem}
              onClose={() => setSelectedItem(null)}
              onAction={handleAction}
            />
          ) : (
            <div className="parse-detail-empty">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <p>Select a parsing record to review</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

