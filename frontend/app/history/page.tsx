"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { BottomNav } from "@/components/v2/BottomNav";
import { Button } from "@/components/v2/Button";
import { SessionCard, SessionCardSkeleton } from "@/components/v2/SessionCard";
import { Stage } from "@/components/v2/Stage";
import { PallyApiError } from "@/lib/api";
import type { ConversationListItem, ConversationListResponse } from "@/lib/api";
import { isTitlePending } from "@/lib/api/pending-titles";
import { resumeConversation } from "@/lib/api/resume-conversation";
import { getCurrentUserId, loadHistoryPage, peekHistorySnapshot, reloadHistoryFirstPage } from "@/lib/api/route-data";
import type { RouteSnapshot } from "@/lib/api/route-data";
import { formatDayGroup } from "@/lib/v2/format";
import { routes } from "@/lib/v2/routes";

const TITLE_POLL_INTERVAL_MS = 1_500;

// Returning to this tab paints the last known list while the fresh read runs.
// Client-only: on a hard load the cache is empty, so server and client markup match.
function readHistorySnapshot(): RouteSnapshot<ConversationListResponse> | null {
  if (typeof window === "undefined") return null;
  return peekHistorySnapshot();
}

type DayGroup = { label: string; items: ConversationListItem[] };

function groupByDay(items: readonly ConversationListItem[]): DayGroup[] {
  const now = new Date();
  const groups: DayGroup[] = [];
  for (const item of items) {
    const label = formatDayGroup(item.started_at, now);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.items.push(item);
    else groups.push({ label, items: [item] });
  }
  return groups;
}

function PageHeading() {
  return (
    <header className="flex flex-col gap-[6px] px-p-5 pb-p-4 pt-[28px]">
      <h1 className="text-p-heading tracking-[-0.02em] text-p-text">피드백</h1>
      <p className="text-p-small text-p-text-secondary">대화를 마치면 고친 표현이 여기에 모여요.</p>
    </header>
  );
}

