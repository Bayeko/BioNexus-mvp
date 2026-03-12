import React, { useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../api';

interface ProposalChatProps {
  chatHistory: ChatMessage[];
  onSend: (message: string) => Promise<void>;
  onRevise: () => Promise<void>;
  isPending: boolean;
}

function formatTime(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function ProposalChat({ chatHistory, onSend, onRevise, isPending }: ProposalChatProps) {
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [revising, setRevising] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput('');
    setSending(true);
    try {
      await onSend(text);
    } finally {
      setSending(false);
    }
  };

  const handleRevise = async () => {
    setRevising(true);
    try {
      await onRevise();
    } finally {
      setRevising(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {chatHistory.length === 0 && (
          <div className="chat-empty">
            Ask questions about this proposal before deciding
          </div>
        )}
        {chatHistory.map((msg, i) => (
          <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
            <div className="chat-msg-header">
              <span className="chat-msg-role">
                {msg.role === 'user' ? 'You' : 'Claude'}
              </span>
              <span className="chat-msg-time">{formatTime(msg.timestamp)}</span>
            </div>
            <div className="chat-msg-content">{msg.content}</div>
          </div>
        ))}
        {sending && (
          <div className="chat-msg chat-msg-assistant">
            <div className="chat-msg-header">
              <span className="chat-msg-role">Claude</span>
            </div>
            <div className="chat-msg-content chat-typing">Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {isPending && (
        <div className="chat-input-area">
          <div className="chat-input-row">
            <textarea
              className="input chat-input"
              placeholder="Ask about this proposal..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={sending}
            />
            <button
              className="btn btn-primary"
              onClick={handleSend}
              disabled={sending || !input.trim()}
            >
              Send
            </button>
          </div>
          {chatHistory.length > 0 && (
            <button
              className="btn btn-revise"
              onClick={handleRevise}
              disabled={revising}
            >
              {revising ? 'Revising...' : 'Revise Proposal'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
