"use client";

import { useEffect } from "react";

import type { UsageResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

export function formatResetDay(resetAt: string): string {
  const date = new Date(resetAt);
  if (Number.isNaN(date.getTime())) return "내일 0시에 다시 채워져요";
  const day = new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric", timeZone: "Asia/Seoul" }).format(date);
  const hour = Number(new Intl.DateTimeFormat("en-US", { hour: "numeric", hour12: false, timeZone: "Asia/Seoul" }).format(date)) % 24;
  return `${day} ${hour}시에 다시 채워져요`;
}

type UsagePopoverProps = {
  id: string;
  open: boolean;
  usage: UsageResponse;
  onClose: () => void;
  className?: string;
};

const MAX_METER_SEGMENTS = 20;

/** Today's usage, anchored under the usage chip. Escape or an outside tap closes it. */
export function UsagePopover({ id, open, usage, onClose, className }: UsagePopoverProps) {
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  // Pro has no daily limit, so there is no meter to draw.
  const dailyLimit = usage.daily_limit;
  const segments = dailyLimit === null ? 0 : Math.min(dailyLimit, MAX_METER_SEGMENTS);
  const filled = dailyLimit === null ? 0 : Math.round((usage.used_turns / Math.max(dailyLimit, 1)) * segments);

  return (
    <>
      <button aria-label="사용량 닫기" className="fixed inset-0 z-p-backdrop cursor-default bg-transparent" onClick={onClose} tabIndex={-1} type="button" />
      <section
        aria-label="오늘의 대화 사용량"
        className={cn(
          "absolute right-p-5 top-[68px] z-p-dialog flex w-[250px] flex-col gap-p-3 rounded-p-card border border-p-border bg-p-raised p-p-4 shadow-p-overlay",
          className,
        )}
        id={id}
        role="dialog"
      >
        <dl className="flex gap-p-6">
          <div className="flex flex-col gap-[2px]">
            <dd className="text-p-section tabular-nums text-p-text">{usage.used_turns}회</dd>
            <dt className="text-p-caption text-p-text-muted">사용</dt>
          </div>
          <div className="flex flex-col gap-[2px]">
            <dd className="text-p-section tabular-nums text-p-text">{usage.remaining_turns}회</dd>
            <dt className="text-p-caption text-p-text-muted">남음</dt>
          </div>
        </dl>
        {segments > 0 ? (
          <div aria-hidden="true" className="flex gap-p-1">
            {Array.from({ length: segments }, (_, index) => (
              <span className={cn("h-[6px] flex-1 rounded-[3px]", index < filled ? "bg-p-primary" : "bg-p-border")} key={index} />
            ))}
          </div>
        ) : null}
        <p className="text-p-caption text-p-text-secondary">{formatResetDay(usage.reset_at)}</p>
      </section>
    </>
  );
}
