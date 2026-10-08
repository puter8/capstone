import { deepEqual, equal } from "node:assert/strict";

import type { AchievementsResponse, ConversationListResponse, ProfileResponse } from "../lib/api/contracts";

type NavigatorFixture = { connection?: { effectiveType?: string; saveData?: boolean } };

function setNavigator(value: NavigatorFixture): void {
  Object.defineProperty(globalThis, "navigator", { configurable: true, value });
}

async function main(): Promise<void> {
  // route-data imports the Supabase client, which needs these at import time.
  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://fixture.supabase.invalid";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "fixture-public-anon-key";
  const { pallyApi } = await import("../lib/api");
  const route = await import("../lib/api/route-data");

  const history: ConversationListResponse = {
    items: [{
      id: "conversation-1",
      status: "completed",
      title: "Weekend plans",
      started_at: "2026-10-08T00:00:00Z",
      last_turn_at: "2026-10-08T00:05:00Z",
      completed_at: "2026-10-08T00:06:00Z",
      turn_count: 4,
      feedback_count: 2,
      preview: "I went to the beach.",
    }],
    next_cursor: null,
  };
  const achievements: AchievementsResponse = {
    date: "2026-10-08",
    timezone: "Asia/Seoul",
    streak_count: 3,
    daily_tasks: [
      { id: "task-1", title: "Talk", description: "Talk with Pally", status: "completed", completed_at: "2026-10-08T00:06:00Z" },
      { id: "task-2", title: "Review", description: "Open feedback", status: "default", completed_at: null },
      { id: "task-3", title: "Visit", description: "Open achievements", status: "default", completed_at: null },
    ],
  };
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
    },
  };

  const calls = { achievements: 0, history: 0, profile: 0 };
  pallyApi.listConversations = async () => { calls.history += 1; return history; };
  pallyApi.getAchievements = async () => { calls.achievements += 1; return achievements; };
  pallyApi.getProfile = async () => { calls.profile += 1; return profile; };

  equal(route.peekHistorySnapshot(), null, "no remembered user means nothing to paint");
  route.rememberUser("user-1");
  equal(route.peekHistorySnapshot(), null, "a tab never loaded has nothing to paint");
  equal(route.peekAchievementsSnapshot(), null);
  equal(route.peekProfileSnapshot(), null);

  await route.loadHistoryPage("user-1");
  await route.loadAchievements("user-1");
  await route.loadProfile("user-1");
  deepEqual(route.peekHistorySnapshot(), { userId: "user-1", data: history }, "the list a tab loaded is painted on return");
  deepEqual(route.peekAchievementsSnapshot(), { userId: "user-1", data: achievements });
  deepEqual(route.peekProfileSnapshot(), { userId: "user-1", data: profile });

  route.invalidateConversationData("user-1");
  deepEqual(route.peekHistorySnapshot()?.data, history, "an ended conversation keeps the old list paintable");
  deepEqual(route.peekAchievementsSnapshot()?.data, achievements);
  await route.loadHistoryPage("user-1");
  equal(calls.history, 2, "but the screen's read still goes to the server");

  route.rememberUser("user-2");
  equal(route.peekHistorySnapshot(), null, "another account never paints the previous account's data");
  route.rememberUser("user-1");
  route.clearUserRouteData("user-1");
  equal(route.peekHistorySnapshot(), null, "logout and deletion drop the painted data");
  equal(route.peekProfileSnapshot(), null);

  // Idle prefetch from home: run timers immediately and count the tab reads it starts.
  Object.defineProperty(globalThis, "window", { configurable: true, value: globalThis });
  const prefetchCalls = async (navigatorFixture: NavigatorFixture): Promise<number> => {
    setNavigator(navigatorFixture);
    route.clearUserRouteData("user-3");
    const before = calls.history;
    route.schedulePrimaryRoutePrefetch("user-3");
    await new Promise((resolve) => setTimeout(resolve, 700));
    return calls.history - before;
  };
  equal(await prefetchCalls({}), 1, "Safari has no connection info and still prefetches");
  equal(await prefetchCalls({ connection: { effectiveType: "4g" } }), 1);
  equal(await prefetchCalls({ connection: {} }), 1, "a browser that reports no type still prefetches");
  equal(await prefetchCalls({ connection: { effectiveType: "3g" } }), 0, "slow networks skip it");
  equal(await prefetchCalls({ connection: { effectiveType: "4g", saveData: true } }), 0, "data saver skips it");

  console.log("Route snapshot checks passed.");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
