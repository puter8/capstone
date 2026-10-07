"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { FeedbackItem } from "@/lib/api";
import { cn } from "@/lib/utils";

type InlineFeedbackPanelProps = {
  className?: string;
  feedback: readonly FeedbackItem[];
  onOpen: (item: FeedbackItem) => void;
};

export function InlineFeedbackPanel({ className, feedback, onOpen }: InlineFeedbackPanelProps) {
  const signature = useMemo(
    () => feedback.map((item) => item.id ?? `${item.original}:${item.corrected}`).join("|"),
    [feedback],
  );
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const explanationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setOpenIndex(null);
  }, [signature]);

  useEffect(() => {
    if (openIndex !== null) explanationRef.current?.scrollIntoView({ block: "nearest", behavior: "auto" });
  }, [openIndex]);

  // Feedback is generated after the conversation ends, so while it is pending there is
  // nothing to show here; History shows its own status. Rendering a notice only took
  // space from the message area and clipped Pally's reply.
  if (feedback.length === 0) return null;

  return (
    <section aria-label="이번 발화 피드백" className={cn("rounded-2xl bg-accent-soft p-3 text-left", className)}>
      {feedback.map((item, index) => {
        const open = openIndex === index;
        return (
          <div className={cn(index > 0 && "mt-2 border-t border-accent/20 pt-2")} key={item.id ?? `${item.original}-${index}`}>
            <button
              aria-expanded={open}
              className="flex min-h-11 w-full items-center justify-between gap-3 text-left"
              onClick={() => {
                const nextOpen = !open;
                setOpenIndex(nextOpen ? index : null);
                if (nextOpen) onOpen(item);
              }}
              type="button"
            >
              <span className="min-w-0 truncate text-body-2-sb text-accent-strong">{item.corrected}</span>
              <span className="shrink-0 text-caption-1 text-text-tertiary">{open ? "접기" : "피드백 보기"}</span>
            </button>
            {open ? (
              <div ref={explanationRef} className="mt-1 border-l-2 border-accent pl-3">
                <p className="text-caption-1 text-text-tertiary line-through">{item.original}</p>
                <p className="mt-1 text-body-2 text-text-secondary">{item.explanation_ko}</p>
              </div>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
