"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, type ComponentType } from "react";

import { NAV_ITEMS, type NavItemId } from "@/lib/v2/routes";
import { cn } from "@/lib/utils";

import { IconBook, IconHome, IconProfile, IconTrophy, type IconProps } from "./icons";

const ICONS: Record<NavItemId, ComponentType<IconProps>> = {
  home: IconHome,
  history: IconBook,
  ranking: IconTrophy,
  my: IconProfile,
};

/**
 * Floating four-tab bar. The active tab is a filled pill in primary plus
 * aria-current, so the state never relies on color alone.
 */
export function BottomNav({ className }: { className?: string }) {
  const pathname = usePathname();
  const router = useRouter();

  // Keep dataKey for the existing route-data prefetch contract until cleanup.
  const prefetchTab = useCallback(
    (href: string, dataKey: string) => {
      router.prefetch(href);
      void import("@/lib/api/route-data")
        .then(({ prefetchRouteData }) => prefetchRouteData(dataKey))
        .catch((error: unknown) => {
          console.error("Tab data prefetch failed", { href, error });
        });
    },
    [router],
  );

  return (
    <nav
      aria-label="하단 내비게이션"
      className={cn(
        "fixed inset-x-0 z-p-nav mx-auto w-[calc(100%-var(--p-space-6))] max-w-[calc(var(--p-content-max)-var(--p-space-6))]",
        "bottom-[calc(var(--p-space-3)+env(safe-area-inset-bottom))]",
        className,
      )}
    >
      <ul className="flex gap-p-1 rounded-p-sheet border border-p-border bg-p-surface p-[6px]">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = ICONS[item.id];
          return (
            <li className="min-w-0 flex-1" key={item.id}>
              <Link
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-[56px] flex-col items-center justify-center gap-[2px] rounded-[18px] pb-[6px] pt-p-2 text-p-nav",
                  "transition-colors duration-p-fast ease-p-out motion-reduce:transition-none",
                  active ? "bg-p-primary-container text-p-primary" : "text-p-text-muted hover:text-p-text-secondary",
                )}
                href={item.href}
                onFocus={() => prefetchTab(item.href, item.dataKey)}
                onPointerEnter={() => prefetchTab(item.href, item.dataKey)}
                onTouchStart={() => prefetchTab(item.href, item.dataKey)}
              >
                <Icon />
                <span className="whitespace-nowrap">{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
