import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App';

// Mock fetch to avoid real API calls during tests
globalThis.fetch = vi.fn(() =>
  Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) })
);

test('renders BioNexus layout', () => {
  render(<App />);
  expect(screen.getByText('BioNexus')).toBeInTheDocument();
});
