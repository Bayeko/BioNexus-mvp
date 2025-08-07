import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import AppRoutes from '../routes';

test('renders home route by default', () => {
  render(
    <MemoryRouter initialEntries={['/']}>
      <AppRoutes />
    </MemoryRouter>
  );
  expect(
    screen.getByRole('heading', { name: /bionexus ui/i })
  ).toBeInTheDocument();
});
