import React from 'react';

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  pending_approval: { label: 'Pending', className: 'status-pending' },
  approved: { label: 'Approved', className: 'status-approved' },
  rejected: { label: 'Rejected', className: 'status-rejected' },
  executing: { label: 'Executing', className: 'status-executing' },
  completed: { label: 'Completed', className: 'status-completed' },
  failed: { label: 'Failed', className: 'status-failed' },
};

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const mapped = STATUS_MAP[status] ?? { label: status, className: 'status-pending' };
  return (
    <span className={`status-badge ${mapped.className}`}>
      <span className="status-dot" />
      {mapped.label}
    </span>
  );
}
