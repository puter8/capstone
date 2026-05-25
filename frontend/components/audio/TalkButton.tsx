'use client';

import { cn } from '@/lib/utils';
import type { RecState } from '@/lib/state/conversation';

export interface TalkButtonProps {
  rec: RecState;
  disabled?: boolean;
  onPressStart: () => void;
  onPressStop: () => void;
}

// aria-labels per UI-SPEC § Copywriting Contract → Primary CTA (TalkButton).
const ARIA: Record<RecState['kind'], string> = {
  idle: '녹음 시작',
  recording: '녹음 정지',
  processing: '처리 중',
  speaking: 'Pally가 응답 중',
  error: '녹음 시작',
};

function MicIcon() {
  // 32x32 white mic icon — matches Figma TalkButton ComponentSet state=idle.
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3z"
        fill="#ffffff"
      />
      <path
        d="M5 11a7 7 0 0 0 14 0M12 18v3"
        stroke="#ffffff"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function StopIcon() {
  // 22x22 white rounded square (radius 6) — Figma state=thinking.
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="18" height="18" rx="6" fill="#ffffff" />
    </svg>
  );
}

export function TalkButton({ rec, disabled = false, onPressStart, onPressStop }: TalkButtonProps) {
  const isRecordingFamily =
    rec.kind === 'recording' || rec.kind === 'processing' || rec.kind === 'speaking';
  // Per D-12: only idle / error / recording are user-interactive. Processing /
  // speaking share the recording visual but the disc is disabled to prevent
  // double-fire of onPressStop while async work is in flight.
  const isInteractive =
    !disabled && (rec.kind === 'idle' || rec.kind === 'error' || rec.kind === 'recording');

  // Ring color: red family while recording/processing/speaking, otherwise orange.
  const ringClass = isRecordingFamily ? 'bg-error/[0.22]' : 'bg-primary/[0.18]';
  // Disc fill: red while recording-family, orange otherwise.
  const discClass = isRecordingFamily ? 'bg-error' : 'bg-primary';

  const handleClick = () => {
    if (!isInteractive) return;
    if (rec.kind === 'recording') {
      onPressStop();
    } else {
      onPressStart();
    }
  };

  return (
    <div className="relative flex items-center justify-center">
      {/* Decorative outer ring — 132x132, not a hit target */}
      <div
        aria-hidden="true"
        className={cn(
          'absolute rounded-full',
          'w-[132px] h-[132px]',
          ringClass,
        )}
      />
      {/* Primary disc — 96x96 hit target (w-24 h-24 = 96px per UI-SPEC § Spacing) */}
      <button
        type="button"
        aria-label={ARIA[rec.kind]}
        aria-disabled={!isInteractive}
        disabled={!isInteractive}
        onClick={handleClick}
        className={cn(
          'relative flex items-center justify-center',
          'w-24 h-24 rounded-full',
          discClass,
          'shadow-lg',
          // Press feedback: scale 0.95 over 150ms
          // (DESIGN.md § Motion "Mic press: scale 0.95, 150ms" + UI-SPEC § Interaction Timing).
          'transition-transform duration-150 active:scale-95',
          'disabled:cursor-default',
        )}
      >
        {isRecordingFamily ? <StopIcon /> : <MicIcon />}
      </button>
    </div>
  );
}
