import assert from "node:assert/strict";

import { clearUser, invalidate, read } from "../lib/api/query-cache";

async function main(): Promise<void> {
  let calls = 0;
  let resolveLoader: (value: string) => void = () => {
    throw new Error("loader resolver was not created");
  };
  const loader = () => {
    calls += 1;
    return new Promise<string>((resolve) => {
      resolveLoader = resolve;
    });
  };

  const first = read("user-a", "profile", 60_000, loader);
  const duplicate = read("user-a", "profile", 60_000, loader);
  assert.equal(calls, 1, "concurrent reads must share one loader");
  resolveLoader("Claire");
  assert.deepEqual(await Promise.all([first, duplicate]), ["Claire", "Claire"]);

  const cached = await read("user-a", "profile", 60_000, async () => {
    calls += 1;
    return "unexpected";
  });
  assert.equal(cached, "Claire");
  assert.equal(calls, 1, "fresh values must be served from cache");

  invalidate("user-a", "profile");
  const refreshed = await read("user-a", "profile", 60_000, async () => {
    calls += 1;
    return "Lee";
  });
  assert.equal(refreshed, "Lee");
  assert.equal(calls, 2, "invalidated values must reload");

  await read("user-b", "profile", 60_000, async () => "Other user");
  clearUser("user-a");
  const isolated = await read("user-b", "profile", 60_000, async () => "unexpected");
  assert.equal(isolated, "Other user", "clearing one user must not affect another user");

  const expiringKey = `usage-${crypto.randomUUID()}`;
  await read("user-a", expiringKey, 0, async () => 1);
  const expired = await read("user-a", expiringKey, 60_000, async () => 2);
  assert.equal(expired, 2, "expired values must reload");

  let resolveStaleRequest: (value: string) => void = () => {
    throw new Error("stale request resolver was not created");
  };
  const staleRequest = read("user-a", "history:first", 60_000, () => (
    new Promise<string>((resolve) => {
      resolveStaleRequest = resolve;
    })
  ));
  invalidate("user-a", "history:");
  resolveStaleRequest("stale");
  assert.equal(await staleRequest, "stale");
  const afterRace = await read("user-a", "history:first", 60_000, async () => "fresh");
  assert.equal(afterRace, "fresh", "invalidated in-flight requests must not repopulate cache");

  clearUser("user-a");
  clearUser("user-b");
  console.log("Query cache checks passed");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
