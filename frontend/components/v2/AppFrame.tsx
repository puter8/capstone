import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type AppFrameProps = {
  children: ReactNode;
  className?: string;
  /** Reserve room for the floating bottom navigation (height + margin + safe area). */
  withBottomNav?: boolean;
  /** Reserve room for the conversation dock, which is sticky at the bottom. */
  withDock?: boolean;
};

/**
 * Page frame for the v2 design: centered column, 480px max, natural document
 * height. Pages lay out in flow (no absolute pixel positions) so text zoom and
 * small screens reflow instead of overlapping.
 */
export function AppFrame({ children, className, withBottomNav = false, withDock = false }: AppFrameProps) {
  return (
    <main
      className={cn(
        "relative mx-auto flex min-h-dvh w-full max-w-p-content flex-col",
        withBottomNav && "pb-[calc(70px+var(--p-space-6)+env(safe-area-inset-bottom))]",
        withDock && "pb-[env(safe-area-inset-bottom)]",
        className,
      )}
    >
      {children}
    </main>
  );
}
