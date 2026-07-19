import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type MobileShellProps = {
  children: ReactNode;
  className?: string;
};

export function MobileShell({ children, className }: MobileShellProps) {
  return (
    <main
      className={cn(
        "relative mx-auto min-h-[874px] w-full max-w-[402px] overflow-hidden bg-surface",
        className,
      )}
    >
      {children}
    </main>
  );
}
