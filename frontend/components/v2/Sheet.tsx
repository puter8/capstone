"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

import { cn } from "@/lib/utils";

type SheetProps = {
  open: boolean;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
  /** Action buttons, rendered in a column (primary first, then the text action). */
  actions: ReactNode;
  /** Escape and backdrop close the sheet. Turn off while an action is in flight. */
  onDismiss?: () => void;
  className?: string;
};

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Bottom sheet: raised panel, 24px top radius, grabber, title 22/30.
 * Accessible dialog: labelled, initial focus inside, focus trapped, Escape
 * closes when dismissible, focus returns to the opener on close.
 */
export function Sheet({ open, title, description, children, actions, onDismiss, className }: SheetProps) {
  const titleId = useId();
  const descriptionId = useId();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const openerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel)?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
      openerRef.current?.focus();
    };
  }, [open]);

  // Callback changes during typing must not interrupt focus or IME composition.
  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && onDismiss) {
        event.preventDefault();
        onDismiss();
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }
      const firstEl = focusable[0];
      const lastEl = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === firstEl) {
        event.preventDefault();
        lastEl.focus();
      } else if (!event.shiftKey && document.activeElement === lastEl) {
        event.preventDefault();
        firstEl.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onDismiss]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-p-backdrop flex items-end justify-center">
      <button
        aria-label="닫기"
        className="absolute inset-0 bg-p-overlay"
        disabled={!onDismiss}
        onClick={onDismiss}
        tabIndex={-1}
        type="button"
      />
      <div
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={cn(
          "relative z-p-dialog flex w-full max-w-p-content flex-col items-center gap-p-4 rounded-t-p-sheet bg-p-raised px-p-6 pt-p-2 shadow-p-overlay outline-none",
          "pb-[calc(var(--p-space-6)+env(safe-area-inset-bottom))]",
          "duration-p-sheet ease-p-out",
          className,
        )}
        ref={panelRef}
        role="dialog"
        tabIndex={-1}
      >
        <span aria-hidden="true" className="h-[4px] w-[36px] rounded-[2px] bg-p-border" />
        <div className="flex w-full flex-col gap-p-2">
          <h2 className="text-p-section text-p-text" id={titleId}>
            {title}
          </h2>
          {description ? (
            <p className="text-p-body text-p-text-secondary" id={descriptionId}>
              {description}
            </p>
          ) : null}
          {children}
        </div>
        <div className="flex w-full flex-col gap-p-1">{actions}</div>
      </div>
    </div>
  );
}