export default function HistoryV2Page() {
  const router = useRouter();
  const [snapshot] = useState(readHistorySnapshot);
  const [items, setItems] = useState<ConversationListItem[]>(snapshot ? snapshot.data.items : []);
  const [isLoading, setIsLoading] = useState(snapshot === null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(snapshot ? snapshot.data.next_cursor : null);
  const [error, setError] = useState<string | null>(null);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);
  const [resumingId, setResumingId] = useState<string | null>(null);
  const [resumeError, setResumeError] = useState<{ id: string; message: string } | null>(null);
  // Set once the session is verified and the fresh first page has arrived. Paging and
  // title polling wait for it, even when the list is already painted from the snapshot.
  const [verifiedUserId, setVerifiedUserId] = useState<string | null>(null);
  const loadingMoreRef = useRef(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;

    const loadFirstPage = async () => {
      const userId = await getCurrentUserId();
      if (!active) return;
      if (snapshot && snapshot.userId !== userId) {
        // The painted list belongs to a previous account: hide it until the fresh read.
        setItems([]);
        setNextCursor(null);
        setIsLoading(true);
      }
      const response = await loadHistoryPage(userId);
      if (!active) return;
      setItems(response.items);
      setNextCursor(response.next_cursor);
      setVerifiedUserId(userId);
    };

    void loadFirstPage()
      .catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") {
          router.replace(routes.login);
          return;
        }
        if (active) setError(caught instanceof Error ? caught.message : "대화 기록을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [router, snapshot]);

  const loadMore = useCallback(async () => {
    const userId = verifiedUserId;
    const cursor = nextCursor;
    if (!userId || !cursor || loadingMoreRef.current) return;

    loadingMoreRef.current = true;
    setIsLoadingMore(true);
    setLoadMoreError(null);
    try {
      const response = await loadHistoryPage(userId, cursor);
      setItems((current) => {
        const existingIds = new Set(current.map((item) => item.id));
        return [...current, ...response.items.filter((item) => !existingIds.has(item.id))];
      });
      setNextCursor(response.next_cursor);
    } catch (caught) {
      if (caught instanceof PallyApiError && caught.code === "unauthorized") {
        router.replace(routes.login);
        return;
      }
      setLoadMoreError(caught instanceof Error ? caught.message : "대화 기록을 더 불러오지 못했어요.");
    } finally {
      loadingMoreRef.current = false;
      setIsLoadingMore(false);
    }
  }, [nextCursor, router, verifiedUserId]);

  const now = Date.now();
  const pendingTitleIds = new Set(items.filter((item) => isTitlePending(item.id, item.title, now)).map((item) => item.id));
  const hasPendingTitle = pendingTitleIds.size > 0;

  // Poll the first page until background-generated titles arrive (or the wait expires).
  useEffect(() => {
    const userId = verifiedUserId;
    if (!hasPendingTitle || !userId) return;
    let active = true;
    const timer = window.setTimeout(() => {
      void reloadHistoryFirstPage(userId)
        .then((response) => {
          if (!active) return;
          const refreshed = new Map(response.items.map((item) => [item.id, item]));
          setItems((current) => current.map((item) => refreshed.get(item.id) ?? item));
        })
        .catch((caught: unknown) => {
          console.error("Conversation title refresh failed", caught);
          // Re-render so expired pending titles fall back instead of spinning forever.
          if (active) setItems((current) => [...current]);
        });
    }, TITLE_POLL_INTERVAL_MS);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [hasPendingTitle, items, verifiedUserId]);

  useEffect(() => {
    if (!verifiedUserId) return;
    const sentinel = sentinelRef.current;
    if (!sentinel || !nextCursor || loadMoreError) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMore();
    }, { rootMargin: "160px" });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore, loadMoreError, nextCursor, verifiedUserId]);

  const resume = useCallback(async (conversationId: string) => {
    if (resumingId) return;
    setResumingId(conversationId);
    setResumeError(null);
    try {
      const href = await resumeConversation(conversationId, routes.home);
      router.push(href);
    } catch (caught) {
      setResumeError({ id: conversationId, message: caught instanceof Error ? caught.message : "대화를 재개하지 못했어요." });
      setResumingId(null);
    }
  }, [resumingId, router]);

  const groups = useMemo(() => groupByDay(items), [items]);

  if (isLoading) {
    return (
      <AppFrame withBottomNav>
        <PageHeading />
        <div aria-busy="true" className="flex flex-col gap-p-3 px-p-5" role="status">
          <span className="sr-only">대화 기록을 불러오고 있어요</span>
          <SessionCardSkeleton />
          <SessionCardSkeleton />
          <SessionCardSkeleton />
        </div>
        <BottomNav />
      </AppFrame>
    );
  }

  return (
    <AppFrame withBottomNav>
      <PageHeading />
      {error ? (
        <div className="flex flex-col items-center gap-p-4 px-p-5 pt-p-8 text-center" role="alert">
          <Stage glow={false} size="compact" />
          <div className="flex flex-col gap-p-2">
            <h2 className="text-p-section text-p-text">기록을 불러오지 못했어요</h2>
            <p className="text-p-body text-p-text-secondary">{error}</p>
          </div>
          <Button onClick={() => window.location.reload()} variant="secondary">
            다시 시도
          </Button>
        </div>
      ) : null}
      {!error && items.length === 0 ? (
        <div className="flex flex-col items-center gap-p-4 px-p-5 pt-p-8 text-center">
          <Stage glow={false} size="compact" />
          <div className="flex flex-col gap-p-2">
            <h2 className="text-p-section text-p-text">아직 나눈 대화가 없어요</h2>
            <p className="text-p-body text-p-text-secondary">첫 대화를 마치면 Pally가 고친 표현을 여기에 모아 둘게요.</p>
          </div>
          <Button onClick={() => router.push(routes.home)}>대화하러 가기</Button>
        </div>
      ) : null}
      {groups.length > 0 ? (
        <div className="flex flex-col gap-p-6 px-p-5 pb-p-6 pt-p-1">
          {groups.map((group) => (
            <section aria-label={group.label} className="flex flex-col gap-p-3" key={group.label}>
              <h2 className="text-p-eyebrow text-p-text-muted">{group.label}</h2>
              {group.items.map((item) => (
                <SessionCard
                  feedbackHref={routes.feedback(item.id)}
                  item={item}
                  key={item.id}
                  onResume={() => {
                    void resume(item.id);
                  }}
                  resumeError={resumeError?.id === item.id ? resumeError.message : null}
                  resuming={resumingId === item.id}
                  titlePending={pendingTitleIds.has(item.id)}
                />
              ))}
            </section>
          ))}
          <div aria-hidden="true" className="h-px shrink-0" ref={sentinelRef} />
          {isLoadingMore ? (
            <p className="py-p-2 text-center text-p-small text-p-text-muted" role="status">
              기록을 더 불러오고 있어요
            </p>
          ) : null}
          {loadMoreError ? (
            <div className="flex flex-col items-center gap-p-2 py-p-2 text-center text-p-small text-p-error" role="alert">
              <p>{loadMoreError}</p>
              <Button onClick={() => { void loadMore(); }} size="compact" variant="secondary">
                다시 시도
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}
      <BottomNav />
    </AppFrame>
  );
}
