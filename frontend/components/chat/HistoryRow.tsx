'use client';

import { cn } from '@/lib/utils';
import type { Message } from '@/lib/types/message';

export interface HistoryRowProps {
  message: Message;
}

function formatTime(iso: string): string {
  // Hour:Minute, Korean locale. Defensive guard if iso invalid — surface, don't
  // silently fall back to "Invalid Date" (CLAUDE.md §7 error handling).
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return '';
  }
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

export function HistoryRow({ message }: HistoryRowProps) {
  const isUser = message.role === 'user';
  // Label color per UI-SPEC § Color reserved-for list: YOU=accent (teal), Pally=primary (orange).
  const labelClass = isUser ? 'text-accent' : 'text-primary';
  const labelText = isUser ? 'YOU' : 'Pally';

  return (
    <div
      className={cn(
        'flex flex-col gap-1 px-4 py-3',
        isUser ? 'items-start' : 'items-end',
      )}
    >
      <span className={cn('text-body-2-sb', labelClass)}>{labelText}</span>
      <p
        className={cn(
          'text-body text-text max-w-[280px]',
          isUser ? 'text-left' : 'text-right',
        )}
      >
        {message.transcript}
      </p>
      <span className="text-caption-1 text-text-muted">
        {formatTime(message.createdAt)}
      </span>
    </div>
  );
}
