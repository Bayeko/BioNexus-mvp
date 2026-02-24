import React, { useState } from 'react';

const styles = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: "'Segoe UI', sans-serif",
  },
  card: {
    background: 'white',
    borderRadius: '16px',
    padding: '48px',
    width: '400px',
    boxShadow: '0 25px 60px rgba(0,0,0,0.4)',
  },
  logo: {
    textAlign: 'center',
    marginBottom: '32px',
  },
  logoTitle: {
    fontSize: '28px',
    fontWeight: '800',
    color: '#0f172a',
    margin: 0,
  },
  logoSub: {
    fontSize: '13px',
    color: '#64748b',
    marginTop: '4px',
  },
  badge: {
    display: 'inline-block',
    background: '#dbeafe',
    color: '#1d4ed8',
    fontSize: '11px',
    padding: '3px 10px',
    borderRadius: '99px',
    marginTop: '8px',
    fontWeight: '600',
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '6px',
  },
  input: {
    width: '100%',
    padding: '12px 14px',
    border: '2px solid #e5e7eb',
    borderRadius: '8px',
    fontSize: '14px',
    marginBottom: '20px',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s',
  },
  button: {
    width: '100%',
    padding: '14px',
    background: 'linear-gradient(135deg, #1d4ed8, #7c3aed)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '700',
    cursor: 'pointer',
    marginTop: '8px',
  },
  error: {
    background: '#fef2f2',
    border: '1px solid #fca5a5',
    color: '#dc2626',
    padding: '12px',
    borderRadius: '8px',
    marginBottom: '16px',
    fontSize: '13px',
  },
};

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('http://localhost:8000/api/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('token', data.access || data.token || 'demo');
        localStorage.setItem('username', username);
        onLogin(username);
      } else {
        // fallback: let local demo login work
        if (username === 'demo_user' && password === 'DemoPassword123!') {
          localStorage.setItem('token', 'demo-token');
          localStorage.setItem('username', username);
          onLogin(username);
        } else {
          setError('Identifiants incorrects. Essayez: demo_user / DemoPassword123!');
        }
      }
    } catch {
      // If backend is down, allow demo login
      if (username === 'demo_user' && password === 'DemoPassword123!') {
        localStorage.setItem('token', 'demo-token');
        localStorage.setItem('username', username);
        onLogin(username);
      } else {
        setError('Impossible de contacter le serveur. Essayez: demo_user / DemoPassword123!');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <p style={styles.logoTitle}>🧬 BioNexus</p>
          <p style={styles.logoSub}>GxP Compliance Platform</p>
          <span style={styles.badge}>21 CFR Part 11 ✓</span>
        </div>

        {error && <div style={styles.error}>⚠️ {error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Nom d'utilisateur</label>
          <input
            style={styles.input}
            type="text"
            placeholder="demo_user"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
          />

          <label style={styles.label}>Mot de passe</label>
          <input
            style={styles.input}
            type="password"
            placeholder="••••••••••••"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          <button style={styles.button} type="submit" disabled={loading}>
            {loading ? '⏳ Connexion...' : '🔐 Se connecter'}
          </button>
        </form>

        <p style={{ textAlign: 'center', color: '#9ca3af', fontSize: '12px', marginTop: '20px' }}>
          demo_user / DemoPassword123!
        </p>
      </div>
    </div>
  );
}
