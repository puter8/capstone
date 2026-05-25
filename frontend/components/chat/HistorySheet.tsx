'use client';

import { cn } from '@/lib/utils';
import type { Message } from '@/lib/types/message';
import { HistoryRow } from './HistoryRow';

export interface HistorySheetProps {
  open: boolean;
  messages: readonly Message[];
  onClose: () => void;
}

export function HistorySheet({ open, messages, onClose }: HistorySheetProps) {
  // Render nothing when closed — no hidden DOM with a11y trap.
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-label="대화 기록"
    >
      {/* Backdrop — tap to close */}
      <button
        type="button"
        onClick={onClose}
        aria-label="대화 기록 닫기"
        className="absolute inset-0 bg-black/30"
      />

      {/* Panel — slide-down from top, max height 605px so the 13px stripe peeks below */}
      <section
        className={cn(
          'relative mx-auto mt-0 w-full max-w-[402px]',
          'bg-surface-raised rounded-b-2xl',
          'shadow-xl',
          'flex flex-col',
          // 200ms ease-out per UI-SPEC § Interaction Timing.
          'transition-transform duration-200 ease-out',
        )}
        style={{ maxHeight: '605px' }}
      >
        {/* 4x40 drag handle (DESIGN.md decisions log 2026-05-25) */}
        <button
          type="button"
          onClick={onClose}
          aria-label="대화 기록 닫기"
          className="mx-auto mt-2 mb-1 h-1 w-10 rounded-full bg-text-muted/40"
        />

        {/* Scrollable message list */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {messages.length === 0 ? (
            <p className="text-body text-text-muted text-center py-8">
              아직 대화가 없어요
            </p>
          ) : (
            <ul className="flex flex-col">
              {messages.map((m) => (
                <li key={m.id}>
                  <HistoryRow message={m} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* 13px primary-soft stripe peeking under the panel (DESIGN.md 2026-05-25) */}
      <div
        aria-hidden="true"
        className="mx-auto w-full max-w-[402px] h-[13px] bg-primary-soft"
      />
    </div>
  );
}
