/**
 * Pally's look survives a reload, and nothing else gets painted as Pally.
 *
 * The route-data cache is in memory, so a cold start knew no axes and the home
 * screen waited three serial round trips before it could draw the character.
 * These assertions cover the stored value's round trip and, more importantly,
 * every way it can be wrong: the wrong account, truncated JSON, a shape from an
 * older build. Each of those must end as "no look yet", never as a half-valid
 * character, because the stage is what the user recognises as theirs.
 */
import { equal, deepEqual } from "node:assert/strict";
import { readFileSync } from "node:fs";

import { forgetRememberedAxes, peekRememberedAxes, rememberAxes } from "../lib/api/remembered-axes";
import type { Axes } from "../lib/types/character";

const AXES: Axes = { Formality: 72, Energy: 81, Intimacy: 64, Humor: 30, Curiosity: 95 };

let store: Record<string, string> = {};

function withBrowser(initial: Record<string, string> = {}): void {
  store = { ...initial };
  (globalThis as { window?: unknown }).window = {
    localStorage: {
      getItem: (key: string) => (key in store ? store[key] : null),
      setItem: (key: string, value: string) => { store[key] = value; },
      removeItem: (key: string) => { delete store[key]; },
    },
  };
}

const KEY = "pally:lastAxes";

// Nothing written yet: the stage has to wait for the profile.
withBrowser();
equal(peekRememberedAxes(), null, "an empty device remembers no look");

// The round trip a returning user depends on.
withBrowser();
rememberAxes("user-1", AXES);
deepEqual(peekRememberedAxes(), { userId: "user-1", axes: AXES }, "a stored look must come back intact");

// Non-default values specifically: storing a look that renders as the default
// yellow Pally would defeat the whole point.
const stored = peekRememberedAxes();
equal(stored?.axes.Curiosity, 95, "the stored look must keep the axis that sets Pally's colour");
equal(stored?.axes.Energy, 81, "the stored look must keep the axis that sets Pally's shape");

// Signing out clears it.
forgetRememberedAxes();
equal(peekRememberedAxes(), null, "forgetting must leave nothing behind");

// Truncated mid-write, or never JSON. Must not throw, must not keep retrying.
withBrowser({ [KEY]: '{"userId":"user-1","axes":{"Formality":5' });
equal(peekRememberedAxes(), null, "unparseable storage must not become a character");
equal(KEY in store, false, "unparseable storage must be discarded, not re-parsed every visit");

// Valid JSON in a shape this build does not understand.
withBrowser({ [KEY]: JSON.stringify({ userId: "user-1", axes: { Formality: 50 } }) });
equal(peekRememberedAxes(), null, "a partial axes object must not become a character");
equal(KEY in store, false, "a partial axes object must be discarded");

// Out of range: a value the renderer's tiers cannot place.
withBrowser({ [KEY]: JSON.stringify({ userId: "user-1", axes: { ...AXES, Curiosity: 140 } }) });
equal(peekRememberedAxes(), null, "an out-of-range axis must not become a character");

// No user attached: it cannot be checked against the session, so it is unusable.
withBrowser({ [KEY]: JSON.stringify({ axes: AXES }) });
equal(peekRememberedAxes(), null, "a look with no account must not be painted");

// A window whose localStorage is missing or throws: private browsing, blocked
// site data. Losing the paint hint is fine; taking the screen down is not.
(globalThis as { window?: unknown }).window = {};
equal(peekRememberedAxes(), null, "an unreachable store must read as no look, not throw");
rememberAxes("user-1", AXES);
forgetRememberedAxes();

(globalThis as { window?: unknown }).window = {
  get localStorage(): Storage { throw new Error("site data is blocked"); },
};
equal(peekRememberedAxes(), null, "a throwing store must read as no look");
rememberAxes("user-1", AXES);

// A store that accepts nothing, the way a full or locked-down one behaves.
(globalThis as { window?: unknown }).window = {
  localStorage: {
    getItem: () => null,
    setItem: () => { throw new Error("quota exceeded"); },
    removeItem: () => {},
  },
};
rememberAxes("user-1", AXES);

// Server render has no storage and must not claim a look.
delete (globalThis as { window?: unknown }).window;
equal(peekRememberedAxes(), null, "no window means no look to paint");

// The screen must actually use it, and must still hold the stage when it has
// nothing: the default axes are a different character from almost every user's.
const hook = readFileSync(new URL("../lib/hooks/useHomeConversation.ts", import.meta.url), "utf8");
for (const [needle, reason] of [
  ["peekRememberedAxes()", "the home hook must paint the remembered look"],
  ["rememberAxes(userId, revealedAxes)", "the profile read must store the look it just learned"],
  ["rememberAxes(userId, getAccumulatedAxes())", "ending a conversation must store Pally's new look"],
  ["forgetRememberedAxes()", "another account's look must be dropped on sight"],
] as const) {
  equal(hook.includes(needle), true, reason);
}

// The four home reads must go out together: the baseline gate used to sit alone
// in front of the profile read that decides Pally's look.
const gateIndex = hook.indexOf("const baseline = await baselinePromise");
const profileIndex = hook.indexOf("const profilePromise = loadProfile(userId)");
equal(profileIndex >= 0 && gateIndex > profileIndex, true, "the profile read must start before the baseline gate blocks");

console.log("remembered axes: PASS");
