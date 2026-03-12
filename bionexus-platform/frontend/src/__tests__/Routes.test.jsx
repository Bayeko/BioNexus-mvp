import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import AppRoutes from '../routes';

// Mock fetch to avoid real API calls during tests
globalThis.fetch = vi.fn(() =>
  Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) })
);

test('renders dashboard on home route', () => {
  render(
    <MemoryRouter initialEntries={['/']}>
      <AppRoutes />
    </MemoryRouter>
  );
  expect(screen.getByText('Dashboard')).toBeInTheDocument();
});

test('renders instruments page', () => {
  render(
    <MemoryRouter initialEntries={['/instruments']}>
      <AppRoutes />
    </MemoryRouter>
  );
  expect(screen.getByText('Instruments')).toBeInTheDocument();
});

test('renders audit log page', () => {
  render(
    <MemoryRouter initialEntries={['/audit']}>
      <AppRoutes />
    </MemoryRouter>
  );
  expect(screen.getByRole('heading', { name: /audit log/i })).toBeInTheDocument();
});
