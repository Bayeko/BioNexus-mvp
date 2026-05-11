import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import CaptureMeasurement, { evaluateThreshold } from '../pages/CaptureMeasurement';

/**
 * Threshold UI tests for CaptureMeasurement.
 *
 * Covers the client-side mirror of InstrumentConfig.evaluate_threshold and
 * the form behaviour for each verdict:
 *   - log   : no banner, submit enabled
 *   - alert : orange banner, submit still enabled (out-of-spec is recorded)
 *   - block : red banner, submit disabled and re-labelled
 */

function mockFetchSequence(responses) {
  const queue = [...responses];
  globalThis.fetch = vi.fn((url, opts) => {
    const method = opts?.method || 'GET';
    const match = queue.findIndex(
      (r) => (!r.url || url.includes(r.url)) && (!r.method || r.method === method),
    );
    if (match === -1) {
      return Promise.reject(new Error(`Unexpected fetch ${method} ${url}`));
    }
    const entry = queue.splice(match, 1)[0];
    return Promise.resolve({
      ok: entry.ok !== false,
      status: entry.status || 200,
      json: () => Promise.resolve(entry.body ?? []),
      text: () => Promise.resolve(JSON.stringify(entry.body ?? {})),
    });
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <CaptureMeasurement />
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Pure-function tests for evaluateThreshold
// ---------------------------------------------------------------------------

describe('evaluateThreshold (pure JS, mirrors Python)', () => {
  const rangeRule = { pH: { min: 6.8, max: 7.6, action: 'alert' } };
  const deviationRule = {
    weight_dev: { warn: 0.5, block: 1.0, unit: '%' },
  };

  test('returns log when value is in range', () => {
    expect(evaluateThreshold(rangeRule, 'pH', 7.2)).toBe('log');
  });

  test('returns configured action when value is below min', () => {
    expect(evaluateThreshold(rangeRule, 'pH', 6.5)).toBe('alert');
  });

  test('returns configured action when value is above max', () => {
    expect(evaluateThreshold(rangeRule, 'pH', 8.0)).toBe('alert');
  });

  test('returns alert at warn level, block at block level', () => {
    expect(evaluateThreshold(deviationRule, 'weight_dev', 0.3)).toBe('log');
    expect(evaluateThreshold(deviationRule, 'weight_dev', 0.7)).toBe('alert');
    expect(evaluateThreshold(deviationRule, 'weight_dev', 1.5)).toBe('block');
  });

  test('falls back to log for non-numeric, missing rule, or empty config', () => {
    expect(evaluateThreshold(rangeRule, 'pH', 'oops')).toBe('log');
    expect(evaluateThreshold(rangeRule, 'unknown', 5.0)).toBe('log');
    expect(evaluateThreshold(null, 'pH', 7.2)).toBe('log');
    expect(evaluateThreshold({}, 'pH', 7.2)).toBe('log');
  });

  test('block check uses magnitude (negative deviations also block)', () => {
    expect(evaluateThreshold(deviationRule, 'weight_dev', -1.5)).toBe('block');
  });
});

// ---------------------------------------------------------------------------
// Integration tests for the CaptureMeasurement form
// ---------------------------------------------------------------------------

describe('CaptureMeasurement threshold banner', () => {
  function setupWithThresholds(thresholds, required = []) {
    mockFetchSequence([
      {
        url: '/api/instruments/',
        body: [{ id: 1, name: 'pH meter A', serial_number: 'PH-001' }],
      },
      { url: '/api/samples/', body: [{ id: 10, sample_id: 'SMP-A' }] },
      {
        url: '/api/instruments/1/config/',
        body: {
          parser_type: 'generic_csv_v1',
          units: 'pH',
          required_metadata_fields: required,
          thresholds,
          configured: true,
        },
      },
    ]);
  }

  async function pickInstrument() {
    const instrumentSelect = await screen.findByRole('combobox', {
      name: /Instrument/i,
    });
    fireEvent.change(instrumentSelect, { target: { value: '1' } });
    // Wait for config to load (banner not yet, but parser_type appears)
    await waitFor(() =>
      expect(screen.getByText(/generic_csv_v1/)).toBeInTheDocument(),
    );
  }

  test('no banner when value is within spec', async () => {
    setupWithThresholds({ pH: { min: 6.8, max: 7.6, action: 'alert' } });
    renderPage();

    await pickInstrument();
    fireEvent.change(screen.getByPlaceholderText(/pH, weight/i), {
      target: { value: 'pH' },
    });
    fireEvent.change(screen.getByPlaceholderText('7.4200'), {
      target: { value: '7.2' },
    });

    expect(screen.queryByTestId('threshold-banner-alert')).not.toBeInTheDocument();
    expect(screen.queryByTestId('threshold-banner-block')).not.toBeInTheDocument();
    const submit = screen.getByRole('button', { name: /Capture Measurement/i });
    expect(submit).not.toBeDisabled();
  });

  test('alert banner shows for out-of-range value, submit still enabled', async () => {
    setupWithThresholds({ pH: { min: 6.8, max: 7.6, action: 'alert' } });
    renderPage();

    await pickInstrument();
    fireEvent.change(screen.getByPlaceholderText(/pH, weight/i), {
      target: { value: 'pH' },
    });
    fireEvent.change(screen.getByPlaceholderText('7.4200'), {
      target: { value: '8.5' },
    });

    expect(await screen.findByTestId('threshold-banner-alert')).toBeInTheDocument();
    expect(screen.getByText(/Threshold alert/i)).toBeInTheDocument();
    const submit = screen.getByRole('button', { name: /Capture Measurement/i });
    expect(submit).not.toBeDisabled();
  });

  test('block banner shows for blocking value, submit is disabled', async () => {
    setupWithThresholds({
      weight_dev: { warn: 0.5, block: 1.0, unit: '%' },
    });
    renderPage();

    await pickInstrument();
    fireEvent.change(screen.getByPlaceholderText(/pH, weight/i), {
      target: { value: 'weight_dev' },
    });
    fireEvent.change(screen.getByPlaceholderText('7.4200'), {
      target: { value: '1.5' },
    });

    expect(await screen.findByTestId('threshold-banner-block')).toBeInTheDocument();
    const submit = screen.getByRole('button', { name: /Blocked by threshold/i });
    expect(submit).toBeDisabled();
  });
});
