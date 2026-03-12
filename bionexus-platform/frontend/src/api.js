/**
 * BioNexus API client.
 * Uses relative URLs ??? Vite dev proxy forwards /api to Django at localhost:8000.
 */

async function request(path) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function buildQS(filters) {
  const params = new URLSearchParams();
  for (const [key, val] of Object.entries(filters)) {
    if (val) params.set(key, val);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

// --- Instruments ---

export function fetchInstruments() {
  return request('/api/instruments/');
}

// --- Samples ---

export function fetchSamples(filters = {}) {
  const mapped = {};
  if (filters.instrument) mapped.instrument = filters.instrument;
  if (filters.status) mapped.status = filters.status;
  if (filters.batch_number) mapped.batch_number = filters.batch_number;
  if (filters.date) mapped['created_at__date'] = filters.date;
  return request(`/api/samples/${buildQS(mapped)}`);
}

export function fetchSample(id) {
  return request(`/api/samples/${id}/`);
}

// --- Measurements ---

export function fetchMeasurements(filters = {}) {
  const mapped = {};
  if (filters.sample) mapped.sample = filters.sample;
  if (filters.instrument) mapped.instrument = filters.instrument;
  if (filters.parameter) mapped.parameter = filters.parameter;
  return request(`/api/measurements/${buildQS(mapped)}`);
}

// --- Audit ---

export function fetchAuditLogs(filters = {}) {
  const mapped = {};
  if (filters.entity_type) mapped.entity_type = filters.entity_type;
  if (filters.entity_id) mapped.entity_id = filters.entity_id;
  if (filters.operation) mapped.operation = filters.operation;
  if (filters.user_email) mapped.user_email = filters.user_email;
  return request(`/api/audit/${buildQS(mapped)}`);
}

// --- AI Parsing ---

export function fetchParsings(filters = {}) {
  const mapped = {};
  if (filters.state) mapped.state = filters.state;
  return request(`/api/parsing/${buildQS(mapped)}`);
}

export function fetchParsing(id) {
  return request(`/api/parsing/${id}/`);
}

export async function uploadParsingFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch('/api/parsing/upload/', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload failed ${res.status}: ${text}`);
  }
  return res.json();
}

export async function validateParsing(id, confirmedData, notes) {
  const res = await fetch(`/api/parsing/${id}/validate/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      confirmed_data: confirmedData,
      validation_notes: notes || '',
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Validation failed ${res.status}: ${text}`);
  }
  return res.json();
}

export async function rejectParsing(id, reason) {
  const res = await fetch(`/api/parsing/${id}/reject/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: reason || 'Rejected by reviewer' }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Rejection failed ${res.status}: ${text}`);
  }
  return res.json();
}

