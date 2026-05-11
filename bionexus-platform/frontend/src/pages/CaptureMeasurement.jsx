/**
 * Capture Measurement page.
 *
 * Operator-facing form that creates a Measurement + MeasurementContext
 * in a single API call. The set of required metadata fields is driven
 * dynamically by the selected instrument's InstrumentConfig.
 *
 * Flow:
 *   1. Operator picks an instrument (dropdown).
 *   2. We fetch /api/instruments/{id}/config/ and render the required
 *      metadata fields with red asterisks.
 *   3. Operator fills in value, unit, method, lot, sample ID.
 *   4. POST /api/measurements/ — server validates context against config.
 *   5. 400 errors from the server are mapped back to inline field errors.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  createMeasurement,
  fetchInstrumentConfig,
  fetchInstruments,
  fetchSamples,
} from '../api';

// Threshold UI styling per verdict (mirror of theme.css banner classes).
const VERDICT_BANNER = {
  log: null, // silent
  alert: {
    className: 'threshold-banner threshold-banner--alert',
    headline: 'Threshold alert',
    body:
      'This value is outside the configured specification range. ' +
      'The reading will still be captured and flagged in the audit trail.',
  },
  block: {
    className: 'threshold-banner threshold-banner--block',
    headline: 'Threshold block',
    body:
      'This value violates a blocking threshold. The reading cannot be ' +
      'submitted without supervisor authorization.',
  },
};

// Ordered catalogue of context fields the form knows how to render.
// Required flag is derived dynamically from the instrument's config.
const CONTEXT_FIELDS = [
  { key: 'operator', label: 'Operator ID', placeholder: 'OP-042' },
  { key: 'lot_number', label: 'Lot / Batch Number', placeholder: 'LOT-2026-04' },
  { key: 'method', label: 'Analytical Method', placeholder: 'USP <621>' },
  { key: 'sample_id', label: 'External Sample ID', placeholder: 'QC-SMP-100' },
  { key: 'notes', label: 'Notes', placeholder: 'Optional remarks', textarea: true },
];

const EMPTY_FORM = {
  sample: '',
  instrument: '',
  parameter: '',
  value: '',
  unit: '',
  measured_at: new Date().toISOString().slice(0, 16), // datetime-local
  context: {
    operator: '',
    lot_number: '',
    method: '',
    sample_id: '',
    notes: '',
  },
};

/**
 * Resolve the logged-in operator for the default operator field.
 * Falls back to empty string — the operator then fills it in manually.
 * Wired to window.BIONEXUS_USER so session auth can inject it later
 * without coupling this form to the auth module.
 */
function resolveCurrentOperator() {
  if (typeof window !== 'undefined' && window.BIONEXUS_USER?.operator_id) {
    return window.BIONEXUS_USER.operator_id;
  }
  if (typeof window !== 'undefined' && window.BIONEXUS_USER?.email) {
    return window.BIONEXUS_USER.email;
  }
  return '';
}

/**
 * Pure-JS mirror of InstrumentConfig.evaluate_threshold (Python).
 *
 * Returns 'log' | 'alert' | 'block'. Falls back to 'log' for any case
 * that the backend treats as "no opinion" (missing config, non-numeric
 * value, parameter not in the thresholds dict, malformed rule).
 *
 * Kept side-effect-free so we can call it on every keystroke during
 * the capture form to give instant operator feedback. The server is
 * the canonical source of truth and re-evaluates on submit.
 */
export function evaluateThreshold(thresholds, parameter, rawValue) {
  if (!thresholds || typeof thresholds !== 'object') return 'log';
  const rule = thresholds[parameter];
  if (!rule || typeof rule !== 'object') return 'log';

  const value = Number(rawValue);
  if (!Number.isFinite(value)) return 'log';

  // Range-based threshold (min/max)
  if (typeof rule.min === 'number' && value < rule.min) {
    return rule.action || 'alert';
  }
  if (typeof rule.max === 'number' && value > rule.max) {
    return rule.action || 'alert';
  }

  // Deviation-based threshold (warn/block); compare against absolute value
  // because deviations are signed but the rule expresses magnitude.
  const magnitude = Math.abs(value);
  if (typeof rule.block === 'number' && magnitude >= rule.block) {
    return 'block';
  }
  if (typeof rule.warn === 'number' && magnitude >= rule.warn) {
    return 'alert';
  }

  return 'log';
}

