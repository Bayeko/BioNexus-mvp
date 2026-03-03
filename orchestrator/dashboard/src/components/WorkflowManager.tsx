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
  return 'manual';
}

export function WorkflowManager({ workflows, onToggle, onTrigger, onDelete }: WorkflowManagerProps) {
  return (
    <div>
      <h2>Workflows</h2>

      {workflows.map((wf) => (
        <div key={wf.id} className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <button
                className={`toggle ${wf.enabled ? 'active' : ''}`}
                onClick={() => onToggle(wf.id)}
                title={wf.enabled ? 'Disable' : 'Enable'}
              />
              <div>
                <span className="card-title">{wf.name}</span>
                <span className={`badge ${wf.source === 'builtin' ? 'badge-muted' : 'badge-blue'}`} style={{ marginLeft: 8 }}>
                  {wf.source}
                </span>
              </div>
            </div>
            <span className="card-meta">{triggerLabel(wf.trigger)}</span>
          </div>

          <div className="card-body">
            <p>{wf.description}</p>
            <p style={{ marginTop: 4, fontSize: 11 }}>
              Connectors: {wf.requiredConnectors.join(', ') || 'none'}
            </p>
          </div>

          <div className="card-actions">
            <button className="btn btn-sm" onClick={() => onTrigger(wf.id)}>
              Trigger Now
            </button>
            {wf.source === 'user-created' && (
              <button className="btn btn-sm btn-reject" onClick={() => onDelete(wf.id)}>
                Delete
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
