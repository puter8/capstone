"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { IconChevronRight } from "./icons";

type ListRowProps = {
  icon: ReactNode;
  label: string;
  /** Current value shown before the chevron (english level, plan). */
  value?: string;
  tone?: "default" | "danger";
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
};

/** 56px settings row inside a grouped card. The whole row is the control. */
export function ListRow({ icon, label, value, tone = "default", href, onClick, disabled, className }: ListRowProps) {
  const content = (
    <>
      <span className={cn("shrink-0", tone === "danger" ? "text-p-error" : "text-p-text-secondary")}>{icon}</span>
      <span className={cn("min-w-0 flex-1 text-left text-p-body", tone === "danger" ? "text-p-error" : "text-p-text")}>{label}</span>
      {value ? <span className="whitespace-nowrap text-p-small text-p-text-muted">{value}</span> : null}
      <IconChevronRight className="shrink-0 text-p-text-muted" size={20} />
    </>
  );
  const rowClass = cn(
    "flex h-[56px] w-full items-center gap-p-3 px-p-4 transition-colors duration-p-fast ease-p-out hover:bg-p-raised motion-reduce:transition-none",
    "disabled:opacity-60",
    className,
  );
  if (href && !disabled) {
    return (
      <Link className={rowClass} href={href}>
        {content}
      </Link>
    );
  }
  return (
    <button className={rowClass} disabled={disabled} onClick={onClick} type="button">
      {content}
    </button>
  );
}

/** Grouped settings card; rows are separated by hairlines. */
export function ListGroup({ children, className, label }: { children: ReactNode; className?: string; label: string }) {
  return (
    <section aria-label={label} className={cn("flex flex-col divide-y divide-p-border overflow-hidden rounded-[20px] bg-p-surface", className)}>
      {children}
    </section>
  );
}
