import React from 'react';

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  pending_approval: { label: 'Pending', className: 'badge-amber' },
  approved: { label: 'Approved', className: 'badge-green' },
  rejected: { label: 'Rejected', className: 'badge-red' },
  executing: { label: 'Executing', className: 'badge-blue' },
  completed: { label: 'Completed', className: 'badge-green' },
  failed: { label: 'Failed', className: 'badge-red' },
};

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const mapped = STATUS_MAP[status] ?? { label: status, className: 'badge-muted' };
  return <span className={`badge ${mapped.className}`}>{mapped.label}</span>;
}
