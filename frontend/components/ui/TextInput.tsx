import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type TextInputProps = InputHTMLAttributes<HTMLInputElement>;

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      className={`${cn(
        "h-14 w-full rounded-2xl border-2 border-primary bg-white px-4 outline-none focus:ring-2 focus:ring-primary-soft",
        className,
      )} text-sm leading-5 text-text placeholder:text-text-tertiary`}
      ref={ref}
      type={type}
      {...props}
    />
  ),
);

TextInput.displayName = "TextInput";
