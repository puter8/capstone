import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type PrimaryButtonProps = ButtonHTMLAttributes<HTMLButtonElement>;

export function PrimaryButton({ children, className, disabled, ...props }: PrimaryButtonProps) {
  return (
    <button
      className={cn(
        "flex h-14 w-full items-center justify-center rounded-xl bg-primary transition-transform active:scale-[0.99] disabled:cursor-not-allowed disabled:bg-text-tertiary",
        className,
      )}
      disabled={disabled}
      {...props}
    >
      <span className="text-button-2-sb text-white">{children}</span>
    </button>
  );
}
