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

function eventIcon(type: string): string {
  if (type.includes('proposal:created')) return '[+]';
  if (type.includes('approved')) return '[v]';
  if (type.includes('rejected')) return '[x]';
  if (type.includes('workflow')) return '[~]';
  if (type.includes('connector')) return '[*]';
  if (type.includes('connected')) return '[.]';
  if (type.includes('error')) return '[!]';
  return '[-]';
}

export function ActivityFeed({ events }: ActivityFeedProps) {
  return (
    <div>
      <h2>Activity Feed</h2>

      {events.length === 0 ? (
        <div className="empty-state">
          <p>No activity yet</p>
          <p style={{ fontSize: 12, marginTop: 4 }}>
            Events will appear here in real-time
          </p>
        </div>
      ) : (
        <div className="card">
          {events.map((evt) => (
            <div key={evt.id} className="activity-item">
              <span className="activity-time">{formatTime(evt.timestamp)}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent)', width: 24 }}>
                {eventIcon(evt.type)}
              </span>
              <span>{evt.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
