import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import CaptureMeasurement from '../pages/CaptureMeasurement';

/**
 * Mock the fetch layer for every scenario. Each test sets
 * the response queue it needs before rendering the page.
 */

function mockFetchSequence(responses) {
  const queue = [...responses];
  globalThis.fetch = vi.fn((url, opts) => {
    // Match by URL contains + method so the tests can be flexible
    const method = opts?.method || 'GET';
    const match = queue.findIndex(
      (r) =>
        (!r.url || url.includes(r.url)) &&
        (!r.method || r.method === method),
    );
    if (match === -1) {
      return Promise.reject(
        new Error(`Unexpected fetch to ${method} ${url}`),
      );
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
// Tests
// ---------------------------------------------------------------------------

describe('CaptureMeasurement page', () => {
  test('renders and loads instruments + samples', async () => {
    mockFetchSequence([
      {
        url: '/api/instruments/',
        body: [{ id: 1, name: 'Mettler XPE205', serial_number: 'MT-001' }],
      },
      {
        url: '/api/samples/',
        body: [{ id: 10, sample_id: 'SMP-A', batch_number: 'B-1' }],
      },
    ]);

    renderPage();

    expect(
      await screen.findByRole('heading', { name: /Capture Measurement/i }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/Mettler XPE205/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/SMP-A/)).toBeInTheDocument();
  });

  test('shows dynamic required-field markers when instrument config requires them', async () => {
    mockFetchSequence([
      {
        url: '/api/instruments/',
        body: [{ id: 1, name: 'Balance', serial_number: 'MT-001' }],
      },
      { url: '/api/samples/', body: [{ id: 10, sample_id: 'SMP-A' }] },
      {
        url: '/api/instruments/1/config/',
        body: {
          parser_type: 'mettler_sics_v1',
          units: 'g',
          required_metadata_fields: ['operator', 'lot_number'],
          thresholds: {},
          configured: true,
        },
      },
    ]);

    renderPage();

    // Wait for instrument list to load, then select instrument
    const select = await screen.findByRole('combobox', { name: /Instrument/i });
    fireEvent.change(select, { target: { value: '1' } });

    // Config hint appears listing the required fields
    await waitFor(() =>
      expect(
        screen.getByText(/mettler_sics_v1/),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/operator, lot_number/)).toBeInTheDocument();

    // Required markers appear on the matching labels
    expect(screen.getByText(/Operator ID \*/)).toBeInTheDocument();
    expect(screen.getByText(/Lot \/ Batch Number \*/)).toBeInTheDocument();
    // Non-required fields stay unmarked
    expect(screen.queryByText(/^Notes \*$/)).not.toBeInTheDocument();
  });

  test('blocks submission when required context fields are missing', async () => {
    mockFetchSequence([
      {
        url: '/api/instruments/',
        body: [{ id: 1, name: 'Balance', serial_number: 'MT-001' }],
      },
      { url: '/api/samples/', body: [{ id: 10, sample_id: 'SMP-A' }] },
      {
        url: '/api/instruments/1/config/',
        body: {
          parser_type: 'mettler_sics_v1',
          units: 'g',
          required_metadata_fields: ['operator'],
          thresholds: {},
          configured: true,
        },
      },
    ]);

    renderPage();

    // Pick instrument + sample
    fireEvent.change(
      await screen.findByRole('combobox', { name: /Instrument/i }),
      { target: { value: '1' } },
    );
    await waitFor(() =>
      expect(screen.getByText(/mettler_sics_v1/)).toBeInTheDocument(),
    );
    fireEvent.change(screen.getByRole('combobox', { name: /Sample/i }), {
      target: { value: '10' },
    });

    // Fill everything EXCEPT operator
    fireEvent.change(screen.getByPlaceholderText(/pH, weight/i), {
      target: { value: 'weight' },
    });
    fireEvent.change(screen.getByPlaceholderText('7.4200'), {
      target: { value: '12.3' },
    });
    // Unit was pre-filled from config — leave it
    fireEvent.click(
      screen.getByRole('button', { name: /Capture Measurement/i }),
    );

    await waitFor(() =>
      expect(
        screen.getByText(/Required by this instrument/i),
      ).toBeInTheDocument(),
    );
    // No POST should have been made
    expect(
      globalThis.fetch.mock.calls.some((c) => c[1]?.method === 'POST'),
    ).toBe(false);
  });
});
