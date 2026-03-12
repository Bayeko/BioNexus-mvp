import React, { useState } from 'react';

interface WorkflowCreatorProps {
  onCreateFromPrompt: (prompt: string) => Promise<void>;
}

const EXAMPLES = [
  'Every time Johannes emails me, draft a prep doc with relevant Drive files',
  'Every Monday at 9am, check for PRs that need my review',
  'When a new file is added to the docs/ folder, create a summary and share it via email',
];

export function WorkflowCreator({ onCreateFromPrompt }: WorkflowCreatorProps) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await onCreateFromPrompt(prompt.trim());
      setSuccess('Workflow created successfully!');
      setPrompt('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Create Workflow</h2>
        <p>Describe a new workflow in plain English and let AI build it</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <textarea
            className="input"
            style={{ minHeight: 80, resize: 'vertical', fontFamily: 'var(--font)' }}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe what you want the workflow to do..."
            disabled={loading}
          />

          <div className="card-actions">
            <button className="btn btn-primary" type="submit" disabled={loading || !prompt.trim()}>
              {loading && <span className="spinner" />}
              {loading ? 'Creating...' : 'Create Workflow'}
            </button>
          </div>
        </form>

        {error && (
          <p style={{ color: 'var(--red)', fontSize: 13, marginTop: 12 }}>{error}</p>
        )}
        {success && (
          <p style={{ color: 'var(--green)', fontSize: 13, marginTop: 12 }}>{success}</p>
        )}
      </div>

      <div className="section-label">Examples</div>
      <div className="card">
        <div className="card-body">
          {EXAMPLES.map((example, i) => (
            <div
              key={i}
              className="action-item"
              style={{ cursor: 'pointer' }}
              onClick={() => setPrompt(example)}
            >
              <span style={{ color: 'var(--accent)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>&gt;</span>
              <span>{example}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
