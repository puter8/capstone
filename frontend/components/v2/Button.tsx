"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

import { IconSpinner } from "./icons";

export type ButtonVariant = "primary" | "secondary" | "text" | "destructive";

type ButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  children: ReactNode;
  variant?: ButtonVariant;
  /** 52px default control height; compact keeps the 44px minimum target. */
  size?: "default" | "compact";
  fullWidth?: boolean;
  /** Replaces the label with the in-progress label and blocks repeat submits. */
  loading?: boolean;
  loadingLabel?: string;
  leadingIcon?: ReactNode;
};

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-p-primary text-p-on-primary hover:bg-p-primary-hover active:bg-p-primary-pressed disabled:bg-p-disabled-bg disabled:text-p-disabled-text",
  secondary:
    "border border-p-border-control bg-p-surface text-p-text hover:bg-p-raised disabled:border-transparent disabled:bg-p-disabled-bg disabled:text-p-disabled-text",
  text: "bg-transparent text-p-primary hover:bg-p-primary-container disabled:bg-p-disabled-bg disabled:text-p-disabled-text",
  destructive:
    "bg-p-error-container text-p-error hover:brightness-110 disabled:bg-p-disabled-bg disabled:text-p-disabled-text",
};

export function Button({
  children,
  className,
  variant = "primary",
  size = "default",
  fullWidth = false,
  loading = false,
  loadingLabel,
  leadingIcon,
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <button
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center gap-p-2 rounded-p-input px-p-5 py-p-3 font-p-ui text-p-button",
        "transition-[background-color,transform] duration-p-fast ease-p-out active:scale-[0.98] disabled:active:scale-100",
        "motion-reduce:transition-none motion-reduce:active:scale-100",
        size === "default" ? "min-h-p-control" : "min-h-p-target",
        fullWidth && "w-full",
        VARIANT_CLASSES[variant],
        className,
      )}
      disabled={isDisabled}
      type={type}
      {...props}
    >
      {loading ? <IconSpinner className="animate-spin motion-reduce:animate-none" size={20} /> : leadingIcon}
      <span className="min-w-0 text-center">{loading && loadingLabel ? loadingLabel : children}</span>
    </button>
  );
}
