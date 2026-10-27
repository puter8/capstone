"use client";

import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

import { IconMic } from "./icons";

type TalkCtaProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  label?: string;
};

/** Voice entry point: a 56px pill that mirrors the mic. One per screen. */
export function TalkCta({ label = "대화 시작하기", className, type = "button", ...props }: TalkCtaProps) {
  return (
    <button
      className={cn(
        "flex h-[56px] w-full items-center justify-center gap-p-2 rounded-p-full bg-p-primary text-p-button text-p-on-primary",
        "transition-[background-color,transform] duration-p-fast ease-p-out hover:bg-p-primary-hover active:scale-[0.98] active:bg-p-primary-pressed",
        "disabled:bg-p-disabled-bg disabled:text-p-disabled-text disabled:active:scale-100 motion-reduce:transition-none",
        className,
      )}
      type={type}
      {...props}
    >
      <IconMic size={22} />
      <span>{label}</span>
    </button>
  );
}
