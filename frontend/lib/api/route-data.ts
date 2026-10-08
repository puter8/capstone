import type {
  AchievementsResponse,
  ConversationDetailResponse,
  ConversationListResponse,
  ProfileResponse,
  SubscriptionResponse,
  UsageQuota,
  UsageResponse,
} from "@/lib/api/contracts";
import { PallyApiError } from "@/lib/api/contracts";
import { SESSION_ERROR_MESSAGE } from "@/lib/api/error-messages";
import { pallyApi } from "@/lib/api";
import { clearUser, evict, invalidate, peekStale, prefetch, read, write, writeStale } from "@/lib/api/query-cache";
import { supabase } from "@/lib/supabase/client";
import type { Axes } from "@/lib/types/character";

const USAGE_TTL_MS = 15_000;
const CONVERSATION_TTL_MS = 30_000;
const ROUTE_DATA_TTL_MS = 60_000;

const CACHE_KEYS = {
  achievements: "achievements",
  conversation: "conversation:",
  history: "history:",
  profile: "profile",
  subscription: "subscription",
  usage: "usage",
} as const;

function cursorKey(cursor?: string): string {
  return cursor ?? "first";
}

// Last signed-in user seen in this tab. Lets the home screen paint cached data
// before the session check returns; it is always verified against the session.
let rememberedUserId: string | null = null;

export function rememberUser(userId: string): void {
  rememberedUserId = userId;
}

export function forgetRememberedUser(): void {
  rememberedUserId = null;
}

export async function getCurrentUserId(): Promise<string> {
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    console.error("Reading the login session failed", error);
    throw new PallyApiError(401, "unauthorized", SESSION_ERROR_MESSAGE);
  }
  if (!data.session) throw new PallyApiError(401, "unauthorized", "로그인이 필요해요.");
  rememberUser(data.session.user.id);
  return data.session.user.id;
}

export interface HomeSnapshot {
  userId: string;
  usage: UsageResponse;
  profile: ProfileResponse["profile"];
  subscription: SubscriptionResponse["subscription"] | null;
}

// Last known home data for the remembered user, even if expired. Null until the
// user has loaded both usage and profile once, so a cold start still shows the loader.
export function peekHomeSnapshot(): HomeSnapshot | null {
  if (!rememberedUserId) return null;
  const usage = peekStale<UsageResponse>(rememberedUserId, CACHE_KEYS.usage);
  const profile = peekStale<ProfileResponse>(rememberedUserId, CACHE_KEYS.profile);
  if (!usage || !profile) return null;
  const subscription = peekStale<SubscriptionResponse>(rememberedUserId, CACHE_KEYS.subscription);
  return {
    userId: rememberedUserId,
    usage,
    profile: profile.profile,
    subscription: subscription ? subscription.subscription : null,
  };
}

export function usageFromQuota(current: UsageResponse | null | undefined, quota: UsageQuota): UsageResponse {
  return {
    plan: quota.daily_limit === null ? "pro" : "free",
    date: current?.date ?? new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(new Date()),
    timezone: "Asia/Seoul",
    used_turns: quota.used_turns ?? (quota.daily_limit !== null && quota.remaining_turns !== null ? quota.daily_limit - quota.remaining_turns : 0),
    remaining_turns: quota.remaining_turns,
    daily_limit: quota.daily_limit,
    reset_at: quota.resets_at,
  };
}

// After a turn the server value is already known from the response. Keep it as the
// stale value so returning to home does not flash the old count before the reload.
export function patchStaleUsage(userId: string, quota: UsageQuota): void {
  writeStale(userId, CACHE_KEYS.usage, usageFromQuota(peekStale<UsageResponse>(userId, CACHE_KEYS.usage), quota));
}

// Same for Pally's look: a finished conversation changes current_axes. Traits and
// everything else stay stale and reload on the next read.
export function patchStaleProfileAxes(userId: string, axes: Axes): void {
  const cached = peekStale<ProfileResponse>(userId, CACHE_KEYS.profile);
  if (!cached) return;
  writeStale(userId, CACHE_KEYS.profile, { profile: { ...cached.profile, current_axes: axes } });
}

export function loadUsage(userId: string): Promise<UsageResponse> {
  return read(userId, CACHE_KEYS.usage, USAGE_TTL_MS, () => pallyApi.getUsage());
}

export function loadSubscription(userId: string): Promise<SubscriptionResponse> {
  return read(userId, CACHE_KEYS.subscription, ROUTE_DATA_TTL_MS, () => pallyApi.getSubscription());
}

export function loadProfile(userId: string): Promise<ProfileResponse> {
  return read(userId, CACHE_KEYS.profile, ROUTE_DATA_TTL_MS, () => pallyApi.getProfile());
}

export function cacheProfile(userId: string, response: ProfileResponse): void {
  write(userId, CACHE_KEYS.profile, ROUTE_DATA_TTL_MS, response);
}

