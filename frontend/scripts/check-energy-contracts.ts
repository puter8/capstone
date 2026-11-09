import { strict as assert } from "node:assert";
import { PallyApiError } from "../lib/api/contracts";
import type { EnergyBaselineResponse } from "../lib/api/contracts";
import { userFacingWarningMessages } from "../lib/api/error-messages";
import { conversationCompleteResponseSchema, energyBaselineResponseSchema } from "../lib/api/schemas";

const required: EnergyBaselineResponse = {
  status: "required",
  baseline: null,
  prompts: ["How was your day today?", "What's your favorite food, and why?", "What do you want to do this week?"],
  limits: { clips: 3, min_seconds: 5, max_seconds: 30 },
};
const ready: EnergyBaselineResponse = {
  ...required,
  status: "ready",
  baseline: { range_st: 0, valid_clips: 3, method_version: "v1" },
};
const disabled: EnergyBaselineResponse = { status: "disabled", baseline: null, prompts: [], limits: null };

for (const response of [required, ready, disabled]) {
  assert.deepEqual(energyBaselineResponseSchema.parse(response), response, "The screen must receive prompts and limits intact");
}
for (const response of [required, ready]) {
  for (const prompts of [undefined, [], required.prompts.slice(0, 2), [...required.prompts, "Extra?"], ["", "Second?", "Third?"], [" ", "Second?", "Third?"], [1, "Second?", "Third?"]]) {
    assert(!energyBaselineResponseSchema.safeParse({ ...response, prompts }).success, "Enabled responses require exactly three nonempty prompts");
  }
  for (const limits of [
    undefined,
    null,
    { ...required.limits, clips: 2 },
    { ...required.limits, min_seconds: 0 },
    { ...required.limits, min_seconds: -1 },
    { ...required.limits, min_seconds: 31 },
    { ...required.limits, min_seconds: NaN },
    { ...required.limits, max_seconds: Infinity },
    { ...required.limits, max_seconds: 31 },
    { ...required.limits, max_seconds: 4 },
  ]) {
    assert(!energyBaselineResponseSchema.safeParse({ ...response, limits }).success, "Invalid recording limits must fail at the API boundary");
  }
}
for (const response of [
  { ...ready, baseline: null },
  { ...required, baseline: ready.baseline },
  { ...disabled, prompts: required.prompts },
  { ...disabled, limits: required.limits },
  { ...disabled, baseline: ready.baseline },
  { ...required, status: "pending" },
]) {
  assert(!energyBaselineResponseSchema.safeParse(response).success, "Registration states must not mix their contracts");
}
assert(energyBaselineResponseSchema.safeParse({ ...required, limits: { clips: 3, min_seconds: 30, max_seconds: 30 } }).success);
for (const baseline of [
  ...[-1, NaN, Infinity].map((range_st) => ({ ...ready.baseline, range_st })),
  { ...ready.baseline, valid_clips: 2 },
  { ...ready.baseline, method_version: "" },
]) {
  assert(!energyBaselineResponseSchema.safeParse({ ...ready, baseline }).success);
}

const completion = conversationCompleteResponseSchema.parse({
  conversation: { id: "d2193690-ec8b-43ae-9385-4f6b1e52bb8f", status: "completed" },
  current_axes: { Formality: 50, Energy: 65, Intimacy: 25, Humor: 10, Curiosity: 70 },
  energy: { status: "retained", score: null, reason: "insufficient_audio" },
  warnings: [{ code: "energy_unavailable", message: "이전 값을 유지했어요." }],
});
assert.equal(completion.current_axes?.Energy, 65);
assert.equal(completion.warnings[0].code, "energy_unavailable");
assert.deepEqual(userFacingWarningMessages(completion.warnings), [], "Energy retention is not shown as a toast");
assert.deepEqual(userFacingWarningMessages([
  ...completion.warnings,
  { code: "tts_failed", message: "음성을 재생하지 못했어요." },
  { code: "feedback_failed", message: "피드백을 만들지 못했어요." },
  { code: "traits_update_failed", message: "성향을 갱신하지 못했어요." },
]), ["음성을 재생하지 못했어요.", "피드백을 만들지 못했어요.", "성향을 갱신하지 못했어요."], "Other warnings stay visible alongside retained energy");
assert.equal(completion.warnings.length, 1, "Filtering the UI does not remove API metadata");

