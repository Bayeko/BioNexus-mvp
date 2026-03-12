import React from 'react';

export default function StatusBadge({ status }) {
  const label = (status || '').replace(/_/g, ' ');
  return <span className={`badge badge--${status}`}>{label}</span>;
}