export function loadAchievements(userId: string): Promise<AchievementsResponse> {
  return read(userId, CACHE_KEYS.achievements, ROUTE_DATA_TTL_MS, () => pallyApi.getAchievements());
}

export function loadHistoryPage(userId: string, cursor?: string): Promise<ConversationListResponse> {
  const key = `${CACHE_KEYS.history}${cursorKey(cursor)}`;
  return read(userId, key, ROUTE_DATA_TTL_MS, () => (
    pallyApi.listConversations({ status: "completed", cursor, limit: 20 })
  ));
}

export function reloadHistoryFirstPage(userId: string): Promise<ConversationListResponse> {
  invalidate(userId, `${CACHE_KEYS.history}first`);
  return loadHistoryPage(userId);
}

export function loadConversationPage(
  userId: string,
  conversationId: string,
  cursor?: string,
): Promise<ConversationDetailResponse> {
  const key = `${CACHE_KEYS.conversation}${conversationId}:${cursorKey(cursor)}`;
  return read(userId, key, CONVERSATION_TTL_MS, () => (
    pallyApi.getConversation(conversationId, { cursor, limit: 50 })
  ));
}

// Evict rather than expire: usage and subscription change with plan changes, so an
// old value must not be painted before the reload. Turns re-seed it via patchStaleUsage.
export function invalidateUsage(userId: string): void {
  evict(userId, CACHE_KEYS.usage);
}

export function invalidateProfile(userId: string): void {
  invalidate(userId, CACHE_KEYS.profile);
}

export function invalidateSubscription(userId: string): void {
  evict(userId, CACHE_KEYS.subscription);
}

export function invalidateConversationData(userId: string, conversationId?: string): void {
  invalidate(userId, CACHE_KEYS.history);
  if (conversationId) invalidate(userId, `${CACHE_KEYS.conversation}${conversationId}:`);
  invalidate(userId, CACHE_KEYS.achievements);
}

export function clearUserRouteData(userId: string): void {
  clearUser(userId);
  if (rememberedUserId === userId) rememberedUserId = null;
}

export async function invalidateCurrentUserConversationData(conversationId?: string): Promise<void> {
  const userId = await getCurrentUserId();
  invalidateConversationData(userId, conversationId);
}

export async function prefetchRouteData(href: string, userId?: string): Promise<void> {
  const scope = userId ?? await getCurrentUserId();
  if (href.startsWith("/home")) {
    await Promise.all([
      loadProfile(scope),
      prefetch(scope, CACHE_KEYS.usage, USAGE_TTL_MS, () => pallyApi.getUsage()),
      prefetch(scope, CACHE_KEYS.subscription, ROUTE_DATA_TTL_MS, () => pallyApi.getSubscription()),
    ]);
    return;
  }
  if (href.startsWith("/history")) {
    await prefetch(scope, `${CACHE_KEYS.history}first`, ROUTE_DATA_TTL_MS, () => (
      pallyApi.listConversations({ status: "completed", limit: 20 })
    ));
    return;
  }
  if (href.startsWith("/ranking")) {
    await prefetch(scope, CACHE_KEYS.achievements, ROUTE_DATA_TTL_MS, () => pallyApi.getAchievements());
    return;
  }
  if (href.startsWith("/my")) {
    await prefetch(scope, CACHE_KEYS.profile, ROUTE_DATA_TTL_MS, () => pallyApi.getProfile());
  }
}

type NetworkInformationLike = {
  effectiveType?: string;
  saveData?: boolean;
};

function canPrefetchOnCurrentNetwork(): boolean {
  const connection = (navigator as Navigator & { connection?: NetworkInformationLike }).connection;
  if (!connection) return false;
  if (connection.saveData) return false;
  return connection.effectiveType === "4g";
}

export function schedulePrimaryRoutePrefetch(userId: string): () => void {
  if (!canPrefetchOnCurrentNetwork()) return () => undefined;

  const run = () => {
    void Promise.allSettled([
      prefetchRouteData("/history", userId),
      prefetchRouteData("/ranking", userId),
      prefetchRouteData("/my", userId),
    ]).then((results) => {
      for (const result of results) {
        if (result.status === "rejected") console.error("Route data prefetch failed", result.reason);
      }
    });
  };

  const idleWindow = window as Window & {
    cancelIdleCallback?: (handle: number) => void;
    requestIdleCallback?: (callback: () => void, options?: { timeout: number }) => number;
  };
  if (idleWindow.requestIdleCallback) {
    const handle = idleWindow.requestIdleCallback(run, { timeout: 2_000 });
    return () => {
      if (idleWindow.cancelIdleCallback) idleWindow.cancelIdleCallback(handle);
    };
  }

  const handle = window.setTimeout(run, 500);
  return () => window.clearTimeout(handle);
}
