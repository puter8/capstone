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
    date: "2026-11-03",
    timezone: "Asia/Seoul",
    expression: {
      id: "b1-thinking-of", level: "B1", text: "I'm thinking of ~ing",
      meaning_ko: "~할까 생각 중이에요", example_en: "I'm thinking of learning the guitar.",
      example_ko: "기타를 배울까 생각 중이에요.",
    },
    used_today: false,
    pally_used_today: true,
  };
  const render = (data: DailyExpressionResponse) => renderToStaticMarkup(createElement(DailyExpressionContent, { data }));
  const markup = render(response);
  match(markup, /thinking of ~ing/, "The card teaches the server's actual expression");
  match(markup, /thinking of learning the guitar/, "The example comes from the same server entry");
  doesNotMatch(markup, /into|baking/, "The previous fixed prompt must never replace server data");
  doesNotMatch(markup, /오늘 사용했어요/, "Pally saying the expression cannot complete the user's task");
  match(render({ ...response, used_today: true }), /오늘 사용했어요/, "Completion uses the server verdict");
  const nextDay = { ...response, date: "2026-11-04", expression: { ...response.expression, id: "b1-into", text: "I'm into ~", example_en: "I'm into music." } };
  match(render(nextDay), /into ~/);
  doesNotMatch(render(nextDay), /thinking of/, "A different day's expression must replace both the title and example");

  for (const bad of [
    { ...response, used_today: "true" },
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
    equal(url, "https://fixture-backend.invalid/api/daily-expression");
    equal(new Headers(init?.headers).get("Authorization"), "Bearer fixture-token");
    calls += 1;
    return Response.json(payload);
  };
  try {
    deepEqual(await httpPallyApi.getDailyExpression(), response);
    payload = { ...response, used_today: true };
    equal((await httpPallyApi.getDailyExpression()).used_today, true, "Returning from a turn reads the fresh server verdict");
    equal(calls, 2, "An old unused verdict must not be cached");
    payload = { ...response, used_today: "true" };
    console.error = (...args: unknown[]) => { logged.push(args); };
    await rejects(httpPallyApi.getDailyExpression(), { code: "invalid_response" });
    equal(logged.length > 0, true, "Malformed responses are logged, never replaced with a fixed expression");
  } finally {
    supabase.auth.getSession = originalSession;
    globalThis.fetch = originalFetch;
    console.error = originalError;
  }
  console.log("Daily expression checks passed: server prompt, fresh completion, and response validation.");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
