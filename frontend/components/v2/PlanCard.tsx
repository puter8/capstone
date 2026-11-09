"use client";

import type { BillingProduct } from "@/lib/api";
import { formatWon, planName } from "@/lib/billing-view";
import { cn } from "@/lib/utils";

type PlanCardProps = {
  product: BillingProduct;
  selected: boolean;
  disabled?: boolean;
  onSelect: () => void;
  className?: string;
};

export function intervalLabel(interval: BillingProduct["interval"]): string {
  return interval === "year" ? "1년마다" : "1개월마다";
}

export function recurringLabel(product: BillingProduct): string {
  return `${product.interval === "year" ? "연" : "월"} ${formatWon(product.amount_minor)}`;
}

/** Radio card for a billing product. Selected = container, 2px primary, filled radio. */
export function PlanCard({ product, selected, disabled, onSelect, className }: PlanCardProps) {
  return (
    <button
      aria-checked={selected}
      className={cn(
        "flex w-full items-center gap-p-3 rounded-p-card p-p-5 text-left transition-colors duration-p-fast ease-p-out motion-reduce:transition-none",
        selected ? "border-2 border-p-primary bg-p-primary-container" : "border border-p-border bg-p-surface hover:bg-p-raised",
        "disabled:opacity-60",
        className,
      )}
      disabled={disabled}
      onClick={onSelect}
      role="radio"
      tabIndex={selected ? 0 : -1}
      type="button"
    >
      <span
        aria-hidden="true"
        className={cn(
          "grid size-[22px] shrink-0 place-items-center rounded-p-full border-2",
          selected ? "border-p-primary" : "border-p-border-control",
        )}
      >
        {selected ? <span className="size-[10px] rounded-p-full bg-p-primary" /> : null}
      </span>
      <span className="flex min-w-0 flex-1 flex-col items-start gap-[6px]">
        <span className="text-p-card tracking-[-0.02em] text-p-text">{planName(product.id)}</span>
        <span className="rounded-p-sm bg-p-secondary-container px-p-2 py-[2px] text-p-eyebrow text-p-secondary">
          {product.trial_days > 0 ? `${product.trial_days}일 무료체험` : product.interval === "year" ? "매년 자동갱신" : "매월 자동갱신"}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end">
        <span className="text-p-section tabular-nums tracking-[-0.02em] text-p-text">{formatWon(product.amount_minor)}</span>
        <span className="text-p-caption text-p-text-muted">{intervalLabel(product.interval)}</span>
      </span>
    </button>
  );
}
