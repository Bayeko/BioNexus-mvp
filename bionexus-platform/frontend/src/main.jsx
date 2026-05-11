import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './theme.css';
import { initObservability } from './observability';

// Initialize Sentry before mounting React so errors during first render
// are captured. The init is a no-op when VITE_SENTRY_DSN is unset.
initObservability();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
