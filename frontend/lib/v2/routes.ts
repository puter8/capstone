/**
 * Route table for the v2 design.
 *
 * Every link and redirect goes through here. The design now uses root routes;
 * keep the existing helper names until the follow-up cleanup.
 */
export const V2_BASE = "";

export function v2Path(path: string): string {
  if (!path.startsWith("/")) throw new Error(`v2Path expects an absolute path, got "${path}"`);
  const joined = `${V2_BASE}${path}`;
  return joined.length > 1 && joined.endsWith("/") ? joined.slice(0, -1) : joined;
}

export const routes = {
  login: v2Path("/"),
  authCallback: v2Path("/auth/callback"),
  home: v2Path("/home"),
  onboarding: v2Path("/onboarding"),
  onboardingVoice: v2Path("/onboarding?step=voice"),
  history: v2Path("/history"),
  feedback: (conversationId: string) =>
    v2Path(`/history/feedback?conversation_id=${encodeURIComponent(conversationId)}`),
  ranking: v2Path("/ranking"),
  my: v2Path("/my"),
  level: v2Path("/settings/level"),
  plans: v2Path("/settings/plans"),
} as const;

export type NavItemId = "home" | "history" | "ranking" | "my";

/**
 * Bottom navigation items. `dataKey` matches `href` at the root and is kept
 * for compatibility with prefetchRouteData until the follow-up cleanup.
 */
export const NAV_ITEMS: ReadonlyArray<{ id: NavItemId; href: string; dataKey: string; label: string }> = [
  { id: "home", href: routes.home, dataKey: "/home", label: "홈" },
  { id: "history", href: routes.history, dataKey: "/history", label: "피드백" },
  { id: "ranking", href: routes.ranking, dataKey: "/ranking", label: "업적" },
  { id: "my", href: routes.my, dataKey: "/my", label: "마이 페이지" },
];
