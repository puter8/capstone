"use client";

import Link from "next/link";

import type { ConversationListItem } from "@/lib/api";
import { formatClockTime, formatDurationMinutes } from "@/lib/v2/format";
import { cn } from "@/lib/utils";

import { IconArrowRight } from "./icons";
import { PallyThumb } from "./PallyThumb";

type SessionCardProps = {
  item: ConversationListItem;
  feedbackHref: string;
  /** The backend is still generating the title; show a placeholder bar. */
  titlePending?: boolean;
  onResume: () => void;
  resuming?: boolean;
  resumeError?: string | null;
  className?: string;
};

export function sessionTitle(item: Pick<ConversationListItem, "title" | "preview">): string {
  return item.title ?? item.preview ?? "Pally와 나눈 대화";
}

/**
 * Diary card for the history list. The title is a stretched link to the
 * feedback detail; "이어서 대화" is a sibling button, never nested inside it.
 */
export function SessionCard({ item, feedbackHref, titlePending = false, onResume, resuming = false, resumeError, className }: SessionCardProps) {
  const title = sessionTitle(item);
  const time = formatClockTime(item.started_at);
  const duration = formatDurationMinutes(item.started_at, item.last_turn_at ?? item.completed_at);
  const meta = [time, duration].filter(Boolean).join(" · ");

  return (
    <article className={cn("relative flex w-full flex-col gap-[6px] rounded-p-sheet bg-p-surface px-p-5 pb-p-3 pt-p-4", className)}>
      <div className="flex items-center gap-p-3">
        <p className="min-w-0 flex-1 text-p-eyebrow text-p-text-muted">{meta}</p>
        <PallyThumb axes={item.current_axes ?? undefined} size={32} />
      </div>
      {titlePending ? (
        <p aria-busy="true" className="flex h-[26px] items-center" role="status">
          <span className="sr-only">대화 제목을 만들고 있어요</span>
          <span aria-hidden="true" className="h-[14px] w-[150px] animate-pulse rounded-p-full bg-p-raised motion-reduce:animate-none" />
        </p>
      ) : (
        <h2 className="font-p-brand text-p-title-en-sm text-p-text [overflow-wrap:anywhere]" lang="en">
          <Link aria-label={`${title} 피드백 보기`} className="after:absolute after:inset-0 after:rounded-p-sheet after:content-['']" href={feedbackHref}>
            {title}
          </Link>
        </h2>
      )}
      {item.preview ? (
        <p className="truncate text-p-small text-p-text-secondary" lang="en">
          {item.preview}
        </p>
      ) : null}
      <div className="flex items-center gap-[6px] pt-p-1">
        <span className="rounded-p-full bg-p-raised px-[10px] py-p-1 text-p-eyebrow text-p-text-secondary">{item.turn_count}번 주고받음</span>
        {item.feedback_count > 0 ? (
          <span className="rounded-p-full bg-p-primary-container px-[10px] py-p-1 text-p-eyebrow text-p-primary">고친 표현 {item.feedback_count}개</span>
        ) : null}
        <span className="flex-1" />
        <button
          aria-busy={resuming || undefined}
          aria-label={`${title} 이어서 대화하기`}
          className="relative z-10 flex min-h-p-target items-center gap-p-1 pl-p-2 text-p-label text-p-primary disabled:text-p-disabled-text"
          disabled={resuming}
          onClick={onResume}
          type="button"
        >
          {resuming ? "재개하는 중…" : "이어서 대화"}
          <IconArrowRight size={16} />
        </button>
      </div>
      {resumeError ? (
        <p className="relative z-10 text-p-caption text-p-error" role="alert">
          {resumeError}
        </p>
      ) : null}
    </article>
  );
}

/** Loading placeholder with the card's real height. */
export function SessionCardSkeleton() {
  return (
    <div aria-hidden="true" className="flex w-full flex-col gap-[10px] rounded-p-sheet bg-p-surface px-p-5 pb-p-3 pt-p-4">
      <span className="h-[12px] w-[96px] rounded-p-full bg-p-raised" />
      <span className="h-[18px] w-[180px] rounded-p-full bg-p-raised" />
      <span className="h-[12px] w-full rounded-p-full bg-p-raised" />
      <span className="h-[24px] w-[200px] rounded-p-full bg-p-raised" />
    </div>
  );
}
