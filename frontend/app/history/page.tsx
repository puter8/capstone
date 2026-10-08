"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { ConversationNoteCard } from "@/components/feedback/ConversationNoteCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { ContentSkeleton } from "@/components/ui/ContentSkeleton";
import { PallyApiError } from "@/lib/api";
import type { ConversationListItem, ConversationListResponse } from "@/lib/api";
import { isTitlePending } from "@/lib/api/pending-titles";
import { getCurrentUserId, loadHistoryPage, peekHistorySnapshot, reloadHistoryFirstPage } from "@/lib/api/route-data";
import type { RouteSnapshot } from "@/lib/api/route-data";

const TITLE_POLL_INTERVAL_MS = 1_500;

// Returning to this tab paints the last known list while the fresh read runs.
// Client-only: on a hard load the cache is empty, so server and client markup match.
function readHistorySnapshot(): RouteSnapshot<ConversationListResponse> | null {
  if (typeof window === "undefined") return null;
  return peekHistorySnapshot();
}

export default function HistoryPage() {
  const router = useRouter();
  const [snapshot] = useState(readHistorySnapshot);
  const [items, setItems] = useState<ConversationListItem[]>(snapshot ? snapshot.data.items : []);
  const [isLoading, setIsLoading] = useState(snapshot === null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(snapshot ? snapshot.data.next_cursor : null);
  const [error, setError] = useState<string | null>(null);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);
  // Set once the session is verified and the fresh first page has arrived. Paging and
  // title polling wait for it, even when the list is already painted from the snapshot.
  const [verifiedUserId, setVerifiedUserId] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
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
          router.replace("/");
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
        router.replace("/");
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
    const root = listRef.current;
    const sentinel = sentinelRef.current;
    if (!root || !sentinel || !nextCursor || loadMoreError) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMore();
    }, { root, rootMargin: "120px" });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore, loadMoreError, nextCursor, verifiedUserId]);

  if (isLoading) {
    return (
      <MobileShell minHeight={640}>
        <h1 className="absolute left-5 top-[79px] text-display text-primary">History</h1>
        <ContentSkeleton className="absolute left-5 right-5 top-[180px]" rows={4} />
        <BottomNav />
      </MobileShell>
    );
  }

  return (
    <MobileShell minHeight={640}>
      <h1 className="absolute left-5 top-[79px] text-display text-primary">History</h1>
      {!error && items.length === 0 ? (
        <p className="absolute left-5 right-5 top-1/2 -translate-y-1/2 text-center text-body text-text-tertiary">
          아직 대화 기록이 없어요!
        </p>
      ) : null}
      <div ref={listRef} className="absolute bottom-[134px] left-5 right-5 top-[180px] flex flex-col gap-3 overflow-y-auto pb-4">
        {error ? (
          <div className="flex flex-col items-center gap-2 text-center text-body text-red-600" role="alert">
            <p>{error}</p>
            <button className="rounded-full border border-red-600 px-4 py-1 text-body-2" onClick={() => window.location.reload()} type="button">다시 시도</button>
          </div>
        ) : null}
        {items.map((item) => (
          <ConversationNoteCard
            conversationId={item.id}
            feedbackHref={`/history/feedback?conversation_id=${encodeURIComponent(item.id)}`}
            key={item.id}
            title={item.title ?? item.preview ?? "Pally와 나눈 대화"}
            titlePending={pendingTitleIds.has(item.id)}
          />
        ))}
        <div aria-hidden="true" className="h-px shrink-0" ref={sentinelRef} />
        {isLoadingMore ? <p className="py-2 text-center text-body-2 text-text-tertiary" role="status">기록을 더 불러오고 있어요</p> : null}
        {loadMoreError ? (
          <div className="flex flex-col items-center gap-2 py-2 text-center text-body-2 text-red-600" role="alert">
            <p>{loadMoreError}</p>
            <button className="rounded-full border border-red-600 px-4 py-1" onClick={() => { void loadMore(); }} type="button">다시 시도</button>
          </div>
        ) : null}
      </div>
      <BottomNav />
    </MobileShell>
  );
}
