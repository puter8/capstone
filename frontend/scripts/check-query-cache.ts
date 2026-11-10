import assert from "node:assert/strict";

import { clearUser, evict, invalidate, peek, peekStale, read, write } from "../lib/api/query-cache";

async function main(): Promise<void> {
  write("peek-user", "history:first", 60_000, { items: [] });
  assert.deepEqual(peek("peek-user", "history:first"), { items: [] }, "empty history is valid cached data");
  assert.equal(peek("other-user", "history:first"), undefined, "peek must stay scoped to the current user");
  write("peek-user", "history:latest", 0, "expired");
  assert.equal(peek("peek-user", "history:latest"), undefined, "peek must not serve expired values");
  invalidate("peek-user", "history:");
  assert.equal(peek("peek-user", "history:first"), undefined, "conversation changes must invalidate peeked history");
  clearUser("peek-user");

  write("stale-user", "usage", 60_000, { remaining: 3 });
  invalidate("stale-user", "usage");
  assert.equal(peek("stale-user", "usage"), undefined, "invalidated values must not count as fresh");
  assert.deepEqual(peekStale("stale-user", "usage"), { remaining: 3 }, "invalidated values stay readable as stale");
  write("stale-user", "profile", 0, "expired");
  assert.equal(peekStale("stale-user", "profile"), "expired", "expired values stay readable as stale");
  assert.equal(peekStale("other-user", "usage"), undefined, "peekStale must stay scoped to the current user");
  let resolveRefresh!: (value: string) => void;
  write("stale-user", "refreshing", 60_000, "old");
  invalidate("stale-user", "refreshing");
  const refreshing = read("stale-user", "refreshing", 60_000, () => new Promise<string>((resolve) => {
    resolveRefresh = resolve;
  }));
  assert.equal(peekStale("stale-user", "refreshing"), "old", "stale value stays readable while a refresh is in flight");
  invalidate("stale-user", "refreshing");
  resolveRefresh("late");
  assert.equal(await refreshing, "late");
  assert.equal(peek("stale-user", "refreshing"), undefined, "an invalidated refresh must not mark the cache fresh");
  assert.equal(peekStale("stale-user", "refreshing"), "old", "an invalidated refresh must not overwrite the stale value");
  write("stale-user", "subscription", 60_000, "pro");
  evict("stale-user", "subscription");
  assert.equal(peekStale("stale-user", "subscription"), undefined, "evict must drop the stale value too");
  clearUser("stale-user");
  assert.equal(peekStale("stale-user", "usage"), undefined, "clearUser must drop stale values too");

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

  let resolveOldProfile!: (value: string) => void;
  invalidate("user-a", "profile");
  const oldProfile = read("user-a", "profile", 60_000, () => new Promise<string>((resolve) => {
    resolveOldProfile = resolve;
  }));
  write("user-a", "profile", 60_000, "B2");
  const unexpectedReload = async (): Promise<string> => {
    throw new Error("saved profiles must not be fetched again");
  };
  assert.equal(await read("user-a", "profile", 60_000, unexpectedReload), "B2");
  resolveOldProfile("B1");
  await oldProfile;
  assert.equal(await read("user-a", "profile", 60_000, unexpectedReload), "B2", "older reads must not overwrite saved profiles");
  assert.equal(await read("user-b", "profile", 60_000, unexpectedReload), "Other user", "writes must stay scoped to the current user");

  // A lifetime chosen from the loaded value, for data that is only final sometimes.
  const settledKey = `conversation-${crypto.randomUUID()}`;
  const byValue = (value: { settled: boolean }) => (value.settled ? 60_000 : 0);
  await read("user-a", settledKey, byValue, async () => ({ settled: true }));
  assert.deepEqual(
    await read("user-a", settledKey, byValue, async () => ({ settled: false })),
    { settled: true },
    "a value its own lifetime calls final must be served from cache",
  );
  const unsettledKey = `conversation-${crypto.randomUUID()}`;
  await read("user-a", unsettledKey, byValue, async () => ({ settled: false }));
  assert.deepEqual(
    await read("user-a", unsettledKey, byValue, async () => ({ settled: true })),
    { settled: true },
    "a value its own lifetime calls unfinished must reload",
  );

  // The lifetime is computed inside the identity check, so a read that crossed an
  // invalidate is still dropped instead of being kept for the long lifetime.
  const racedKey = `conversation-${crypto.randomUUID()}`;
  let resolveRaced!: (value: { settled: boolean }) => void;
  const raced = read("user-a", racedKey, byValue, () => new Promise<{ settled: boolean }>((resolve) => {
    resolveRaced = resolve;
  }));
  invalidate("user-a", racedKey);
  resolveRaced({ settled: true });
  await raced;
  assert.deepEqual(
    await read("user-a", racedKey, byValue, async () => ({ settled: false })),
    { settled: false },
    "an invalidated read must not be stored even when its value looks final",
  );

  clearUser("user-a");
  clearUser("user-b");
  console.log("Query cache checks passed");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
