"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { IconChevronLeft, IconX } from "./icons";

export type ConversationStatus = "speaking" | "listening" | "idle" | "processing" | "closing";

const STATUS_LABEL: Record<ConversationStatus, string> = {
  speaking: "말하는 중",
  listening: "듣는 중",
  idle: "내 차례",
  processing: "답변 준비 중",
  closing: "저장 중",
};

const STATUS_DOT: Record<ConversationStatus, string> = {
  speaking: "bg-p-primary",
  listening: "bg-p-error",
  idle: "bg-p-secondary",
  processing: "bg-p-text-muted",
  closing: "bg-p-text-muted",
};

type BackTopBarProps = {
  variant: "back";
  title: string;
  /** Visually hide the title (onboarding steps keep it for screen readers). */
  hideTitle?: boolean;
  /** Navigate with a link when given; otherwise call onBack. */
  backHref?: string;
  onBack?: () => void;
  /** Hide the back control but keep its space (first onboarding step). */
  backHidden?: boolean;
  trailing?: ReactNode;
};

type ConversationTopBarProps = {
  variant: "conversation";
  status: ConversationStatus;
  onEnd: () => void;
  endDisabled?: boolean;
  trailing?: ReactNode;
};

type TopBarProps = (BackTopBarProps | ConversationTopBarProps) & { className?: string };

export function TopBar(props: TopBarProps) {
  if (props.variant === "conversation") {
    const { status, onEnd, endDisabled, trailing, className } = props;
    return (
      <header className={cn("flex h-[64px] w-full items-center px-p-4", className)}>
        <button
          aria-label="대화 종료"
          className="flex min-h-p-target items-center py-[4px] disabled:opacity-60"
          disabled={endDisabled}
          onClick={onEnd}
          type="button"
        >
          <span className="flex h-[36px] items-center gap-p-1 rounded-p-full bg-p-raised pl-[10px] pr-[14px] text-p-text-secondary">
            <IconX size={18} />
            <span className="whitespace-nowrap text-p-label">대화 종료</span>
          </span>
        </button>
        <div className="flex min-w-0 flex-1 flex-col items-center">
          <span
            className="font-p-brand text-p-title-en-sm text-p-text"
            lang="en"
            style={{ fontVariationSettings: '"SOFT" 0, "WONK" 1' }}
          >
            Pally
          </span>
          {/* The dock's status line is the live region; this one is decorative. */}
          <span aria-hidden="true" className="flex items-center gap-[6px]">
            <span className={cn("size-[6px] rounded-p-full", STATUS_DOT[status])} />
            <span className="whitespace-nowrap text-p-caption text-p-text-secondary">{STATUS_LABEL[status]}</span>
          </span>
        </div>
        <div className="flex min-w-[44px] justify-end">{trailing}</div>
      </header>
    );
  }

  const { title, hideTitle, backHref, onBack, backHidden, trailing, className } = props;
  const backClass = "grid size-p-target place-items-center rounded-p-full text-p-text";
  const inertProps = backHidden ? ({ inert: "" } as Record<string, string>) : {};
  return (
    <header className={cn("flex h-[56px] w-full items-center px-p-2", className)}>
      <div className={cn(backHidden && "invisible")} {...inertProps}>
        {backHref ? (
          <Link aria-label="뒤로 가기" className={backClass} href={backHref}>
            <IconChevronLeft />
          </Link>
        ) : (
          <button aria-label="뒤로 가기" className={backClass} onClick={onBack} type="button">
            <IconChevronLeft />
          </button>
        )}
      </div>
      <h1 className={cn("min-w-0 flex-1 text-center text-p-button text-p-text", hideTitle && "sr-only")}>{title}</h1>
      <div className="flex min-w-[44px] justify-end">{trailing}</div>
    </header>
  );
}
