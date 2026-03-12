import React from 'react';
import type { WorkflowDefinition } from '../api';

interface WorkflowManagerProps {
  workflows: WorkflowDefinition[];
  onToggle: (id: string) => void;
  onTrigger: (id: string) => void;
  onDelete: (id: string) => void;
}

function triggerLabel(trigger: WorkflowDefinition['trigger']): string {
  if (trigger.type === 'cron' && trigger.cron) return `cron: ${trigger.cron}`;
  if (trigger.type === 'event' && trigger.event) return `event: ${trigger.event}`;
  return 'Manual trigger';
}

export function WorkflowManager({ workflows, onToggle, onTrigger, onDelete }: WorkflowManagerProps) {
  return (
    <div>
      <div className="page-header">
        <h2>Workflows</h2>
        <p>Configure automated workflows and their triggers</p>
      </div>

      {workflows.length === 0 ? (
        <div className="empty-state">
          <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09" />
          </svg>
          <p>No workflows configured</p>
          <p className="empty-subtitle">Create a workflow from the Create page</p>
        </div>
      ) : (
        workflows.map((wf) => (
          <div key={wf.id} className="card workflow-card">
            <div className="card-header">
              <div className="card-header-left">
                <button
                  className={`toggle ${wf.enabled ? 'active' : ''}`}
                  onClick={() => onToggle(wf.id)}
                  title={wf.enabled ? 'Disable workflow' : 'Enable workflow'}
                />
                <div>
                  <span className="card-title">{wf.name}</span>
                  <span className={`badge ${wf.source === 'builtin' ? 'badge-muted' : 'badge-blue'}`} style={{ marginLeft: 8 }}>
                    {wf.source === 'builtin' ? 'Built-in' : 'Custom'}
                  </span>
                </div>
              </div>
              <span className="card-meta">{triggerLabel(wf.trigger)}</span>
            </div>

            <div className="card-body">
              <p>{wf.description}</p>

              {/* Required connectors as badges */}
              {wf.requiredConnectors.length > 0 && (
                <div className="workflow-meta">
                  {wf.requiredConnectors.map((conn) => (
                    <span key={conn} className="connector-tag">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 4h6v6H4zM14 4h6v6h-6z" />
                      </svg>
                      {conn}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="card-actions">
              <button className="btn btn-sm btn-trigger" onClick={() => onTrigger(wf.id)}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Trigger Now
              </button>
              {wf.source === 'user-created' && (
                <button className="btn btn-sm btn-danger" onClick={() => onDelete(wf.id)}>
                  Delete
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
