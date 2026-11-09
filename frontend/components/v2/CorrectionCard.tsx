"use client";

import { useEffect, useRef } from "react";

import type { FeedbackItem } from "@/lib/api";
import { locateEdits, spliceEdits } from "@/lib/feedback-sentence";
import { cn } from "@/lib/utils";

type CorrectionCardProps = {
  index: number;
  utterance: string | null;
  items: readonly FeedbackItem[];
  /** Fires once when the card scrolls into view. */
  onOpen?: () => void;
  className?: string;
};

/**
 * One utterance and every correction made to it. Changed words are a muted
 * <del>, replacements an underlined lilac <ins>; the error color is never used
 * for the learner's English.
 */
export function CorrectionCard({ index, utterance, items, onOpen, className }: CorrectionCardProps) {
  const ref = useRef<HTMLElement | null>(null);
  const openedRef = useRef(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || !onOpen) return;
    const observer = new IntersectionObserver((entries) => {
      if (openedRef.current || !entries.some((entry) => entry.isIntersecting)) return;
      openedRef.current = true;
      onOpen();
      observer.disconnect();
    }, { threshold: 0.5 });
    observer.observe(node);
    return () => observer.disconnect();
  }, [onOpen]);

  const edits = utterance ? locateEdits(utterance, items) : [];
  // Only fixes written in the user's own words can be placed back into the sentence.
  const fixes = edits.filter((edit) => edit.item.replacement);
  const fixed = new Set(fixes.map((edit) => edit.item));
  const showPairs = items.length > 1;

  return (
    <article className={cn("flex w-full flex-col gap-p-3 rounded-p-card bg-p-surface p-p-5", className)} ref={ref}>
      <header className="flex items-center gap-p-2 text-p-eyebrow text-p-primary">
        <span aria-hidden="true" className="grid size-[24px] place-items-center rounded-p-full bg-p-primary-container">
          {index}
        </span>
        <h2>
          <span className="sr-only">{index}번째 </span>고친 표현
        </h2>
      </header>
      <div className="flex flex-col gap-[2px]">
        <p className="text-p-caption text-p-text-muted">내가 한 말</p>
        <p className="whitespace-pre-wrap text-p-body text-p-text-muted [overflow-wrap:anywhere]" lang="en">
          {utterance
            ? spliceEdits(utterance, edits, (edit) => (
                <del className="decoration-p-text-muted" key={edit.start}>{utterance.slice(edit.start, edit.end)}</del>
              ))
            : items.map((item) => item.original).join(" / ")}
        </p>
      </div>
      <div className="flex flex-col gap-[2px]">
        <p className="text-p-caption text-p-text-muted">더 자연스럽게</p>
        <p className="whitespace-pre-wrap text-p-body text-p-text [overflow-wrap:anywhere]" lang="en">
          {utterance && fixes.length > 0
            ? spliceEdits(utterance, fixes, (edit) => (
                <ins className="font-semibold text-p-primary underline decoration-solid underline-offset-4" key={edit.start}>{edit.item.replacement}</ins>
              ))
            : items.map((item, itemIndex) => (
                <ins className="font-semibold text-p-primary underline decoration-solid underline-offset-4" key={itemIndex}>
                  {itemIndex > 0 ? " / " : ""}{item.corrected}
                </ins>
              ))}
        </p>
      </div>
      {items.some((item) => item.explanation_ko.trim()) ? (
        <>
          <hr className="border-0 border-t border-p-border" />
          <div className="flex flex-col gap-p-1">
            {items.map((item, itemIndex) => (item.explanation_ko.trim() ? (
              <p className="whitespace-pre-wrap text-p-small text-p-text-secondary" key={itemIndex}>
                {showPairs ? (
                  <span className="font-semibold" lang="en">{item.original} → {fixed.has(item) ? item.replacement : item.corrected}: </span>
                ) : null}
                {item.explanation_ko}
              </p>
            ) : null))}
          </div>
        </>
      ) : null}
    </article>
  );
}
