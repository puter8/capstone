"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { IconAlert } from "./icons";

type ToastProps = {
  message: string;
  tone?: "error" | "info";
  icon?: ReactNode;
  onDismiss: () => void;
  className?: string;
};

/**
 * Inline notice pinned under the top bar. Errors are alerts and stay until
 * dismissed; informational notices use role=status.
 */
export function Toast({ message, tone = "error", icon, onDismiss, className }: ToastProps) {
  return (
    <div className={cn("pointer-events-none fixed inset-x-0 z-p-toast flex justify-center px-p-5", className)}>
      <button
        aria-label={`${message} (닫기)`}
        className={cn(
          "pointer-events-auto flex w-full max-w-[calc(var(--p-content-max)-var(--p-space-10))] items-start gap-[10px] rounded-p-card py-[14px] pl-[14px] pr-p-4 text-left text-p-small text-p-text shadow-p-overlay",
          tone === "error" ? "bg-p-error-container" : "bg-p-info-container",
        )}
        onClick={onDismiss}
        role={tone === "error" ? "alert" : "status"}
        type="button"
      >
        <span className={cn("mt-px shrink-0", tone === "error" ? "text-p-error" : "text-p-info")}>{icon ?? <IconAlert size={20} />}</span>
        <span className="min-w-0 flex-1">{message}</span>
      </button>
    </div>
  );
}
