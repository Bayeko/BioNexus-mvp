import React from 'react';
import type { Proposal } from '../api';
import { ProposalCard } from './ProposalCard';

interface ApprovalQueueProps {
  proposals: Proposal[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onChat: (id: string, message: string) => Promise<void>;
  onRevise: (id: string) => Promise<void>;
  onUndo: (id: string) => void;
}

export function ApprovalQueue({ proposals, onApprove, onReject, onChat, onRevise, onUndo }: ApprovalQueueProps) {
  const pending = proposals.filter((p) => p.status === 'pending_approval');
  const autoApproved = proposals.filter(
    (p) => p.autoApproved && p.status === 'approved' && p.undoDeadline && new Date(p.undoDeadline) > new Date(),
  );
  const history = proposals.filter((p) => p.status !== 'pending_approval');

  return (
    <div>
      <div className="page-header">
        <h2>Approval Queue</h2>
        <p>Review and approve proposed actions from your workflows</p>
      </div>

      {/* Auto-approved undo window */}
      {autoApproved.length > 0 && (
        <>
          <div className="section-label">Auto-Approved — Undo Window</div>
          {autoApproved.map((p) => (
            <ProposalCard
              key={p.id}
              proposal={p}
              onApprove={onApprove}
              onReject={onReject}
              onChat={onChat}
              onRevise={onRevise}
              onUndo={onUndo}
            />
          ))}
        </>
      )}

      {/* Pending approval */}
      {pending.length > 0 && (
        <>
          <div className="section-label">Awaiting Review ({pending.length})</div>
          {pending.map((p) => (
            <ProposalCard
              key={p.id}
              proposal={p}
              onApprove={onApprove}
              onReject={onReject}
              onChat={onChat}
              onRevise={onRevise}
            />
          ))}
        </>
      )}

      {/* Empty state */}
      {pending.length === 0 && autoApproved.length === 0 && (
        <div className="empty-state">
          <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          <p>No proposals awaiting review</p>
          <p className="empty-subtitle">Trigger a workflow to generate a new proposal</p>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <>
          <div className="section-label" style={{ marginTop: 32 }}>History</div>
          {history.slice(0, 20).map((p) => (
            <ProposalCard
              key={p.id}
              proposal={p}
              onApprove={onApprove}
              onReject={onReject}
              onChat={onChat}
              onRevise={onRevise}
            />
          ))}
        </>
      )}
    </div>
  );
}
