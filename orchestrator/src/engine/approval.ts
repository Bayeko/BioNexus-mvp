import type { ProposalStatus } from '../store/types.js';

/** Valid state transitions for proposal lifecycle */
const VALID_TRANSITIONS: Record<ProposalStatus, ProposalStatus[]> = {
  pending_approval: ['approved', 'rejected'],
  approved: ['executing'],
  rejected: [],
  executing: ['completed', 'failed'],
  completed: [],
  failed: [],
};

export function canTransition(from: ProposalStatus, to: ProposalStatus): boolean {
  return VALID_TRANSITIONS[from]?.includes(to) ?? false;
}

export function validateTransition(from: ProposalStatus, to: ProposalStatus): void {
  if (!canTransition(from, to)) {
    throw new Error(`Invalid proposal transition: ${from} → ${to}`);
  }
}

export function isTerminal(status: ProposalStatus): boolean {
  return status === 'completed' || status === 'failed' || status === 'rejected';
}

export function isPending(status: ProposalStatus): boolean {
  return status === 'pending_approval';
}
