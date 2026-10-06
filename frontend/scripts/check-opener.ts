import { deepEqual, equal, rejects } from "node:assert/strict";
import { mockPallyApi, resetMockPallyApi } from "../lib/api/mock-client";
import { openerResponseSchema } from "../lib/api/schemas";
import { PallyApiError } from "../lib/api/contracts";

async function main() {
  resetMockPallyApi();
  const quota = await mockPallyApi.getUsage();
  const { conversation } = await mockPallyApi.createConversation(crypto.randomUUID());
  const key = crypto.randomUUID();
  await rejects(() => mockPallyApi.createOpener(conversation.id, ""), (error: unknown) => error instanceof PallyApiError && error.status === 422);
  const opener = await mockPallyApi.createOpener(conversation.id, key);
  deepEqual(openerResponseSchema.parse(opener), opener);
  deepEqual(await mockPallyApi.createOpener(conversation.id, key), opener);
  const detail = await mockPallyApi.getConversation(conversation.id);
  equal(detail.turns.length, 1, "Retry must not duplicate the saved opener");
  equal(detail.turns[0].user_transcript, null);
  equal(detail.conversation.turn_count, 0, "Opener is not a user turn");
  equal(detail.conversation.title, opener.text);
  deepEqual(await mockPallyApi.getUsage(), quota, "Opener consumes no quota");
  await mockPallyApi.completeConversation(conversation.id);
  await rejects(() => mockPallyApi.createOpener(conversation.id, key), (error: unknown) => error instanceof PallyApiError && error.code === "conversation_closed");
  await mockPallyApi.reopenConversation(conversation.id);
  await mockPallyApi.createTurn(conversation.id, { audio: new Blob([new Uint8Array([1])], {type:"audio/wav"}), idempotency_key:crypto.randomUUID() });
  await rejects(() => mockPallyApi.createOpener(conversation.id, key), (error: unknown) => error instanceof PallyApiError && error.code === "conversation_started");
  equal((await mockPallyApi.getConversation(conversation.id)).conversation.turn_count, 1);
  deepEqual(openerResponseSchema.parse({text:"How was your day?",audio:null,warnings:[{code:"tts_failed",message:"Text only"}]}).audio, null);
  equal(openerResponseSchema.safeParse({text:"",audio:null,warnings:[]}).success, false);

  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://fixture.supabase.invalid";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "fixture-anon-key";
  process.env.NEXT_PUBLIC_BACKEND_URL = "https://fixture-backend.invalid";
  const { supabase } = await import("../lib/supabase/client");
  const { httpPallyApi } = await import("../lib/api/http-client");
  const originalSession = supabase.auth.getSession;
  const originalFetch = globalThis.fetch;
  const user = {id:crypto.randomUUID(),aud:"authenticated",app_metadata:{},user_metadata:{},created_at:new Date().toISOString()};
  supabase.auth.getSession = async () => ({data:{session:{access_token:"fixture-token",refresh_token:"fixture-refresh",token_type:"bearer",expires_in:3600,user}},error:null});
  let status = 201;
  let payload: unknown = opener;
  const calls: Array<{method?:string; path:string; key:string|null}> = [];
  globalThis.fetch = async (input, init) => {
    const url = new URL(String(input));
    equal(url.origin,"https://fixture-backend.invalid");
    calls.push({method:init?.method,path:url.pathname,key:new Headers(init?.headers).get("Idempotency-Key")});
    return new Response(JSON.stringify(payload),{status,headers:{"Content-Type":"application/json"}});
  };
  try {
    await httpPallyApi.createOpener(conversation.id,key);
    await httpPallyApi.createOpener(conversation.id,key);
    deepEqual(calls,[0,1].map(()=>({method:"POST",path:`/api/conversations/${conversation.id}/opener`,key})));
    for (const code of ["opener_failed","conversation_started","conversation_closed"]) {
      status = code === "opener_failed" ? 503 : 409;
      payload = {error:{code,message:"fixture error"}};
      await rejects(()=>httpPallyApi.createOpener(conversation.id,key),(error:unknown)=>error instanceof PallyApiError&&error.code===code&&error.status===status);
    }
  } finally {
    globalThis.fetch = originalFetch;
    supabase.auth.getSession = originalSession;
    await supabase.auth.stopAutoRefresh();
    resetMockPallyApi();
  }
  console.log("Opener checks passed: headers, replay, quota, history, null audio and error codes.");
}

main().catch((error:unknown)=>{ console.error(error);process.exitCode=1; });
