import type {
  AchievementsResponse,
  ConversationDetailResponse,
  ConversationListItem,
  ConversationListResponse,
  DailyExpressionResponse,
  EnergyBaselineResponse,
  ProfileResponse,
  Subscription,
  SubscriptionResponse,
  UsageQuota,
  UsageResponse,
} from "@/lib/api/contracts";
import { PallyApiError } from "@/lib/api/contracts";
import { isFallbackTitle } from "@/lib/api/pending-titles";
import { forgetRememberedAxes, peekRememberedAxes } from "@/lib/api/remembered-axes";
import { SESSION_ERROR_MESSAGE } from "@/lib/api/error-messages";
import { pallyApi } from "@/lib/api";
import { clearUser, evict, invalidate, peekStale, prefetch, read, write, writeStale } from "@/lib/api/query-cache";
import { supabase } from "@/lib/supabase/client";
import type { Axes } from "@/lib/types/character";

// Usage changes in three ways this tab knows exactly: a turn (its response carries the
// new count), the daily reset (reset_at) and a plan change (syncSubscription). The
// lifetime only bounds what it cannot see, turns taken on another device, and the
// server refuses a turn over the limit whatever is painted here.
const USAGE_TTL_MS = 60_000;
const CONVERSATION_TTL_MS = 30_000;
// A page of a finished conversation with no extraction left cannot change on its own.
// Reopening, a new turn and completion all invalidate the entry, so the only thing a
// re-read buys is the same bytes again. The cache is per tab and in memory, so this is
// in practice "keep it for this tab" rather than a day.
const SETTLED_CONVERSATION_TTL_MS = 12 * 60 * 60 * 1000;
const BASELINE_TTL_MS = 12 * 60 * 60 * 1000;
const ROUTE_DATA_TTL_MS = 60_000;

const CACHE_KEYS = {
  achievements: "achievements",
  energyBaseline: "energy-baseline",
  conversation: "conversation:",
  dailyExpression: "daily-expression:",
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
  /** Null when no usage is known to still hold: home then paints without the count. */
  usage: UsageResponse | null;
  profile: ProfileResponse["profile"];
  subscription: SubscriptionResponse["subscription"] | null;
}

/**
 * Whether a usage value still describes the current day. The daily count resets at
 * `reset_at`, so a value read before that moment is known to be wrong after it and
 * must not be painted, however recently it was loaded.
 */
export function isUsageCurrent(usage: UsageResponse, now: number = Date.now()): boolean {
  const resetAt = Date.parse(usage.reset_at);
  return !Number.isNaN(resetAt) && now < resetAt;
}

// Never past the daily reset: a count read a second before midnight is wrong a second after.
function usageTtl(usage: UsageResponse): number {
  const resetAt = Date.parse(usage.reset_at);
  if (Number.isNaN(resetAt)) return 0;
  return Math.max(0, Math.min(USAGE_TTL_MS, resetAt - Date.now()));
}

// Last known home data for the remembered user, even if expired. Null until the user
// has loaded the profile once, so a cold start still shows the loader. Usage is left
// out when it was evicted or its day has ended; the screen does not wait for it.
export function peekHomeSnapshot(): HomeSnapshot | null {
  if (!rememberedUserId) return null;
  const profile = peekStale<ProfileResponse>(rememberedUserId, CACHE_KEYS.profile);
  if (!profile) return null;
  const usage = peekStale<UsageResponse>(rememberedUserId, CACHE_KEYS.usage);
  const subscription = peekStale<SubscriptionResponse>(rememberedUserId, CACHE_KEYS.subscription);
  return {
    userId: rememberedUserId,
    usage: usage && isUsageCurrent(usage) ? usage : null,
    profile: profile.profile,
    subscription: subscription ? subscription.subscription : null,
  };
}

export interface RouteSnapshot<T> {
  userId: string;
  data: T;
}

// Last known tab data for the remembered user, even if expired, so returning to a tab
// paints at once. The screen still verifies the session and replaces it with a fresh read.
function peekRouteSnapshot<T>(key: string): RouteSnapshot<T> | null {
  if (!rememberedUserId) return null;
  const data = peekStale<T>(rememberedUserId, key);
  return data === undefined ? null : { userId: rememberedUserId, data };
}

export function peekHistorySnapshot(): RouteSnapshot<ConversationListResponse> | null {
  return peekRouteSnapshot(`${CACHE_KEYS.history}first`);
}

export function peekAchievementsSnapshot(): RouteSnapshot<AchievementsResponse> | null {
  return peekRouteSnapshot(CACHE_KEYS.achievements);
}

export function peekProfileSnapshot(): RouteSnapshot<ProfileResponse> | null {
  return peekRouteSnapshot(CACHE_KEYS.profile);
}

/**
 * Last known plan, or null when it is not known. A paid period that has ended since
 * the value was read is not known either: the plan label must stay empty until the
 * fresh read rather than show a plan the user may no longer have.
 */
