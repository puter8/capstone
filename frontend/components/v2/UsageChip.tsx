"use client";

import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type UsageChipProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  plan: "free" | "pro";
  /** Remaining turns today; ignored for Pro. */
  remaining: number;
  /** Home shows "오늘 N회 남음", the conversation top bar the shorter "N회 남음". */
  context?: "home" | "conversation";
  /** Id of the popover this chip toggles. */
  controls?: string;
  expanded?: boolean;
};

export function usageChipLabel(plan: "free" | "pro", remaining: number, context: "home" | "conversation"): string {
  if (plan === "pro") return "Pro · 무제한";
  if (remaining <= 0) return "오늘 남은 대화 없음";
  return context === "home" ? `오늘 ${remaining}회 남음` : `${remaining}회 남음`;
}

/** 36px pill inside a 44px hit area, per the top-bar touch-target rule. */
export function UsageChip({ plan, remaining, context = "home", controls, expanded, className, ...props }: UsageChipProps) {
  const label = usageChipLabel(plan, remaining, context);
  const exhausted = plan === "free" && remaining <= 0;
  const accessibleName = plan === "pro" ? "Pro 요금제, 대화 무제한, 자세히 보기" : `오늘 남은 대화 ${Math.max(remaining, 0)}회, 자세히 보기`;
  return (
    <button
      aria-controls={controls}
      aria-expanded={expanded}
      aria-label={accessibleName}
      className={cn("flex min-h-p-target items-center py-[4px]", className)}
      type="button"
      {...props}
    >
      <span className="flex h-[36px] items-center gap-p-2 rounded-p-full border border-p-border bg-p-surface pl-p-3 pr-[14px]">
        <span
          aria-hidden="true"
          className={cn("size-[6px] rounded-p-full", exhausted ? "bg-p-text-muted" : plan === "pro" ? "bg-p-secondary" : "bg-p-primary")}
        />
        <span className="whitespace-nowrap text-p-eyebrow text-p-text-secondary">{label}</span>
      </span>
    </button>
  );
}
