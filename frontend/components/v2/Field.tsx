"use client";

import { forwardRef, useId, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type FieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  label: string;
  /** Helper text under the input; replaced by the error when one is set. */
  hint?: string;
  error?: string | null;
};

/** Labelled text input, 52px, with the hint and error wired through aria-describedby. */
export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field({ label, hint, error, className, ...props }, ref) {
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className={cn("flex w-full flex-col gap-p-2", className)}>
      <label className="text-p-label text-p-text" htmlFor={id}>
        {label}
      </label>
      <input
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
        className={cn(
          "min-h-p-control w-full rounded-p-input border bg-p-surface px-p-4 py-p-3 text-p-body text-p-text placeholder:text-p-text-muted",
          error ? "border-p-error" : "border-p-border-control",
        )}
        id={id}
        ref={ref}
        {...props}
      />
      {error ? (
        <p className="text-p-small text-p-error" id={`${id}-error`} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-p-small text-p-text-secondary" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
    </div>
  );
});
