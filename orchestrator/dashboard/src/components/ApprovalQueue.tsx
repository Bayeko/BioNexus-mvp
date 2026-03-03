import React from 'react';
import type { Proposal } from '../api';
import { ProposalCard } from './ProposalCard';

interface ApprovalQueueProps {
  proposals: Proposal[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export function ApprovalQueue({ proposals, onApprove, onReject }: ApprovalQueueProps) {
  const pending = proposals.filter((p) => p.status === 'pending_approval');
  const history = proposals.filter((p) => p.status !== 'pending_approval');

  return (
    <div>
      <h2>Approval Queue</h2>

      {pending.length === 0 ? (
        <div className="empty-state">
          <p>No pending proposals</p>
          <p style={{ fontSize: 12, marginTop: 4 }}>
            Trigger a workflow to generate a proposal
          </p>
        </div>
      ) : (
        pending.map((p) => (
          <ProposalCard key={p.id} proposal={p} onApprove={onApprove} onReject={onReject} />
        ))
      )}

      {history.length > 0 && (
        <>
          <h2 style={{ marginTop: 24 }}>History</h2>
          {history.slice(0, 20).map((p) => (
            <ProposalCard key={p.id} proposal={p} onApprove={onApprove} onReject={onReject} />
          ))}
        </>
      )}
    </div>
  );
}
