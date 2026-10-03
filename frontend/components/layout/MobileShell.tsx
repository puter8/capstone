import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type MobileShellProps = {
  children: ReactNode;
  className?: string;
  /** Lowest viewport height (px) at which this screen's layout fits without overlap. Defaults to the 874px Figma frame. */
  minHeight?: number;
};

export function MobileShell({ children, className, minHeight = 874 }: MobileShellProps) {
  return (
    <main
      className={cn(
        "relative mx-auto min-h-[874px] w-full max-w-[402px] overflow-hidden bg-surface",
        className,
      )}
      style={{ minHeight: `max(100dvh, ${minHeight}px)` }}
    >
      {children}
    </main>
  );
}