export function peekSubscriptionSnapshot(): RouteSnapshot<SubscriptionResponse> | null {
  const snapshot = peekRouteSnapshot<SubscriptionResponse>(CACHE_KEYS.subscription);
  if (!snapshot) return null;
  const { entitled, current_period_end: periodEnd } = snapshot.data.subscription;
  if (entitled && periodEnd && Date.now() >= Date.parse(periodEnd)) return null;
  return snapshot;
}

/**
 * The list row of a conversation, from the first page of the list if this tab has it.
 * Lets the detail screen show the title and date the user just tapped while the
 * detail itself is still loading.
 */
export function peekHistoryItem(conversationId: string): ConversationListItem | null {
  const list = peekHistorySnapshot();
  return list?.data.items.find((item) => item.id === conversationId) ?? null;
}

function expressionDate(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}

export function peekDailyExpressionSnapshot(): RouteSnapshot<DailyExpressionResponse> | null {
  const snapshot = peekRouteSnapshot<DailyExpressionResponse>(`${CACHE_KEYS.dailyExpression}${expressionDate()}`);
  if (!snapshot || snapshot.data.date !== expressionDate()) return null;
  const profile = peekStale<ProfileResponse>(snapshot.userId, CACHE_KEYS.profile);
  if (profile && profile.profile.english_level !== snapshot.data.expression.level) return null;
  return snapshot;
}

export function loadDailyExpression(userId: string): Promise<DailyExpressionResponse> {
  return read(userId, `${CACHE_KEYS.dailyExpression}${expressionDate()}`, ROUTE_DATA_TTL_MS, () => pallyApi.getDailyExpression());
}

