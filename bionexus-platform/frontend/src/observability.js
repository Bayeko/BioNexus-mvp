/**
 * Frontend observability initialization.
 *
 * Sentry is loaded lazily and ONLY when VITE_SENTRY_DSN is set at build
 * time, so dev runs and tests stay free of network calls. The default
 * severity tag mirrors the backend convention: p0 (GxP breach), p1
 * (prod down), p2 (degraded), p3 (minor). Tag overrides at capture
 * sites take precedence.
 *
 * Add VITE_SENTRY_DSN to .env.production or your CI build env to enable.
 */

export async function initObservability() {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) {
    return; // dev/test mode — no network calls, no SDK loaded
  }

  try {
    const Sentry = await import('@sentry/react');
    Sentry.init({
      dsn,
      environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'dev',
      release: import.meta.env.VITE_SENTRY_RELEASE || undefined,
      // Keep tracing low in prod to stay within free-plan quota.
      tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || 0),
      // No PII policy: never attach IP, user agent, or auto-detected user.
      sendDefaultPii: false,
      initialScope: {
        tags: { severity: 'p2' }, // default; override per capture
      },
    });
    // eslint-disable-next-line no-console
    console.info('[observability] Sentry initialized');
  } catch (err) {
    // SDK not installed (e.g. dev environment). Silent fallback so the
    // app keeps booting; the absence of @sentry/react is intentional in
    // local development.
    // eslint-disable-next-line no-console
    console.warn('[observability] Sentry SDK not available:', err.message);
  }
}
