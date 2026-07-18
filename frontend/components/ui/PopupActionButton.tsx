import type { ButtonHTMLAttributes } from "react";

type PopupActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function PopupActionButton({ children, className = "", variant = "secondary", ...props }: PopupActionButtonProps) {
  return (
    <button
      className={`flex h-11 items-center justify-center rounded-full px-3 text-button-2 disabled:bg-text-tertiary disabled:text-white ${
        variant === "primary" ? "bg-primary text-white" : "border border-[#e4dfd5] bg-white text-text"
      } ${className}`}
      type="button"
      {...props}
    >
      {children}
    </button>
  );
}