async function checkHttpContract() {
  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://fixture.supabase.invalid";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "fixture-anon-key";
  process.env.NEXT_PUBLIC_BACKEND_URL = "https://fixture-backend.invalid";
  const { supabase } = await import("../lib/supabase/client");
  const { httpPallyApi } = await import("../lib/api/http-client");
  const originalSession = supabase.auth.getSession;
  const originalFetch = globalThis.fetch;
  const originalConsoleError = console.error;
  const logged: unknown[][] = [];
  console.error = (...args: unknown[]) => { logged.push(args); };
  const user = { id: crypto.randomUUID(), aud: "authenticated", app_metadata: {}, user_metadata: {}, created_at: new Date().toISOString() };
  supabase.auth.getSession = async () => ({
    data: { session: { access_token: "fixture-token", refresh_token: "fixture-refresh", token_type: "bearer", expires_in: 3600, user } },
    error: null,
  });

  try {
    globalThis.fetch = async (input, init) => {
      assert.equal(input, "https://fixture-backend.invalid/api/energy/baseline");
      assert.equal(init?.method, "GET");
      return Response.json(required);
    };
    assert.deepEqual(await httpPallyApi.getEnergyBaseline(), required);

    const clips: [Blob, Blob, Blob] = [1, 2, 3].map((value) => new Blob([String(value)], { type: "audio/wav" })) as [Blob, Blob, Blob];
    const details = { clip_index: 2, reason: "insufficient_voiced_frames" };
    globalThis.fetch = async (input, init) => {
      assert.equal(input, "https://fixture-backend.invalid/api/energy/baseline");
      assert.equal(init?.method, "POST");
      assert.equal(new Headers(init?.headers).get("Idempotency-Key"), "baseline-retry-key");
      assert(init?.body instanceof FormData);
      const uploaded = init.body.getAll("audio");
      assert.equal(uploaded.length, 3);
      assert.deepEqual(await Promise.all(uploaded.map((clip) => {
        assert(clip instanceof Blob);
        return clip.text();
      })), ["1", "2", "3"]);
      return Response.json({
        error: { code: "invalid_audio", message: "Insufficient voiced frames", request_id: "req_baseline", details },
      }, { status: 422 });
    };
    await assert.rejects(() => httpPallyApi.registerEnergyBaseline(clips, "baseline-retry-key"), (error: unknown) => {
      assert(error instanceof PallyApiError);
      assert.deepEqual([error.status, error.code, error.requestId], [422, "invalid_audio", "req_baseline"]);
      assert.deepEqual(error.details, details, "The UI needs the rejected clip index and reason for a focused retry");
      assert.match(error.message, /[가-힣]/);
      assert.notEqual(error.message, "Insufficient voiced frames", "Internal server text must not become the UI error");
      return true;
    });
    assert(logged.length > 0, "Failed requests remain logged");

    globalThis.fetch = async () => Response.json({
      error: { code: "invalid_audio", message: "Invalid details", details: [2, "clip_too_short"] },
    }, { status: 422 });
    await assert.rejects(() => httpPallyApi.getEnergyBaseline(), (error: unknown) => error instanceof PallyApiError && error.code === "invalid_response");
    assert.equal(new PallyApiError(422, "invalid_audio", "다시 녹음해 주세요.").details, undefined, "Existing constructor callers remain supported");
  } finally {
    globalThis.fetch = originalFetch;
    supabase.auth.getSession = originalSession;
    console.error = originalConsoleError;
    await supabase.auth.stopAutoRefresh();
  }
}

checkHttpContract().then(() => {
  console.log("Energy API boundary checks passed: registration states, prompts, limits, multipart uploads and clip-specific errors.");
}).catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
