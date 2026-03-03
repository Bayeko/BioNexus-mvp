import React from 'react';
import type { Proposal } from '../api';
import { StatusBadge } from './StatusBadge';

interface ProposalCardProps {
  proposal: Proposal;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function ProposalCard({ proposal, onApprove, onReject }: ProposalCardProps) {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <span className="card-title">{proposal.workflowName}</span>
          <span className="card-meta" style={{ marginLeft: 8 }}>
            {timeAgo(proposal.createdAt)}
          </span>
        </div>
        <StatusBadge status={proposal.status} />
      </div>

      <div className="card-body">
        <p style={{ color: 'var(--text)', marginBottom: 8 }}>{proposal.summary}</p>

        {proposal.actions.length > 0 && (
          <ul className="action-list">
            {proposal.actions.map((action, i) => (
              <li key={i}>
                <span className={`priority-${action.priority}`}>
                  [{action.priority}]
                </span>{' '}
                {action.description}
              </li>
            ))}
          </ul>
        )}

        {proposal.reasoning && (
          <p style={{ marginTop: 8, fontStyle: 'italic', fontSize: 12 }}>
            {proposal.reasoning}
          </p>
        )}
      </div>

      {proposal.status === 'pending_approval' && (
        <div className="card-actions">
          <button className="btn btn-approve" onClick={() => onApprove(proposal.id)}>
            Approve
          </button>
          <button className="btn btn-reject" onClick={() => onReject(proposal.id)}>
            Reject
          </button>
        </div>
      )}

      {proposal.executionLog && proposal.executionLog.length > 0 && (
        <div style={{ marginTop: 12, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
          {proposal.executionLog.map((log, i) => (
            <div key={i}>{log}</div>
          ))}
        </div>
      )}
    </div>
  );
}