export default function CaptureMeasurement() {
  const navigate = useNavigate();
  const [instruments, setInstruments] = useState([]);
  const [samples, setSamples] = useState([]);
  const [config, setConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [form, setForm] = useState({
    ...EMPTY_FORM,
    context: { ...EMPTY_FORM.context, operator: resolveCurrentOperator() },
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [inst, samp] = await Promise.all([fetchInstruments(), fetchSamples()]);
        setInstruments(inst);
        setSamples(samp);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Whenever the instrument changes, pull its config so we know what's required
  useEffect(() => {
    if (!form.instrument) {
      setConfig(null);
      return;
    }
    setConfigLoading(true);
    fetchInstrumentConfig(form.instrument)
      .then((cfg) => {
        setConfig(cfg);
        // Prefill the default unit from the config if the form unit is still empty
        if (cfg.units && !form.unit) {
          setForm((prev) => ({ ...prev, unit: cfg.units }));
        }
      })
      .catch((err) => setError(`Failed to load instrument config: ${err.message}`))
      .finally(() => setConfigLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.instrument]);

  const requiredFields = useMemo(() => {
    if (!config) return new Set();
    return new Set(config.required_metadata_fields || []);
  }, [config]);

  // Live threshold verdict — recomputed on every relevant keystroke.
  // 'log' means "all clear", 'alert' shows a banner, 'block' shows banner +
  // disables the submit button. The server is the canonical evaluator ;
  // this is purely UX feedback before the round-trip.
  const thresholdVerdict = useMemo(() => {
    if (!config || !config.thresholds) return 'log';
    if (!form.parameter || form.value === '') return 'log';
    return evaluateThreshold(config.thresholds, form.parameter, form.value);
  }, [config, form.parameter, form.value]);

  const submitBlocked = thresholdVerdict === 'block';

  function setTopLevel(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function setContextField(key, value) {
    setForm((prev) => ({
      ...prev,
      context: { ...prev.context, [key]: value },
    }));
  }

  function validateLocally() {
    const errors = {};
    if (!form.sample) errors.sample = 'Sample is required.';
    if (!form.instrument) errors.instrument = 'Instrument is required.';
    if (!form.parameter) errors.parameter = 'Parameter is required.';
    if (form.value === '' || form.value === null) errors.value = 'Value is required.';
    if (!form.unit) errors.unit = 'Unit is required.';
    if (!form.measured_at) errors.measured_at = 'Measurement time is required.';

    for (const field of requiredFields) {
      const val = form.context[field];
      if (!val || (typeof val === 'string' && !val.trim())) {
        errors[`context.${field}`] =
          'Required by this instrument\u2019s configuration.';
      }
    }
    return errors;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (submitBlocked) {
      // Client-side defense in depth ; the server is the canonical
      // evaluator and would 400 this anyway.
      setError('Submission blocked by instrument threshold rule.');
      return;
    }
    const localErrors = validateLocally();
    if (Object.keys(localErrors).length > 0) {
      setFieldErrors(localErrors);
      return;
    }
    setFieldErrors({});
    setSubmitting(true);

    try {
      const payload = {
        sample: Number(form.sample),
        instrument: Number(form.instrument),
        parameter: form.parameter,
        value: form.value,
        unit: form.unit,
        // Backend expects ISO — datetime-local gives YYYY-MM-DDTHH:mm
        measured_at: new Date(form.measured_at).toISOString(),
        context: { ...form.context },
      };
      const created = await createMeasurement(payload);
      setSuccess(
        `Captured measurement #${created.id} (hash ${(created.data_hash || '').slice(0, 12)}\u2026)`,
      );
      // Reset value fields but keep instrument, sample and operator
      setForm((prev) => ({
        ...prev,
        parameter: '',
        value: '',
        measured_at: new Date().toISOString().slice(0, 16),
        context: { ...prev.context, notes: '' },
      }));
    } catch (err) {
      // DRF returns field errors as { field: [msg] } or nested { context: { field: msg } }
      const mapped = {};
      const detail = err.detail;
      if (detail && typeof detail === 'object') {
        for (const [k, v] of Object.entries(detail)) {
          if (k === 'context' && v && typeof v === 'object') {
            for (const [ctxK, ctxV] of Object.entries(v)) {
              mapped[`context.${ctxK}`] = Array.isArray(ctxV) ? ctxV.join(', ') : String(ctxV);
            }
          } else {
            mapped[k] = Array.isArray(v) ? v.join(', ') : String(v);
          }
        }
      }
      setFieldErrors(mapped);
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="loading">Loading capture form…</div>;

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <h1>Capture Measurement</h1>
        <p>
          Record an instrument reading with the operational context required by
          the instrument&apos;s configuration. Value, timestamp, operator, lot,
          and method are bound into the SHA-256 integrity hash.
        </p>
      </div>

      {error && <div className="error-banner"><span>{error}</span></div>}
      {success && (
        <div
          className="error-banner"
          style={{ background: '#1a3a24', borderColor: '#3fb950', color: '#a8e6b8' }}
        >
          <span>{success}</span>
          <button onClick={() => navigate('/measurements')}>View all</button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="capture-form">
        <fieldset>
          <legend>Instrument & Sample</legend>

          <label className="form-label">
            Instrument *
            <select
              className="form-input"
              value={form.instrument}
              onChange={(e) => setTopLevel('instrument', e.target.value)}
            >
              <option value="">Select an instrument…</option>
              {instruments.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} ({i.serial_number})
                </option>
              ))}
            </select>
            {fieldErrors.instrument && (
              <span className="form-error">{fieldErrors.instrument}</span>
            )}
          </label>

          {configLoading && (
            <div className="config-hint">Loading instrument configuration…</div>
          )}
          {config && config.configured === false && form.instrument && (
            <div className="config-hint config-hint--warn">
              No configuration attached to this instrument — no metadata fields
              are enforced. Consider creating a config for regulatory traceability.
            </div>
          )}
          {config && config.configured && (
            <div className="config-hint">
              Parser: <strong>{config.parser_type}</strong>
              {config.units && <> · Default unit: <strong>{config.units}</strong></>}
              {config.required_metadata_fields?.length > 0 && (
                <> · Required metadata:{' '}
                  <strong>{config.required_metadata_fields.join(', ')}</strong>
                </>
              )}
            </div>
          )}

          <label className="form-label">
            Sample *
            <select
              className="form-input"
              value={form.sample}
              onChange={(e) => setTopLevel('sample', e.target.value)}
            >
              <option value="">Select a sample…</option>
              {samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.sample_id} — {s.batch_number || 'no batch'}
                </option>
              ))}
            </select>
            {fieldErrors.sample && (
              <span className="form-error">{fieldErrors.sample}</span>
            )}
          </label>
        </fieldset>

        <fieldset>
          <legend>Reading</legend>

          <div className="form-row">
            <label className="form-label">
              Parameter *
              <input
                className="form-input"
                value={form.parameter}
                onChange={(e) => setTopLevel('parameter', e.target.value)}
                placeholder="pH, weight, absorbance…"
              />
              {fieldErrors.parameter && (
                <span className="form-error">{fieldErrors.parameter}</span>
              )}
            </label>

            <label className="form-label">
              Value *
              <input
                className="form-input"
                value={form.value}
                onChange={(e) => setTopLevel('value', e.target.value)}
                placeholder="7.4200"
                inputMode="decimal"
              />
              {fieldErrors.value && (
                <span className="form-error">{fieldErrors.value}</span>
              )}
            </label>

            <label className="form-label">
              Unit *
              <input
                className="form-input"
                value={form.unit}
                onChange={(e) => setTopLevel('unit', e.target.value)}
                placeholder="pH, g, mg/L"
              />
              {fieldErrors.unit && (
                <span className="form-error">{fieldErrors.unit}</span>
              )}
            </label>
          </div>

          <label className="form-label">
            Measured At *
            <input
              type="datetime-local"
              className="form-input"
              value={form.measured_at}
              onChange={(e) => setTopLevel('measured_at', e.target.value)}
            />
            {fieldErrors.measured_at && (
              <span className="form-error">{fieldErrors.measured_at}</span>
            )}
          </label>
        </fieldset>

        <fieldset>
          <legend>Operational Context</legend>
          <p className="fieldset-hint">
            Fields marked * are required by the selected instrument&apos;s configuration.
          </p>

          {CONTEXT_FIELDS.map(({ key, label, placeholder, textarea }) => {
            const isRequired = requiredFields.has(key);
            const errKey = `context.${key}`;
            return (
              <label key={key} className="form-label">
                {label}{isRequired && ' *'}
                {textarea ? (
                  <textarea
                    className="form-input"
                    rows={3}
                    value={form.context[key]}
                    onChange={(e) => setContextField(key, e.target.value)}
                    placeholder={placeholder}
                  />
                ) : (
                  <input
                    className="form-input"
                    value={form.context[key]}
                    onChange={(e) => setContextField(key, e.target.value)}
                    placeholder={placeholder}
                  />
                )}
                {fieldErrors[errKey] && (
                  <span className="form-error">{fieldErrors[errKey]}</span>
                )}
              </label>
            );
          })}
        </fieldset>

        {VERDICT_BANNER[thresholdVerdict] && (
          <div
            className={VERDICT_BANNER[thresholdVerdict].className}
            role="alert"
            data-testid={`threshold-banner-${thresholdVerdict}`}
          >
            <strong>{VERDICT_BANNER[thresholdVerdict].headline}</strong>
            <p>{VERDICT_BANNER[thresholdVerdict].body}</p>
          </div>
        )}

        <div className="form-footer">
          <button
            type="submit"
            className="btn btn--primary"
            disabled={submitting || submitBlocked}
            title={submitBlocked ? 'Submit blocked by threshold rule' : ''}
          >
            {submitting
              ? 'Capturing…'
              : submitBlocked
                ? 'Blocked by threshold'
                : 'Capture Measurement'}
          </button>
        </div>
      </form>
    </div>
  );
}
