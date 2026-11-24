/**
 * Pally's last known look, kept across reloads.
 *
 * The route-data cache lives in memory, so a hard load has no axes and the home
 * screen has to wait three serial round trips (session, voice baseline, profile)
 * before it knows which character to draw. That left either a yellow stranger on
 * screen or an empty stage for up to a second and a half on every cold start.
 *
 * This is a paint hint, never a source of truth: the profile read still runs and
 * replaces it, and a value belonging to another account is dropped on sight.
 */
import { z } from "zod";

import { axesSchema } from "@/lib/api/schemas";
import type { Axes } from "@/lib/types/character";

const STORAGE_KEY = "pally:lastAxes";

const rememberedAxesSchema = z.object({
  userId: z.string().min(1),
  axes: axesSchema,
});

/**
 * localStorage, or null where it cannot be reached.
 *
 * Private-browsing modes and blocked site data leave it missing or make the
 * property itself throw. This is only a paint hint, so losing it costs the user
 * a spinner on the stage - never the conversation they are in the middle of
 * saving. That is why the write path below logs instead of throwing.
 */
function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage ?? null;
  } catch (error) {
    console.error("localStorage is unreachable; Pally's look will not persist", error);
    return null;
  }
}

// Truncated by a crash mid-write, or never JSON at all. The schema check below
// turns whatever this returns into a clean discard.
function parseStored(stored: string): unknown {
  try {
    return JSON.parse(stored);
  } catch (error) {
    console.error("Stored Pally axes are not JSON", error);
    return null;
  }
}

/**
 * The look to paint before the profile arrives, or null when there is none to
 * trust. Reading during render would be a hydration mismatch, so callers settle
 * this in an effect.
 */
export function peekRememberedAxes(): { userId: string; axes: Axes } | null {
  const store = storage();
  if (!store) return null;
  const stored = store.getItem(STORAGE_KEY);
  if (!stored) return null;
  const parsed = rememberedAxesSchema.safeParse(parseStored(stored));
  if (!parsed.success) {
    // Written by an older build, or edited by hand. Drop it rather than drawing
    // a half-valid character, and stop re-parsing it on every visit.
    console.error("Stored Pally axes are unusable; discarding them", parsed.error);
    store.removeItem(STORAGE_KEY);
    return null;
  }
  return parsed.data;
}

export function rememberAxes(userId: string, axes: Axes): void {
  const store = storage();
  if (!store) return;
  try {
    store.setItem(STORAGE_KEY, JSON.stringify({ userId, axes }));
  } catch (error) {
    // A full or blocked store must not take down the turn or the session end
    // that this is attached to: the next cold start just shows the spinner.
    console.error("Storing Pally's look failed", error);
  }
}

export function forgetRememberedAxes(): void {
  const store = storage();
  if (!store) return;
  store.removeItem(STORAGE_KEY);
}
