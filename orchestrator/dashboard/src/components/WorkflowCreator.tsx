import React, { useState } from 'react';

interface WorkflowCreatorProps {
  onCreateFromPrompt: (prompt: string) => Promise<void>;
}

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
      <h2>Create Workflow</h2>
      <div className="card">
        <div className="card-body">
          <p style={{ marginBottom: 12 }}>
            Describe a new workflow in plain English. The AI will create a structured
            workflow definition from your description.
          </p>

          <form onSubmit={handleSubmit}>
            <input
              className="input"
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder='e.g. "Every time Johannes emails me, draft a prep doc with relevant Drive files"'
              disabled={loading}
            />

            <div className="card-actions">
              <button className="btn btn-primary" type="submit" disabled={loading || !prompt.trim()}>
                {loading ? 'Creating...' : 'Create Workflow'}
              </button>
            </div>
          </form>

          {error && (
            <p style={{ color: 'var(--red)', fontSize: 13, marginTop: 8 }}>{error}</p>
          )}
          {success && (
            <p style={{ color: 'var(--green)', fontSize: 13, marginTop: 8 }}>{success}</p>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="card-title" style={{ marginBottom: 8 }}>Examples</div>
        <div className="card-body">
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {[
              'Every time Johannes emails me, draft a prep doc with relevant Drive files',
              'Every Monday at 9am, check for PRs that need my review',
              'When a new file is added to the docs/ folder, create a summary and share it via email',
            ].map((example, i) => (
              <li
                key={i}
                style={{ padding: '6px 0', cursor: 'pointer', fontSize: 13 }}
                onClick={() => setPrompt(example)}
              >
                <span style={{ color: 'var(--accent)', marginRight: 6 }}>&gt;</span>
                {example}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
