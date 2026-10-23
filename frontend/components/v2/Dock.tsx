"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

import { IconMic, IconMicOff, IconRotateCcw, IconSkipForward, IconSpinner, IconTranscript, IconVolume } from "./icons";

export type DockState = "ready" | "recording" | "processing" | "speaking" | "retry" | "disabled";

type DockProps = {
  state: DockState;
  onPressMic: () => void;
  onReplay: () => void;
  onToggleTranscript: () => void;
  transcriptOpen: boolean;
  /** Last reply audio is available to replay (current session only). */
  canReplay: boolean;
  replaying?: boolean;
  /** Recording start (ms epoch) for the elapsed arc; required while recording. */
  recordingStartedAt?: number | null;
  /** Elapsed recording time supplied by the caller instead of the internal clock. */
  elapsedMs?: number;
  /** Hide the replay and transcript buttons (onboarding uses the mic alone). */
  sideControls?: boolean;
  /** Auto-stop limit of the recorder, in ms. */
  maxRecordingMs: number;
  /** Overrides the default status line (e.g. a specific error). */
  statusText?: string;
  className?: string;
};

const STATUS_TEXT: Record<DockState, string> = {
  ready: "눌러서 말하기",
  recording: "듣고 있어요",
  processing: "답변을 준비하고 있어요",
  speaking: "Pally가 말하고 있어요 · 눌러서 건너뛰기",
  retry: "눌러서 다시 말하기",
  disabled: "오늘 무료 대화를 모두 썼어요",
};

const MIC_LABEL: Record<DockState, string> = {
  ready: "말하기 시작",
  recording: "녹음 끝내기",
  processing: "답변 준비 중",
  speaking: "Pally 말 건너뛰기",
  retry: "다시 말하기",
  disabled: "오늘 남은 대화 없음",
};

const RING_RADIUS = 46;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

function formatClock(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function useElapsed(startedAt: number | null | undefined, active: boolean): number {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!active || !startedAt) {
      setElapsed(0);
      return;
    }
    setElapsed(Date.now() - startedAt);
    const timer = window.setInterval(() => setElapsed(Date.now() - startedAt), 200);
    return () => window.clearInterval(timer);
  }, [active, startedAt]);
  return elapsed;
}

/**
 * All speaking controls in one place: replay, the 80px mic with its 8px ring,
 * and the transcript toggle. The status line is the single live region.
 */
export function Dock({
  state,
  onPressMic,
  onReplay,
  onToggleTranscript,
  transcriptOpen,
  canReplay,
  replaying = false,
  recordingStartedAt,
  elapsedMs,
  sideControls = true,
  maxRecordingMs,
  statusText,
  className,
}: DockProps) {
  const internalElapsed = useElapsed(recordingStartedAt, state === "recording" && elapsedMs === undefined);
  const elapsed = elapsedMs ?? internalElapsed;
  const progress = Math.min(1, maxRecordingMs > 0 ? elapsed / maxRecordingMs : 0);
  const replayHidden = state === "recording" || state === "speaking" || state === "disabled";
  const replayInert = replayHidden ? ({ inert: "" } as Record<string, string>) : {};
  // While a replay plays the center button is the skip control, so it stays enabled.
  const micDisabled = state === "processing" || state === "disabled";

  return (
    <div className={cn("flex w-full flex-col items-center gap-p-3 pb-p-6 pt-p-2", className)}>
      <div className="flex items-center gap-[28px]">
        {sideControls ? (
        <div className={cn(replayHidden && "invisible")} {...replayInert}>
          <button
            aria-label="Pally 말 다시 듣기"
            aria-pressed={replaying || undefined}
            className="grid size-[52px] place-items-center rounded-p-full border border-p-border bg-p-surface text-p-text-secondary disabled:text-p-disabled-text"
            disabled={!canReplay || state === "processing" || replaying}
            onClick={onReplay}
            type="button"
          >
            <IconVolume size={22} />
          </button>
        </div>
        ) : null}

        <div className="relative size-[96px]">
          {/* Outer ring: primary-container at rest, the elapsed arc while recording. */}
          <div
            aria-hidden="true"
            className={cn(
              "absolute inset-0 rounded-p-full",
              state === "speaking" ? "border border-p-border" : "bg-p-primary-container",
              (state === "processing" || state === "disabled") && "opacity-60",
            )}
          />
          {state === "recording" ? (
            <svg aria-hidden="true" className="absolute inset-0 -rotate-90" viewBox="0 0 96 96">
              <circle
                className="stroke-p-primary"
                cx="48"
                cy="48"
                fill="none"
                r={RING_RADIUS}
                strokeDasharray={RING_CIRCUMFERENCE}
                strokeDashoffset={RING_CIRCUMFERENCE * (1 - progress)}
                strokeLinecap="round"
                strokeWidth="3"
              />
            </svg>
          ) : null}
          <button
            aria-label={MIC_LABEL[state]}
            className={cn(
              "absolute left-1/2 top-1/2 grid size-p-mic -translate-x-1/2 -translate-y-1/2 place-items-center rounded-p-full",
              "transition-transform duration-p-fast ease-p-out active:scale-[0.98] disabled:active:scale-100 motion-reduce:transition-none",
              (state === "ready" || state === "retry" || state === "recording") && "bg-p-primary text-p-on-primary hover:bg-p-primary-hover active:bg-p-primary-pressed",
              state === "processing" && "bg-p-primary-container text-p-primary",
              state === "speaking" && "border-2 border-p-primary bg-p-raised text-p-primary",
              state === "disabled" && "bg-p-disabled-bg text-p-disabled-text",
            )}
            disabled={micDisabled}
            onClick={onPressMic}
            type="button"
          >
            {state === "ready" ? <IconMic size={28} /> : null}
            {state === "recording" ? <span aria-hidden="true" className="block size-[24px] rounded-[4px] bg-p-on-primary" /> : null}
            {state === "processing" ? <IconSpinner className="animate-spin motion-reduce:animate-none" size={28} /> : null}
            {state === "speaking" ? <IconSkipForward size={28} /> : null}
            {state === "retry" ? <IconRotateCcw size={28} /> : null}
            {state === "disabled" ? <IconMicOff size={28} /> : null}
          </button>
        </div>

        {sideControls ? (
        <button
          aria-expanded={transcriptOpen}
          aria-label="전체 대화 보기"
          className={cn(
            "grid size-[52px] place-items-center rounded-p-full border border-p-border bg-p-surface text-p-text-secondary",
            transcriptOpen && "border-p-primary text-p-primary",
          )}
          onClick={onToggleTranscript}
          type="button"
        >
          <IconTranscript size={22} />
        </button>
        ) : null}
      </div>

      <div className="flex min-h-[20px] items-center gap-p-2">
        {state === "recording" ? <span aria-hidden="true" className="size-[8px] rounded-p-full bg-p-error" /> : null}
        <p aria-live="polite" className={cn("text-p-label", state === "disabled" ? "text-p-text-muted" : "text-p-text-secondary")}>
          {statusText ?? STATUS_TEXT[state]}
        </p>
        {state === "recording" ? (
          <span aria-hidden="true" className="text-p-label font-medium tabular-nums text-p-text-muted">
            {formatClock(elapsed)} / {formatClock(maxRecordingMs)}
          </span>
        ) : null}
      </div>
    </div>
  );
}
