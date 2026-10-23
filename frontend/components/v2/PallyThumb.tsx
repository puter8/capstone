"use client";

import { useEffect, useRef, useState } from "react";

import PallyCanvas from "@/components/pally/PallyCanvas";
import { DEFAULT_AXES, type Axes } from "@/lib/types/character";
import { cn } from "@/lib/utils";

// One snapshot per distinct look; cards that share axes share the image.
const snapshotCache = new Map<string, string>();
const CAPTURE_SIZE = 128;
const MAX_CAPTURE_ATTEMPTS = 12;

type PallyThumbProps = {
  axes?: Axes | null;
  size?: number;
  className?: string;
};

/**
 * Small still of Pally for list cards. PallyCanvas is built for the stage
 * (fixed glow, bobbing, one animation loop per instance), so the thumb renders
 * it once off-screen, snapshots the canvas and shows the image instead.
 */
export function PallyThumb({ axes, size = 32, className }: PallyThumbProps) {
  const resolvedAxes = axes ?? DEFAULT_AXES;
  const key = JSON.stringify(resolvedAxes);
  const [src, setSrc] = useState<string | null>(() => snapshotCache.get(key) ?? null);
  const hostRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    const cached = snapshotCache.get(key);
    if (cached) {
      setSrc(cached);
      return;
    }
    let cancelled = false;
    let attempts = 0;
    let frame = 0;
    const capture = () => {
      if (cancelled) return;
      const canvas = hostRef.current?.querySelector("canvas");
      // The first frames can be empty while the renderer sets up; retry briefly.
      if (canvas && canvas.width > 0 && attempts >= 2) {
        try {
          const url = canvas.toDataURL("image/png");
          snapshotCache.set(key, url);
          setSrc(url);
          return;
        } catch (error) {
          console.error("Pally thumbnail capture failed", error);
          return;
        }
      }
      attempts += 1;
      if (attempts <= MAX_CAPTURE_ATTEMPTS) frame = requestAnimationFrame(capture);
    };
    frame = requestAnimationFrame(capture);
    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
    };
  }, [key]);

  return (
    <span className={cn("relative inline-block shrink-0", className)} style={{ width: size, height: size }}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element -- data URL snapshot, not an optimizable asset
        <img alt="" className="size-full object-contain" height={size} src={src} width={size} />
      ) : (
        <span aria-hidden="true" className="pointer-events-none absolute left-0 top-0 opacity-0" ref={hostRef} style={{ width: CAPTURE_SIZE, height: CAPTURE_SIZE }}>
          <PallyCanvas axes={resolvedAxes} size={CAPTURE_SIZE} />
        </span>
      )}
    </span>
  );
}
