import { deepEqual, equal } from "node:assert/strict";

import type { ProfileResponse, UsageQuota } from "../lib/api/contracts";
import type { Axes } from "../lib/types/character";

const OLD_AXES: Axes = { Formality: 50, Energy: 30, Intimacy: 20, Humor: 10, Curiosity: 15 };
const NEW_AXES: Axes = { Formality: 54, Energy: 41, Intimacy: 30, Humor: 8, Curiosity: 22 };

async function main(): Promise<void> {
  // route-data imports the Supabase client, which needs these at import time.
  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://fixture.supabase.invalid";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "fixture-public-anon-key";
  const route = await import("../lib/api/route-data");

  const profile: ProfileResponse = {
    profile: {
      id: "user-1",
      display_name: "Claire",
      english_level: "B2",
      onboarding_completed: true,
      traits: ["acquaint", "serious", "calm", "indifferent", "casual"],
      avatar_url: null,
      created_at: "2026-10-06T00:00:00Z",
      updated_at: "2026-10-06T00:00:00Z",
      current_axes: OLD_AXES,
    },
  };
  const quota: UsageQuota = { used_turns: 3, remaining_turns: 17, daily_limit: 20, exhausted: false, resets_at: "2026-10-07T00:00:00+09:00" };

  equal(route.peekHomeSnapshot(), null, "no remembered user means no snapshot");
  route.rememberUser("user-1");
  route.cacheProfile("user-1", profile);
  equal(route.peekHomeSnapshot(), null, "profile alone is not enough to paint home");

  route.patchStaleUsage("user-1", quota);
  const first = route.peekHomeSnapshot();
  equal(first?.userId, "user-1");
  deepEqual(first?.profile.current_axes, OLD_AXES);
  equal(first?.usage.remaining_turns, 17, "a turn's quota seeds the stale usage");
  equal(first?.usage.plan, "free");
  equal(first?.subscription, null);

  route.invalidateProfile("user-1");
  route.patchStaleProfileAxes("user-1", NEW_AXES);
  const afterConversation = route.peekHomeSnapshot();
  deepEqual(afterConversation?.profile.current_axes, NEW_AXES, "ending a conversation shows the new look immediately");
  equal(afterConversation?.profile.display_name, "Claire", "other profile fields are kept");

  route.invalidateUsage("user-1");
  equal(route.peekHomeSnapshot(), null, "a plan change must not paint the old usage");

  route.patchStaleUsage("user-1", { ...quota, remaining_turns: null, daily_limit: null });
  equal(route.peekHomeSnapshot()?.usage.plan, "pro", "unlimited quota means the pro plan");

  route.clearUserRouteData("user-1");
  equal(route.peekHomeSnapshot(), null, "logout and deletion drop the snapshot and the remembered user");
  route.patchStaleUsage("user-1", quota);
  equal(route.peekHomeSnapshot(), null, "a cleared user is no longer remembered");

  route.rememberUser("user-2");
  route.forgetRememberedUser();
  equal(route.peekHomeSnapshot(), null, "forgetting the user disables the snapshot");
  console.log("Home snapshot checks passed.");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
