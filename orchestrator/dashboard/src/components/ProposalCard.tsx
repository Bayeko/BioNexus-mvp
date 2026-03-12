import React, { useState, useEffect } from 'react';
import type { Proposal, RiskLevel } from '../api';
import { StatusBadge } from './StatusBadge';
import { ProposalChat } from './ProposalChat';

const RISK_BADGE: Record<RiskLevel, { label: string; cls: string }> = {
  green: { label: 'LOW', cls: 'badge badge-green' },
  yellow: { label: 'MED', cls: 'badge badge-amber' },
  red: { label: 'HIGH', cls: 'badge badge-red' },
};

const RISK_DOT: Record<RiskLevel, string> = {
  green: 'risk-dot risk-green',
  yellow: 'risk-dot risk-yellow',
  red: 'risk-dot risk-red',
};

interface ProposalCardProps {
  proposal: Proposal;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onChat: (id: string, message: string) => Promise<void>;
  onRevise: (id: string) => Promise<void>;
  onUndo?: (id: string) => void;
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

export function ProposalCard({ proposal, onApprove, onReject, onChat, onRevise, onUndo }: ProposalCardProps) {
  const [chatOpen, setChatOpen] = useState(false);
  const [logsOpen, setLogsOpen] = useState(false);
  const [undoRemaining, setUndoRemaining] = useState<number | null>(null);
  const isPending = proposal.status === 'pending_approval';
  const hasChat = (proposal.chatHistory?.length ?? 0) > 0;
  const hasLogs = (proposal.executionLog?.length ?? 0) > 0;

  const canUndo = proposal.autoApproved
    && proposal.undoDeadline
    && proposal.status === 'approved'
    && new Date(proposal.undoDeadline) > new Date();

  useEffect(() => {
    if (!canUndo || !proposal.undoDeadline) return;
    const tick = () => {
      const remaining = Math.max(0, Math.floor((new Date(proposal.undoDeadline!).getTime() - Date.now()) / 1000));
      setUndoRemaining(remaining);
      if (remaining <= 0) clearInterval(interval);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [canUndo, proposal.undoDeadline]);

  const riskBadge = proposal.riskLevel ? RISK_BADGE[proposal.riskLevel] : null;

  return (
    <div className="card">
      {/* Header */}
      <div className="card-header">
        <div className="card-header-left">
          <span className="card-title">{proposal.workflowName}</span>
          <span className="card-meta">{timeAgo(proposal.createdAt)}</span>
          {proposal.autoApproved && <span className="auto-badge">Auto</span>}
        </div>
        <div className="card-header-right">
          {riskBadge && <span className={riskBadge.cls}>{riskBadge.label}</span>}
          <StatusBadge status={proposal.status} />
        </div>
      </div>

      {/* Summary */}
      <p className="card-summary">{proposal.summary}</p>

      {/* Action checklist */}
      {proposal.actions.length > 0 && (
        <ul className="action-list">
          {proposal.actions.map((action, i) => (
            <li key={i} className="action-item">
              <span className="action-num">{i + 1}</span>
              {action.riskLevel && (
                <span className={RISK_DOT[action.riskLevel]} title={`${action.riskLevel} risk`} />
              )}
              <div className="action-content">
                <span className="action-desc">{action.description}</span>
                <span className={`priority-pill priority-${action.priority}`} style={{ marginLeft: 8 }}>
                  {action.priority}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Reasoning */}
      {proposal.reasoning && (
        <p className="card-body" style={{ marginTop: 10, fontStyle: 'italic', fontSize: 12.5 }}>
          {proposal.reasoning}
        </p>
      )}

      {/* Undo button (yellow auto-approved) */}
      {canUndo && undoRemaining !== null && undoRemaining > 0 && onUndo && (
        <div className="card-actions">
          <button className="btn btn-undo" onClick={() => onUndo(proposal.id)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 105.64-12.36L1 10" />
            </svg>
            Undo {Math.floor(undoRemaining / 60)}:{String(undoRemaining % 60).padStart(2, '0')}
          </button>
        </div>
      )}

      {/* Action buttons for pending */}
      {isPending && (
        <div className="card-actions">
          <button className="btn btn-approve" onClick={() => onApprove(proposal.id)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
            Approve
          </button>
          <button className="btn btn-reject" onClick={() => onReject(proposal.id)}>
            Reject
          </button>
          <button
            className={`btn btn-discuss ${chatOpen ? 'active' : ''}`}
            onClick={() => setChatOpen(!chatOpen)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>
            Discuss{hasChat ? ` (${proposal.chatHistory!.length})` : ''}
          </button>
        </div>
      )}

      {/* Discussion toggle for non-pending with chat */}
      {!isPending && !canUndo && hasChat && (
        <div className="card-actions">
          <button
            className={`btn btn-discuss ${chatOpen ? 'active' : ''}`}
            onClick={() => setChatOpen(!chatOpen)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>
            Discussion ({proposal.chatHistory!.length})
          </button>
        </div>
      )}

      {/* Chat panel */}
      {chatOpen && (
        <ProposalChat
          chatHistory={proposal.chatHistory ?? []}
          onSend={(msg) => onChat(proposal.id, msg)}
          onRevise={() => onRevise(proposal.id)}
          isPending={isPending}
        />
      )}

      {/* Collapsible execution logs */}
      {hasLogs && (
        <div className="card-footer">
          <button
            className={`exec-log-toggle ${logsOpen ? 'open' : ''}`}
            onClick={() => setLogsOpen(!logsOpen)}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
            Execution log ({proposal.executionLog!.length} entries)
          </button>
          {logsOpen && (
            <div className="exec-log">
              {proposal.executionLog!.map((log, i) => (
                <div key={i}>{log}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