export function invalidateDailyExpression(userId: string): void {
  evict(userId, CACHE_KEYS.dailyExpression);
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

// After a turn the server value is already known from the response, so it is stored
// as a fresh read: returning to home neither flashes the old count nor asks again.
export function cacheTurnUsage(userId: string, quota: UsageQuota): void {
  const usage = usageFromQuota(peekStale<UsageResponse>(userId, CACHE_KEYS.usage), quota);
  write(userId, CACHE_KEYS.usage, usageTtl(usage), usage);
}

// Same for Pally's look: a finished conversation changes current_axes. Traits and
// everything else stay stale and reload on the next read.
export function patchStaleProfileAxes(userId: string, axes: Axes): void {
  const cached = peekStale<ProfileResponse>(userId, CACHE_KEYS.profile);
  if (!cached) return;
  writeStale(userId, CACHE_KEYS.profile, { profile: { ...cached.profile, current_axes: axes } });
}

export function loadUsage(userId: string): Promise<UsageResponse> {
  return read(userId, CACHE_KEYS.usage, usageTtl, () => pallyApi.getUsage());
}

export function loadSubscription(userId: string): Promise<SubscriptionResponse> {
  return read(userId, CACHE_KEYS.subscription, ROUTE_DATA_TTL_MS, () => pallyApi.getSubscription());
}

export function loadProfile(userId: string): Promise<ProfileResponse> {
  return read(userId, CACHE_KEYS.profile, ROUTE_DATA_TTL_MS, () => pallyApi.getProfile());
}

export function cacheProfile(userId: string, response: ProfileResponse): void {
  const previous = peekStale<ProfileResponse>(userId, CACHE_KEYS.profile);
  if (previous?.profile.english_level !== response.profile.english_level) {
    invalidateDailyExpression(userId);
    // The three daily tasks are the same at every level and a completed one stays
    // completed, so the old value is still paintable; it only needs a re-read.
    invalidate(userId, CACHE_KEYS.achievements);
  }
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

export function invalidateHistory(userId: string): void {
  invalidate(userId, CACHE_KEYS.history);
}

/**
 * Whether the user's voice is registered. Home waits for this before anything else,
 * because it decides whether to send the user to registration, so an uncached read
 * put a round trip in front of every visit.
 *
 * "required" is never kept: it is the answer that redirects, and it stops being true
 * the moment the user registers. Once registered or disabled it only changes through
 * deletion, which clears this user's cache entirely.
 */
export function loadEnergyBaseline(userId: string): Promise<EnergyBaselineResponse> {
  return read(
    userId, CACHE_KEYS.energyBaseline,
    (baseline: EnergyBaselineResponse) => (baseline.status === "required" ? 0 : BASELINE_TTL_MS),
    () => pallyApi.getEnergyBaseline(),
  );
}

/**
 * How long a loaded page of conversation detail is worth keeping. A completed
 * conversation is only settled once its feedback is extracted and its generated title
 * has replaced the first-utterance fallback; until then a re-read brings new content.
 */
function conversationPageTtl(detail: ConversationDetailResponse): number {
  const firstUtterance = detail.turns.find((turn) => turn.user_transcript)?.user_transcript ?? null;
  const settled = detail.conversation.status === "completed"
    && !detail.turns.some((turn) => turn.feedback_pending)
    && !isFallbackTitle(detail.conversation.title, firstUtterance);
  return settled ? SETTLED_CONVERSATION_TTL_MS : CONVERSATION_TTL_MS;
}

export function loadConversationPage(
  userId: string,
  conversationId: string,
  cursor?: string,
): Promise<ConversationDetailResponse> {
  const key = `${CACHE_KEYS.conversation}${conversationId}:${cursorKey(cursor)}`;
  return read(userId, key, conversationPageTtl, () => (
    pallyApi.getConversation(conversationId, { cursor, limit: 50 })
  ));
}

/**
 * The first page of a conversation already read in this tab, for painting the detail
 * screen without a spinner. Synchronous, so it runs before the session check; the
 * screen still verifies and replaces it. Undefined when nothing is cached.
 */
export function peekConversationPage(conversationId: string): ConversationDetailResponse | undefined {
  if (!rememberedUserId) return undefined;
  return peekStale<ConversationDetailResponse>(
    rememberedUserId, `${CACHE_KEYS.conversation}${conversationId}:${cursorKey()}`,
  );
}

/**
 * Re-read pages of one conversation through the cache, so what the detail screen polls
 * is also what it paints the next time it opens. Nothing else is touched: a page that
 * is still being extracted changes neither the list nor the achievements.
 */
export function reloadConversationPages(
  userId: string,
  conversationId: string,
  cursors: ReadonlyArray<string | undefined>,
): Promise<ConversationDetailResponse[]> {
  invalidate(userId, `${CACHE_KEYS.conversation}${conversationId}:`);
  return Promise.all(cursors.map((cursor) => loadConversationPage(userId, conversationId, cursor)));
}

// Evict rather than expire: usage and subscription change with plan changes, so an
// old value must not be painted before the reload. Turns re-seed it via cacheTurnUsage.
export function invalidateUsage(userId: string): void {
  evict(userId, CACHE_KEYS.usage);
}

export function invalidateProfile(userId: string): void {
  invalidate(userId, CACHE_KEYS.profile);
}

export function invalidateSubscription(userId: string): void {
  evict(userId, CACHE_KEYS.subscription);
}

function sameSubscription(a: Subscription, b: Subscription): boolean {
  return a.plan === b.plan
    && a.status === b.status
    && a.entitled === b.entitled
    && a.product_id === b.product_id
    && a.current_period_end === b.current_period_end
    && a.will_renew === b.will_renew
    && a.entitlements.length === b.entitlements.length
    && a.entitlements.every((entitlement) => b.entitlements.includes(entitlement));
}

/**
 * Reconcile the cache with a subscription just read from the server. Usage is dropped
 * only when the plan really differs from what was cached, so looking at the billing
 * screen does not empty it. With nothing cached there is nothing to compare against,
 * and it is dropped as before. The subscription itself is the server's current answer
 * and is kept as such, which is also what the next comparison is made against.
 */
export function syncSubscription(userId: string, latest: Subscription): void {
  const cached = peekStale<SubscriptionResponse>(userId, CACHE_KEYS.subscription);
  if (!cached || !sameSubscription(cached.subscription, latest)) invalidateUsage(userId);
  write(userId, CACHE_KEYS.subscription, ROUTE_DATA_TTL_MS, { subscription: latest });
}

export function invalidateConversationData(userId: string, conversationId?: string): void {
  invalidate(userId, CACHE_KEYS.history);
  if (conversationId) invalidate(userId, `${CACHE_KEYS.conversation}${conversationId}:`);
  invalidate(userId, CACHE_KEYS.achievements);
}

export function clearUserRouteData(userId: string): void {
  clearUser(userId);
  if (rememberedUserId === userId) rememberedUserId = null;
  // Pally's look outlives the tab, so dropping a user's data has to reach it too.
  // Only this user's: signing out must not wipe the look of whoever logs in next.
  if (peekRememberedAxes()?.userId === userId) forgetRememberedAxes();
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
      loadDailyExpression(scope),
      loadUsage(scope),
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
  // Safari, and so every iOS browser, has no Network Information API. Treat it as a
  // normal connection instead of never prefetching on iPhones.
  if (!connection) return true;
  if (connection.saveData) return false;
  return connection.effectiveType === undefined || connection.effectiveType === "4g";
}

const PRIMARY_ROUTES = [
  { href: "/history", key: `${CACHE_KEYS.history}first` },
  { href: "/ranking", key: CACHE_KEYS.achievements },
  { href: "/my", key: CACHE_KEYS.profile },
] as const;

/**
 * Warm the other tabs while the current one is idle. `onlyMissing` skips a tab that
 * already has a value to paint, even an expired one: that tab opens without a loader
 * and re-reads itself, so asking again here would only add a request per visit.
 */
export function schedulePrimaryRoutePrefetch(userId: string, options: { onlyMissing?: boolean } = {}): () => void {
  if (!canPrefetchOnCurrentNetwork()) return () => undefined;

  const run = () => {
    const targets = options.onlyMissing
      ? PRIMARY_ROUTES.filter((route) => peekStale(userId, route.key) === undefined)
      : PRIMARY_ROUTES;
    void Promise.allSettled(targets.map((route) => prefetchRouteData(route.href, userId))).then((results) => {
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
