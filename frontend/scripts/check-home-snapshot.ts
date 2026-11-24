import { deepEqual, equal } from "node:assert/strict";

import type { ProfileResponse, Subscription, UsageQuota } from "../lib/api/contracts";
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
  const nextReset = new Date(Date.now() + 60 * 60 * 1000).toISOString();
  const pastReset = new Date(Date.now() - 1_000).toISOString();
  const quota: UsageQuota = { used_turns: 3, remaining_turns: 17, daily_limit: 20, exhausted: false, resets_at: nextReset };
  const freePlan: Subscription = {
    plan: "free", status: "none", entitled: false, product_id: null,
    current_period_end: null, will_renew: false, entitlements: [], updated_at: null,
  };
  const proPlan: Subscription = {
    ...freePlan, plan: "pro", status: "active", entitled: true, product_id: "pro_monthly",
    current_period_end: "2026-12-01T00:00:00Z", will_renew: true, entitlements: ["pro"],
  };

  equal(route.peekHomeSnapshot(), null, "no remembered user means no snapshot");
  route.rememberUser("user-1");
  route.cacheProfile("user-1", profile);
  const withoutUsage = route.peekHomeSnapshot();
  equal(withoutUsage?.userId, "user-1", "the profile is enough to paint home");
  equal(withoutUsage?.usage, null, "unknown usage is left out instead of blocking the screen");

  route.cacheTurnUsage("user-1", quota);
  const first = route.peekHomeSnapshot();
  equal(first?.userId, "user-1");
  deepEqual(first?.profile.current_axes, OLD_AXES);
  equal(first?.usage?.remaining_turns, 17, "a turn's quota seeds the stale usage");
  equal(first?.usage?.plan, "free");
  equal(first?.subscription, null);

  route.invalidateProfile("user-1");
  route.patchStaleProfileAxes("user-1", NEW_AXES);
  const afterConversation = route.peekHomeSnapshot();
  deepEqual(afterConversation?.profile.current_axes, NEW_AXES, "ending a conversation shows the new look immediately");
  equal(afterConversation?.profile.display_name, "Claire", "other profile fields are kept");

  route.invalidateUsage("user-1");
  equal(route.peekHomeSnapshot()?.usage, null, "a plan change must not paint the old usage");

  route.cacheTurnUsage("user-1", { ...quota, remaining_turns: null, daily_limit: null });
  equal(route.peekHomeSnapshot()?.usage?.plan, "pro", "unlimited quota means the pro plan");

  // The daily count resets at reset_at: a value from before it is known to be wrong.
  route.cacheTurnUsage("user-1", { ...quota, remaining_turns: 0, exhausted: true, resets_at: pastReset });
  equal(route.peekHomeSnapshot()?.usage, null, "usage from before the daily reset is not painted");
  equal(route.isUsageCurrent({ ...route.usageFromQuota(null, quota), reset_at: "not a date" }), false, "an unreadable reset time is not trusted");

  // Reading the billing screen keeps usage unless the plan really changed.
  const { pallyApi } = await import("../lib/api");
  pallyApi.getSubscription = async () => ({ subscription: freePlan });
  route.cacheTurnUsage("user-1", quota);
  route.syncSubscription("user-1", freePlan);
  equal(route.peekHomeSnapshot()?.usage, null, "with no cached subscription there is nothing to compare, so usage is dropped");

  await route.loadSubscription("user-1");
  route.cacheTurnUsage("user-1", quota);
  route.syncSubscription("user-1", { ...freePlan, updated_at: "2026-11-19T00:00:00Z" });
  equal(route.peekHomeSnapshot()?.usage?.remaining_turns, 17, "an unchanged plan keeps usage");
  equal(route.peekHomeSnapshot()?.subscription?.entitled, false, "an unchanged plan keeps the subscription");

  route.syncSubscription("user-1", proPlan);
  equal(route.peekHomeSnapshot()?.usage, null, "a changed plan drops usage");
  equal(route.peekHomeSnapshot()?.subscription?.entitled, true, "the plan just read from the server replaces the cached one");
  route.cacheTurnUsage("user-1", { ...quota, remaining_turns: null, daily_limit: null });
  route.syncSubscription("user-1", proPlan);
  equal(route.peekHomeSnapshot()?.usage?.plan, "pro", "reading the same plan again keeps usage");

  // A turn's quota is the server's current count: the next read does not ask again.
  let usageReads = 0;
  pallyApi.getUsage = async () => { usageReads += 1; return route.usageFromQuota(null, quota); };
  route.cacheTurnUsage("user-1", quota);
  equal((await route.loadUsage("user-1")).remaining_turns, 17);
  equal(usageReads, 0, "usage from a turn is reused");
  route.cacheTurnUsage("user-1", { ...quota, resets_at: pastReset });
  await route.loadUsage("user-1");
  equal(usageReads, 1, "usage from before the daily reset is read again");

  // A saved name is kept, so no screen paints the previous one.
  route.cacheProfile("user-1", { profile: { ...profile.profile, display_name: "Aning" } });
  equal(route.peekHomeSnapshot()?.profile.display_name, "Aning", "a saved name is painted at once");
  equal(route.peekProfileSnapshot()?.data.profile.display_name, "Aning");

  // The plan label is painted only while the plan is known.
  equal(route.peekSubscriptionSnapshot()?.data.subscription.entitled, true);
  route.syncSubscription("user-1", { ...proPlan, current_period_end: pastReset });
  equal(route.peekSubscriptionSnapshot(), null, "a paid period that has ended is not painted as the current plan");

  route.clearUserRouteData("user-1");
  equal(route.peekHomeSnapshot(), null, "logout and deletion drop the snapshot and the remembered user");
  route.cacheTurnUsage("user-1", quota);
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
