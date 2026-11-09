import { deepEqual, doesNotMatch, equal, match, rejects } from "node:assert/strict";
import React, { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import type { DailyExpressionResponse } from "../lib/api/contracts";
import { dailyExpressionResponseSchema } from "../lib/api/schemas";

async function main() {
  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://fixture.supabase.invalid";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "fixture-public-anon-key";
  process.env.NEXT_PUBLIC_BACKEND_URL = "https://fixture-backend.invalid";
  (globalThis as { React?: typeof React }).React = React;

  const { DailyExpressionContent } = await import("../components/v2/DailyExpressionCard");
  const { httpPallyApi } = await import("../lib/api/http-client");
  const { supabase } = await import("../lib/supabase/client");
  const response: DailyExpressionResponse = {
    date: new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date()),
    timezone: "Asia/Seoul",
    expression: {
      id: "b1-thinking-of", level: "B1", text: "I'm thinking of ~ing",
      meaning_ko: "~할까 생각 중이에요", example_en: "I'm thinking of learning the guitar.",
      example_ko: "기타를 배울까 생각 중이에요.",
    },
  };
  const render = (data: DailyExpressionResponse) => renderToStaticMarkup(createElement(DailyExpressionContent, { data }));
  const markup = render(response);
  match(markup, /thinking of ~ing/, "The card teaches the server's actual expression");
  match(markup, /thinking of learning the guitar/, "The example comes from the same server entry");
  doesNotMatch(markup, /into|baking/, "The previous fixed prompt must never replace server data");
  doesNotMatch(markup, /오늘 사용했어요/, "The home card no longer displays the completion label");
  const legacyCompleted = { ...response, used_today: true, pally_used_today: true };
  doesNotMatch(render(legacyCompleted), /오늘 사용했어요/, "Legacy response flags must not bring back the label");
  const nextDay = { ...response, date: "2026-11-04", expression: { ...response.expression, id: "b1-into", text: "I'm into ~", example_en: "I'm into music." } };
  match(render(nextDay), /into ~/);
  doesNotMatch(render(nextDay), /thinking of/, "A different day's expression must replace both the title and example");

  for (const bad of [
    { ...response, expression: { ...response.expression, level: "invalid" } },
    { ...response, timezone: "UTC" },
    { ...response, date: "2026-02-31" },
    { ...response, expression: { ...response.expression, example_en: " " } },
  ]) equal(dailyExpressionResponseSchema.safeParse(bad).success, false);

  const originalSession = supabase.auth.getSession;
  const originalFetch = globalThis.fetch;
  const originalError = console.error;
  const logged: unknown[][] = [];
  const user = { id: crypto.randomUUID(), aud: "authenticated", app_metadata: {}, user_metadata: {}, created_at: new Date().toISOString() };
  supabase.auth.getSession = async () => ({ data: { session: { access_token: "fixture-token", refresh_token: "fixture-refresh", token_type: "bearer", expires_in: 3600, user } }, error: null });
  let payload: unknown = response;
  let calls = 0;
  globalThis.fetch = async (url, init) => {
    equal(url, "https://fixture-backend.invalid/api/daily-expression?include_usage=false");
    equal(new Headers(init?.headers).get("Authorization"), "Bearer fixture-token");
    calls += 1;
    return Response.json(payload);
  };
  try {
    deepEqual(await httpPallyApi.getDailyExpression(), response);
    payload = nextDay;
    equal((await httpPallyApi.getDailyExpression()).expression.id, "b1-into");
    equal(calls, 2, "The HTTP layer must not keep a previous expression");
    payload = { ...response, expression: { ...response.expression, example_en: " " } };
    console.error = (...args: unknown[]) => { logged.push(args); };
    await rejects(httpPallyApi.getDailyExpression(), { code: "invalid_response" });
    equal(logged.length > 0, true, "Malformed responses are logged, never replaced with a fixed expression");
  } finally {
    supabase.auth.getSession = originalSession;
    globalThis.fetch = originalFetch;
    console.error = originalError;
  }

  const { pallyApi } = await import("../lib/api");
  const route = await import("../lib/api/route-data");
  const originalLoader = pallyApi.getDailyExpression;
  const profile = {
    id: "user-1", display_name: "Claire", english_level: "B1" as const,
    onboarding_completed: true, traits: [], avatar_url: null,
    created_at: "2026-11-03T00:00:00Z", updated_at: "2026-11-03T00:00:00Z",
  };
  let reads = 0;
  pallyApi.getDailyExpression = async () => { reads += 1; return response; };
  try {
    route.rememberUser("user-1");
    route.cacheProfile("user-1", { profile });
    await Promise.all([route.loadDailyExpression("user-1"), route.loadDailyExpression("user-1")]);
    equal(reads, 1, "Home prefetch and the card share one in-flight request");
    deepEqual(route.peekDailyExpressionSnapshot()?.data, response, "A returning home paints the prompt immediately");
    await route.loadDailyExpression("user-1");
    equal(reads, 1, "Returning home reuses the fresh prompt");

    route.cacheProfile("user-1", { profile: { ...profile, english_level: "B2" } });
    equal(route.peekDailyExpressionSnapshot(), null, "Changing level removes the old prompt, including stale paint");
    const b2 = { ...response, expression: { ...response.expression, level: "B2" as const, id: "b2-tend-to", text: "I tend to ~" } };
    pallyApi.getDailyExpression = async () => { reads += 1; return b2; };
    await route.loadDailyExpression("user-1");
    equal(reads, 2);
    equal(route.peekDailyExpressionSnapshot()?.data.expression.level, "B2");
    route.cacheProfile("user-1", { profile: { ...profile, english_level: "B2", display_name: "New name" } });
    equal(route.peekDailyExpressionSnapshot()?.data.expression.level, "B2", "A name edit does not discard the prompt");

    route.invalidateDailyExpression("user-1");
    let resolveOld!: (value: DailyExpressionResponse) => void;
    pallyApi.getDailyExpression = () => new Promise((resolve) => { resolveOld = resolve; });
    const pending = route.loadDailyExpression("user-1");
    route.cacheProfile("user-1", { profile: { ...profile, english_level: "C1" } });
    const c1 = { ...b2, expression: { ...b2.expression, level: "C1" as const, id: "c1-partial-to", text: "I'm partial to ~" } };
    pallyApi.getDailyExpression = async () => c1;
    await route.loadDailyExpression("user-1");
    resolveOld(b2);
    await pending;
    equal(route.peekDailyExpressionSnapshot()?.data.expression.level, "C1", "An old in-flight request cannot restore the previous level");
    route.rememberUser("user-2");
    equal(route.peekDailyExpressionSnapshot(), null, "Account changes cannot paint another user's prompt");
    route.rememberUser("user-1");
    route.invalidateDailyExpression("user-1");
    pallyApi.getDailyExpression = async () => ({ ...c1, date: "2000-01-01" });
    await route.loadDailyExpression("user-1");
    equal(route.peekDailyExpressionSnapshot(), null, "A previous KST day cannot be painted as today's prompt");
  } finally {
    route.clearUserRouteData("user-1");
    pallyApi.getDailyExpression = originalLoader;
  }
  console.log("Daily expression checks passed: prompt-only reads, no completion label, scoped cache and level invalidation.");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
