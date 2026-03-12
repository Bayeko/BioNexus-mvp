import React from 'react';

export interface ActivityEvent {
  id: string;
  type: string;
  message: string;
  timestamp: string;
}

interface ActivityFeedProps {
  events: ActivityEvent[];
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function EventIcon({ type }: { type: string }) {
  const props = { width: 14, height: 14, fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

  if (type.includes('auto-approved') || type.includes('approved') || type.includes('completed'))
    return <svg {...props} viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12" /></svg>;
  if (type.includes('rejected') || type.includes('failed') || type.includes('undone'))
    return <svg {...props} viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>;
  if (type.includes('proposal:created'))
    return <svg {...props} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>;
  if (type.includes('workflow'))
    return <svg {...props} viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3" /></svg>;
  if (type.includes('connector'))
    return <svg {...props} viewBox="0 0 24 24"><path d="M4 4h6v6H4zM14 4h6v6h-6z" /></svg>;
  if (type.includes('connected'))
    return <svg {...props} viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" /></svg>;
  if (type.includes('error'))
    return <svg {...props} viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>;
  return <svg {...props} viewBox="0 0 24 24"><circle cx="12" cy="12" r="1" /></svg>;
}

function iconClass(type: string): string {
  if (type.includes('auto-approved') || type.includes('approved') || type.includes('completed'))
    return 'activity-icon activity-icon-approved';
  if (type.includes('rejected') || type.includes('failed') || type.includes('undone'))
    return 'activity-icon activity-icon-rejected';
  if (type.includes('proposal'))
    return 'activity-icon activity-icon-proposal';
  if (type.includes('workflow'))
    return 'activity-icon activity-icon-workflow';
  if (type.includes('connector'))
    return 'activity-icon activity-icon-connector';
  if (type.includes('connected'))
    return 'activity-icon activity-icon-connected';
  if (type.includes('error'))
    return 'activity-icon activity-icon-error';
  return 'activity-icon activity-icon-default';
}

export function ActivityFeed({ events }: ActivityFeedProps) {
  return (
    <div>
      <div className="page-header">
        <h2>Activity Feed</h2>
        <p>Real-time log of orchestrator events</p>
      </div>

      {events.length === 0 ? (
        <div className="empty-state">
          <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          <p>No activity yet</p>
          <p className="empty-subtitle">Events will appear here in real-time</p>
        </div>
      ) : (
        <div className="card" style={{ padding: '8px 16px' }}>
          {events.map((evt) => (
            <div key={evt.id} className="activity-item">
              <div className={iconClass(evt.type)}>
                <EventIcon type={evt.type} />
              </div>
              <div className="activity-body">
                <div className="activity-message">{evt.message}</div>
                <div className="activity-time">{formatTime(evt.timestamp)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
