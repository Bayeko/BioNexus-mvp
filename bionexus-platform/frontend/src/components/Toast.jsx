/**
 * Lightweight toast notification context.
 *
 * Aligned with the refined-industrial aesthetic (no SaaS-purple
 * gradients, no marketing-grade animations) per the Labionexus brand
 * canonical. Three semantic variants — success, warning, error — each
 * with a discreet icon + accent border. Auto-dismiss after 4s, stack
 * up to 3 visible at once.
 *
 * Usage:
 *   import { useToast } from '../components/Toast';
 *   const { toast } = useToast();
 *   toast.success('Connection saved');
 *   toast.error('Vault returned 401');
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';

const ToastContext = createContext(null);

const MAX_VISIBLE = 3;
const DEFAULT_TTL_MS = 4000;

let toastIdCounter = 0;

function variantStyle(variant) {
  switch (variant) {
    case 'success':
      return {
        background: 'rgba(63, 185, 80, 0.08)',
        borderColor: 'rgba(63, 185, 80, 0.5)',
        color: '#7ce38b',
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M5 13l4 4L19 7" />
          </svg>
        ),
      };
    case 'warning':
      return {
        background: 'rgba(245, 158, 11, 0.08)',
        borderColor: 'rgba(245, 158, 11, 0.5)',
        color: '#fbbf24',
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 9v4M12 17h0M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
        ),
      };
    case 'error':
      return {
        background: 'rgba(239, 68, 68, 0.10)',
        borderColor: 'rgba(239, 68, 68, 0.55)',
        color: '#fca5a5',
        icon: (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        ),
      };
    default:
      return {
        background: 'rgba(99, 102, 241, 0.08)',
        borderColor: 'rgba(99, 102, 241, 0.4)',
        color: '#a5b4fc',
        icon: null,
      };
  }
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((variant, message) => {
    const id = ++toastIdCounter;
    setToasts((prev) => {
      const next = [...prev, { id, variant, message }];
      return next.length > MAX_VISIBLE ? next.slice(-MAX_VISIBLE) : next;
    });
  }, []);

  const toast = React.useMemo(
    () => ({
      success: (msg) => push('success', msg),
      warning: (msg) => push('warning', msg),
      error: (msg) => push('error', msg),
      info: (msg) => push('info', msg),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={{ toast, dismiss }}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }) {
  const style = variantStyle(toast.variant);
  useEffect(() => {
    const timer = setTimeout(onDismiss, DEFAULT_TTL_MS);
    return () => clearTimeout(timer);
  }, [onDismiss]);
  return (
    <div
      className="toast-item"
      style={{
        background: style.background,
        borderColor: style.borderColor,
        color: style.color,
      }}
      onClick={onDismiss}
    >
      {style.icon && <span className="toast-icon">{style.icon}</span>}
      <span className="toast-message">{toast.message}</span>
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // No-op shim so the hook never crashes outside a provider (e.g. unit tests)
    return {
      toast: {
        success: () => {},
        warning: () => {},
        error: () => {},
        info: () => {},
      },
      dismiss: () => {},
    };
  }
  return ctx;
}
