'use client';

import { cn } from '@/lib/utils';
import type { Message } from '@/lib/types/message';

export interface ChatBubbleProps {
  messages: readonly Message[];
  historyOpen: boolean;
  onToggleHistory: () => void;
}

function SenderLabel({ role }: { role: Message['role'] }) {
  if (role === 'user') {
    return <span className="text-accent text-body-2-sb">YOU</span>;
  }
  return <span className="text-primary text-body-2-sb">Pally</span>;
}

function Chevron({ open }: { open: boolean }) {
  // 16x16 chevron — down when closed (open=false), up when open=true.
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      aria-hidden="true"
      className={cn(
        'transition-transform duration-200',
        open ? 'rotate-180' : 'rotate-0',
      )}
    >
      {/* #6b7280 = text-muted token — SVG stroke attr cannot reference Tailwind tokens */}
      <path
        d="M3 6l5 5 5-5"
        stroke="#6b7280"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export function ChatBubble({
  messages,
  historyOpen,
  onToggleHistory,
}: ChatBubbleProps) {
  const isEmpty = messages.length === 0;
  // Last Pally reply is the latest entry; last user turn is the one before.
  const lastPally = !isEmpty ? messages.at(-1) : undefined;
  const lastUser = !isEmpty ? messages.at(-2) : undefined;

  return (
    <section
      className={cn(
        'mx-auto w-full max-w-[370px]',
        'bg-surface-raised rounded-2xl border border-border',
        'px-4 py-3',
        'shadow-sm',
      )}
      aria-label="대화"
    >
      {isEmpty ? (
        // Empty state per UI-SPEC Copywriting Contract — two <p> for screen-reader correctness.
        <div className="py-6 text-center">
          <p className="text-title-1 text-text">오늘은 어떤 이야기를 해볼까요?</p>
          <p className="text-body text-text-muted mt-2">
            마이크를 눌러 영어로 말해보세요
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {lastUser && lastUser.role === 'user' && (
            <p className="text-body text-text">
              <SenderLabel role="user" />
              <span className="ml-2">{lastUser.transcript}</span>
            </p>
          )}
          {lastPally && lastPally.role === 'pally' && (
            <p className="text-subtitle-sb text-text">
              <SenderLabel role="pally" />
              <span className="ml-2">{lastPally.transcript}</span>
            </p>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={onToggleHistory}
        aria-label={historyOpen ? '대화 기록 닫기' : '대화 기록 열기'}
        aria-expanded={historyOpen}
        className="mx-auto mt-2 flex items-center justify-center w-full h-6 rounded-md hover:bg-surface"
      >
        <Chevron open={historyOpen} />
      </button>
    </section>
  );
}
