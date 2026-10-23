import type { Viewport } from "next";
import { Fraunces } from "next/font/google";

// Pretendard Variable with unicode-range subsets: only the glyph ranges a page
// uses are downloaded. Imported here, not in the root layout, so v1 keeps its budget.
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "@/styles/v2-tokens.css";

import { cn } from "@/lib/utils";

// Fraunces is reserved for short English content and numerals (see new-design.md §3).
// `axes` is only accepted together with weight "variable".
const fraunces = Fraunces({
  weight: "variable",
  style: ["normal", "italic"],
  subsets: ["latin"],
  axes: ["SOFT", "WONK", "opsz"],
  display: "swap",
  variable: "--font-fraunces",
});

// The root layout locks zoom for the v1 screens; v2 follows the accessibility
// baseline and lets users zoom. Nested viewport exports are shallow-merged, so
// both keys are set explicitly.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
};

export default function DesignV2Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div
      data-design="v2"
      className={cn(fraunces.variable, "min-h-dvh bg-p-bg font-p-ui text-p-text antialiased")}
    >
      {children}
    </div>
  );
}
