import { deepEqual, equal } from "node:assert/strict";

import type {
  AchievementsResponse, ConversationDetailResponse, ConversationListResponse,
  EnergyBaselineLimits, EnergyBaselinePrompts, EnergyBaselineResponse, ProfileResponse,
} from "../lib/api/contracts";

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

  // Feedback detail: a settled page is kept for the tab, an unfinished one is re-read.
  // Both lifetimes are longer than a test takes, so the clock is moved past the short
  // one (30s) and nowhere near the settled one to tell the two apart.
  const detail = (over: Partial<ConversationDetailResponse["conversation"]> = {}, pending = false): ConversationDetailResponse => ({
    conversation: {
      id: "conversation-1", status: "completed", title: "Weekend plans",
      started_at: "2026-10-08T00:00:00Z", last_turn_at: "2026-10-08T00:05:00Z",
      completed_at: "2026-10-08T00:06:00Z", reopened_at: null, reopen_count: 0,
      turn_count: 1, ...over,
    },
    turns: [{
      id: "turn-1", sequence: 1, status: "completed",
      user_transcript: "I went to the beach.", pally_text: "Nice!",
      feedback: [], feedback_pending: pending, pally_segments: null,
      created_at: "2026-10-08T00:05:00Z",
    }],
    next_cursor: null,
  });
  const realNow = Date.now;
  // Reads the page twice a minute apart and reports how many requests that took.
  const readsAMinuteApart = async (response: ConversationDetailResponse): Promise<number> => {
    route.clearUserRouteData("user-4");
    route.rememberUser("user-4");
    let requests = 0;
    pallyApi.getConversation = async () => { requests += 1; return response; };
    await route.loadConversationPage("user-4", "conversation-1");
    const movedOn = realNow() + 60_000;
    Date.now = () => movedOn;
    try {
      await route.loadConversationPage("user-4", "conversation-1");
    } finally {
      Date.now = realNow;
    }
    return requests;
  };

  equal(await readsAMinuteApart(detail()), 1,
    "a finished conversation with its feedback and title is read once");
  deepEqual(route.peekConversationPage("conversation-1")?.conversation.title, "Weekend plans",
    "and stays paintable, so reopening it shows no loader");

  // The settled page above is still cached here, so the counts show both halves.
  let requests = 0;
  pallyApi.getConversation = async () => { requests += 1; return detail(); };
  await route.loadConversationPage("user-4", "conversation-1");
  equal(requests, 0, "a settled page is served from cache");
  route.invalidateConversationData("user-4", "conversation-1");
  await route.loadConversationPage("user-4", "conversation-1");
  equal(requests, 1, "reopening or ending the conversation still forces a fresh read");

  equal(await readsAMinuteApart(detail({}, true)), 2,
    "a page still extracting feedback is re-read");
  equal(await readsAMinuteApart(detail({ title: "I went to the beach." })), 2,
    "a page whose title is still the first-utterance fallback is re-read");
  equal(await readsAMinuteApart(detail({ status: "active", completed_at: null })), 2,
    "an active conversation is re-read");
  equal(Date.now, realNow, "the clock must be put back");
  route.clearUserRouteData("user-4");

  // Voice baseline: home waits for this first, so a registered user must not pay a
  // round trip for it on every visit, and "required" must never be served from cache.
  const prompts: EnergyBaselinePrompts = ["one", "two", "three"];
  const limits: EnergyBaselineLimits = { clips: 3, min_seconds: 2, max_seconds: 10 };
  const baseline = (status: "ready" | "required" | "disabled"): EnergyBaselineResponse => {
    if (status === "ready") {
      return {
        status, prompts, limits,
        baseline: { range_st: 4, valid_clips: 3, method_version: "pitch-range-fold-v1" },
      };
    }
    if (status === "required") return { status, baseline: null, prompts, limits };
    return { status, baseline: null, prompts: [], limits: null };
  };
  const baselineReads = async (status: "ready" | "required" | "disabled"): Promise<number> => {
    route.clearUserRouteData("user-5");
    route.rememberUser("user-5");
    let requests = 0;
    const response = baseline(status);
    pallyApi.getEnergyBaseline = async () => { requests += 1; return response; };
    await route.loadEnergyBaseline("user-5");
    const movedOn = realNow() + 60_000;
    Date.now = () => movedOn;
    try {
      await route.loadEnergyBaseline("user-5");
    } finally {
      Date.now = realNow;
    }
    return requests;
  };
  equal(await baselineReads("ready"), 1, "a registered voice is read once");
  equal(await baselineReads("disabled"), 1, "a server with the feature off is read once");
  equal(await baselineReads("required"), 2, "an unregistered voice must never be served from cache");
  route.clearUserRouteData("user-5");

  console.log("Route snapshot checks passed.");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
