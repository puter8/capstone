"use client";

import PallyCanvas, { type PallyGaze } from "@/components/pally/PallyCanvas";
import type { Axes } from "@/lib/types/character";
import { cn } from "@/lib/utils";

export type StageState = "idle" | "speaking" | "listening" | "thinking";

type StageProps = {
  axes?: Axes;
  size?: "large" | "compact";
  state?: StageState;
  /** The lilac light behind Pally. Off on login, loading, error and empty screens. */
  glow?: boolean;
  className?: string;
};

const GLOW_OPACITY_VAR: Record<StageState, string> = {
  idle: "var(--p-stage-glow-idle)",
  speaking: "var(--p-stage-glow-speaking)",
  listening: "var(--p-stage-glow-listening)",
  thinking: "var(--p-stage-glow-thinking)",
};

const DIMENSIONS = {
  large: { height: "h-[280px]", glow: "h-[210px] w-[270px]", character: 176, rings: ["size-[220px]", "size-[268px]"] },
  compact: { height: "h-[184px]", glow: "h-[140px] w-[220px]", character: 112, rings: ["size-[156px]", "size-[204px]"] },
} as const;

/**
 * Pally on stage. The conversation state changes only the light and the rings
 * around the character, never the character itself, which is the live
 * PallyCanvas render of the user's current axes.
 */
export function Stage({ axes, size = "large", state = "idle", glow = true, className }: StageProps) {
  const dims = DIMENSIONS[size];
  const gaze: PallyGaze = state === "thinking" ? "up-right" : "center";
  return (
    <div className={cn("relative mx-auto w-full max-w-[320px]", dims.height, className)} data-stage-state={state}>
      {glow ? (
        <div
          aria-hidden="true"
          className={cn(
            "pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-p-full bg-p-primary blur-[48px]",
            "transition-opacity duration-p-sheet ease-p-out motion-reduce:transition-none",
            dims.glow,
          )}
          style={{ opacity: GLOW_OPACITY_VAR[state] }}
        />
      ) : null}
      {state === "speaking"
        ? dims.rings.map((ring, index) => (
            <div
              aria-hidden="true"
              className={cn(
                "pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-p-full border border-p-primary",
                index === 0 ? "opacity-30" : "opacity-15",
                ring,
              )}
              key={ring}
            />
          ))
        : null}
      <div
        className={cn(
          "absolute left-1/2 -translate-x-1/2 -translate-y-1/2 transition-[top] duration-p-standard ease-p-out motion-reduce:transition-none",
          state === "thinking" ? "top-[calc(50%-10px)]" : "top-1/2",
        )}
      >
        <PallyCanvas axes={axes} gaze={gaze} size={dims.character} />
      </div>
    </div>
  );
}
