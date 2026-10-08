import { deepEqual, equal, match, notEqual } from "node:assert/strict";

import { PallyApiError } from "../lib/api/contracts";
import { NETWORK_ERROR_MESSAGE, signInErrorMessage, userFacingErrorMessage } from "../lib/api/error-messages";

const HANGUL = /[가-힣]/;

// Codes with the English message the backend sends today (backend/main.py AppError).
const ENGLISH_BACKEND_ERRORS: Array<[number, string, string]> = [
  [401, "unauthorized", "Missing or invalid Authorization header"],
  [400, "invalid_audio", "Empty audio file"],
  [404, "not_found", "Conversation not found"],
  [404, "profile_not_found", "Profile not found. Complete onboarding first."],
  [409, "conflict", "Onboarding already completed. Use PATCH /api/profile to edit."],
  [409, "conversation_already_active", "Conversation is already active"],
  [409, "conversation_closed", "Conversation is already closed"],
  [409, "conversation_started", "Conversation already has a user turn"],
  [409, "duplicate_turn", "Duplicate turn already being processed"],
  [422, "speech_not_recognized", "No recognizable speech in audio"],
  [422, "validation_error", "display_name must be 1-30 characters after trimming"],
  [502, "ai_engine_failed", "Reply generation failed"],
  [502, "stt_failed", "Speech recognition failed"],
  [503, "persistence_failed", "Failed to read usage"],
  [503, "service_unavailable", "Speech/AI provider not configured"],
  [503, "auth_unavailable", "Auth service unavailable"],
  [503, "opener_failed", "Opener generation failed"],
];

async function main() {
  for (const [status, code, message] of ENGLISH_BACKEND_ERRORS) {
    const shown = userFacingErrorMessage(status, code, message);
    match(shown, HANGUL, `${code} must be shown in Korean`);
    notEqual(shown, message);
  }
  for (const status of [422, 500]) {
    match(userFacingErrorMessage(status, "a_code_added_later", "Something failed"), HANGUL, `unknown code at ${status}`);
  }
  equal(
    userFacingErrorMessage(503, "billing_error", "카카오페이 테스트 결제 설정이 필요해요."),
    "카카오페이 테스트 결제 설정이 필요해요.",
    "A Korean server message was written for the user and stays as it is",
  );

  // Sign-in fails inside Supabase Auth (English text) or in our API (Korean, kept as is).
  const supabaseFailure = new Error("invalid request: both auth code and code verifier should be non-empty");
  match(signInErrorMessage(supabaseFailure), HANGUL);
  notEqual(signInErrorMessage(supabaseFailure), supabaseFailure.message);
  match(signInErrorMessage("not an Error"), HANGUL);
  equal(signInErrorMessage(new PallyApiError(0, "network_error", NETWORK_ERROR_MESSAGE)), NETWORK_ERROR_MESSAGE);

  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://fixture.supabase.invalid";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "fixture-anon-key";
  process.env.NEXT_PUBLIC_BACKEND_URL = "https://fixture-backend.invalid";
  const { supabase } = await import("../lib/supabase/client");
  const { httpPallyApi } = await import("../lib/api/http-client");
  const originalSession = supabase.auth.getSession;
  const originalFetch = globalThis.fetch;
  const originalConsoleError = console.error;
  const logged: string[] = [];
  console.error = (...args: unknown[]) => { logged.push(args.map((arg) => JSON.stringify(arg, (_key, value) => (value instanceof Error ? value.message : value))).join(" ")); };
  const user = { id: crypto.randomUUID(), aud: "authenticated", app_metadata: {}, user_metadata: {}, created_at: new Date().toISOString() };
  const signedIn = async () => ({ data: { session: { access_token: "fixture-token", refresh_token: "fixture-refresh", token_type: "bearer", expires_in: 3600, user } }, error: null });
  supabase.auth.getSession = signedIn as typeof supabase.auth.getSession;

  const respond = (status: number, body: string, contentType = "application/json") => {
    globalThis.fetch = async () => new Response(body, { status, headers: { "Content-Type": contentType } });
  };
  const failure = async () => {
    try {
      await httpPallyApi.getUsage();
    } catch (error) {
      if (error instanceof PallyApiError) return error;
      throw error;
    }
    throw new Error("The request was expected to fail");
  };

  try {
    // A backend error keeps its code, status and request id; only the text changes.
    respond(422, JSON.stringify({ error: { code: "speech_not_recognized", message: "No recognizable speech in audio", request_id: "req_1" } }));
    let error = await failure();
    deepEqual([error.status, error.code, error.requestId], [422, "speech_not_recognized", "req_1"]);
    match(error.message, HANGUL);
    ok(logged.some((line) => line.includes("No recognizable speech in audio")), "The server's original text is still logged");

    // Offline: fetch itself rejects.
    globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
    error = await failure();
    deepEqual([error.status, error.code, error.message], [0, "network_error", NETWORK_ERROR_MESSAGE]);
    ok(logged.some((line) => line.includes("Failed to fetch")), "The network failure is logged");

    // A proxy answers with HTML instead of JSON.
    respond(502, "<html>Bad Gateway</html>", "text/html");
    error = await failure();
    deepEqual([error.status, error.code], [502, "invalid_response"]);
    match(error.message, HANGUL);
    ok(!error.message.includes("Unexpected token"), "The JSON parser's message must not reach the screen");

    // The login session itself cannot be read.
    supabase.auth.getSession = (async () => ({ data: { session: null }, error: new Error("AuthApiError: Invalid Refresh Token") })) as unknown as typeof supabase.auth.getSession;
    error = await failure();
    deepEqual([error.status, error.code], [401, "unauthorized"]);
    match(error.message, HANGUL);
    ok(!error.message.includes("Refresh Token"));
  } finally {
    console.error = originalConsoleError;
    globalThis.fetch = originalFetch;
    supabase.auth.getSession = originalSession;
    await supabase.auth.stopAutoRefresh();
  }

  console.log("Error message checks passed: backend codes, offline, non-JSON reply, session read failure and sign-in failure show Korean text.");
}

function ok(condition: unknown, message?: string): asserts condition {
  if (!condition) throw new Error(message ?? "Assertion failed");
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
