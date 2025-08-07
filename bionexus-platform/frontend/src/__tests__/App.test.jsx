import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App';

test('renders BioNexus UI heading', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /bionexus ui/i })).toBeInTheDocument();
});
