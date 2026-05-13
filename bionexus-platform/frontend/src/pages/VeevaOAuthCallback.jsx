/**
 * OAuth2 callback landing page.
 *
 * Vault redirects the operator here after authorize approval with two
 * query parameters: ``code`` (single-use authorization code) and
 * ``state`` (the CSRF token we minted before the redirect).
 *
 * This page strips both, POSTs them to the backend callback endpoint,
 * and bounces back to /integrations/veeva on success.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { postVeevaOAuthCallback } from '../api';
import { useToast } from '../components/Toast';

export default function VeevaOAuthCallback() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { toast } = useToast();
  const [status, setStatus] = useState('processing');
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = params.get('code');
    const state = params.get('state');

    if (!code || !state) {
      setStatus('error');
      setError('Missing code or state in the callback URL.');
      return;
    }

    (async () => {
      try {
        const result = await postVeevaOAuthCallback(code, state);
        if (result.ok && result.success) {
          setStatus('success');
          toast.success('OAuth2 connection complete.');
          setTimeout(() => navigate('/integrations/veeva'), 1200);
        } else {
          setStatus('error');
          setError(result.detail || 'Callback failed.');
          toast.error(result.detail || 'OAuth callback failed.');
        }
      } catch (err) {
        setStatus('error');
        setError(err.message);
        toast.error(err.message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="page-wrapper"
      style={{ maxWidth: 520, margin: '60px auto', textAlign: 'center' }}
    >
      <h1>Veeva OAuth2 callback</h1>
      {status === 'processing' && (
        <p>Exchanging authorization code for an access token…</p>
      )}
      {status === 'success' && (
        <p>Success. Redirecting you back to the Veeva connection page…</p>
      )}
      {status === 'error' && (
        <>
          <p style={{ color: '#fca5a5' }}>OAuth callback failed: {error}</p>
          <button
            className="btn btn--primary"
            onClick={() => navigate('/integrations/veeva')}
            style={{ marginTop: 16 }}
          >
            Back to Veeva settings
          </button>
        </>
      )}
    </div>
  );
}
