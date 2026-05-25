'use client';

import { useEffect } from 'react';
import { cn } from '@/lib/utils';

// 4000ms per UI-SPEC § Interaction Timing — "long enough to read 1 Korean line
// at calm pace, short enough to clear before the user re-attempts".
const AUTO_DISMISS_MS = 4000;

export interface ToastProps {
  message: string;
  visible: boolean;
  onDismiss: () => void;
}

export function Toast({ message, visible, onDismiss }: ToastProps) {
  useEffect(() => {
    if (!visible) return;
    const t = window.setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => window.clearTimeout(t);
  }, [visible, onDismiss]);

  if (!visible) return null;

  return (
    <button
      type="button"
      onClick={onDismiss}
      className={cn(
        'block w-full max-w-[320px] mx-auto',
        'bg-surface-raised border border-border rounded-lg',
        'px-4 py-2',
        'text-body text-text-muted text-left',
        'shadow-lg',
        'transition-opacity duration-200',
      )}
      aria-live="polite"
    >
      {message}
    </button>
  );
}
