"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { FeedbackCard } from "@/components/feedback/FeedbackCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { PageLoader } from "@/components/ui/PageLoader";
import { PageHeader } from "@/components/ui/PageHeader";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { FeedbackItem } from "@/lib/api";
import { getCurrentUserId, invalidateConversationData, loadConversationPage, loadHistoryPage } from "@/lib/api/route-data";
import { recordFeedbackItemOpened } from "@/lib/analytics/activity-events";

export default function FeedbackPage() {
  const router = useRouter();
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);
  const [feedbackPending, setFeedbackPending] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [pollingStopped, setPollingStopped] = useState(false);
  const [isActiveConversation, setIsActiveConversation] = useState(false);
  const loadedCursorsRef = useRef<Array<string | undefined>>([undefined]);
  const refreshingRef = useRef(false);
  const openedFeedbackRef = useRef(new Set<string>());
  const conversationIdRef = useRef<string | null>(null);
  const listRef = useRef<HTMLElement | null>(null);
  const loadingMoreRef = useRef(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const userIdRef = useRef<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadFeedback = async () => {
      try {
        const userId = await getCurrentUserId();
        const requestedId = new URLSearchParams(window.location.search).get("conversation_id");
        const conversationId = requestedId ?? (await loadHistoryPage(userId)).items[0]?.id;
        if (!conversationId) return;
        userIdRef.current = userId;
        conversationIdRef.current = conversationId;

        const detail = await loadConversationPage(userId, conversationId);

        if (active) {
          const nextFeedback = detail.turns.flatMap((turn) => turn.feedback);
          setFeedback(nextFeedback);
          setFeedbackPending(detail.turns.some((turn) => turn.feedback_pending));
          setIsActiveConversation(detail.conversation.status === "active");
          setNextCursor(detail.next_cursor);
          void pallyApi.recordActivityEvent({
            event_id: crypto.randomUUID(),
            event_type: "conversation_detail_opened",
            occurred_at: new Date().toISOString(),
            conversation_id: conversationId,
          }).catch((eventError: unknown) => console.error("Activity event failed", eventError));
        }
      } catch (caught) {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") {
          router.replace("/");
          return;
        }
        if (active) setError(caught instanceof Error ? caught.message : "피드백을 불러오지 못했어요.");
      } finally {
        if (active) setIsLoading(false);
      }
    };

    void loadFeedback();
    return () => {
      active = false;
    };
  }, [router]);

  const loadMore = useCallback(async () => {
    const userId = userIdRef.current;
    const conversationId = conversationIdRef.current;
    const cursor = nextCursor;
    if (!userId || !conversationId || !cursor || loadingMoreRef.current || refreshingRef.current) return;

    loadingMoreRef.current = true;
    setIsLoadingMore(true);
    setLoadMoreError(null);
    try {
      const detail = await loadConversationPage(userId, conversationId, cursor);
      loadedCursorsRef.current.push(cursor);
      const nextFeedback = detail.turns.flatMap((turn) => turn.feedback);
      setFeedback((current) => [...current, ...nextFeedback]);
      setFeedbackPending((current) => current || detail.turns.some((turn) => turn.feedback_pending));
      setNextCursor(detail.next_cursor);
    } catch (caught) {
      if (caught instanceof PallyApiError && caught.code === "unauthorized") {
        router.replace("/");
        return;
      }
      setLoadMoreError(caught instanceof Error ? caught.message : "피드백을 더 불러오지 못했어요.");
    } finally {
      loadingMoreRef.current = false;
      setIsLoadingMore(false);
    }
  }, [nextCursor, router]);

  // Refresh every loaded page so completed extraction replaces pending items,
  // including feedback outside the first page, without appending duplicates.
  useEffect(() => {
    if (isLoading || !feedbackPending || isActiveConversation) return;
    let cancelled = false;
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout>;
    setPollingStopped(false);
    setRefreshError(null);
    const poll = async () => {
      if (loadingMoreRef.current || refreshingRef.current) {
        timer = setTimeout(() => { void poll(); }, 3000);
        return;
      }
      const userId = userIdRef.current;
      const conversationId = conversationIdRef.current;
      if (!userId || !conversationId) return;
      refreshingRef.current = true;
      setIsRefreshing(true);
      try {
        const pages = await Promise.all(loadedCursorsRef.current.map((cursor) => (
          pallyApi.getConversation(conversationId, { cursor, limit: 50 })
        )));
        if (cancelled) return;
        const turns = pages.flatMap((page) => page.turns);
        const pending = turns.some((turn) => turn.feedback_pending);
        setFeedback(turns.flatMap((turn) => turn.feedback));
        setFeedbackPending(pending);
        setIsActiveConversation(pages[0].conversation.status === "active");
        setNextCursor(pages[pages.length - 1].next_cursor);
        invalidateConversationData(userId, conversationId);
        attempts += 1;
        if (pending && attempts < 10 && pages[0].conversation.status === "completed") {
          timer = setTimeout(() => { void poll(); }, 3000);
        } else if (pending) {
          setPollingStopped(true);
        }
      } catch (caught) {
        console.error("Feedback refresh failed", caught);
        if (!cancelled) {
          setRefreshError(caught instanceof Error ? caught.message : "피드백을 다시 불러오지 못했어요.");
          setPollingStopped(true);
        }
      } finally {
        refreshingRef.current = false;
        if (!cancelled) setIsRefreshing(false);
      }
    };
    timer = setTimeout(() => { void poll(); }, 3000);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [feedbackPending, isActiveConversation, isLoading, refreshVersion]);

  useEffect(() => {
    if (isLoading || isRefreshing) return;
    const root = listRef.current;
    const sentinel = sentinelRef.current;
    if (!root || !sentinel || !nextCursor || loadMoreError) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMore();
    }, { root, rootMargin: "120px" });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [isLoading, isRefreshing, loadMore, loadMoreError, nextCursor]);

  const recordFeedbackOpen = useCallback((conversationId: string, item: FeedbackItem) => {
    const key = item.id ?? `${conversationId}:${item.original}:${item.corrected}`;
    if (openedFeedbackRef.current.has(key)) return;
    openedFeedbackRef.current.add(key);
    void recordFeedbackItemOpened(conversationId, item)
      .catch((eventError: unknown) => console.error("Activity event failed", eventError));
  }, []);

  if (isLoading) {
    return (
      <MobileShell minHeight={640}>
        <PageLoader />
      </MobileShell>
    );
  }

  return (
    <MobileShell minHeight={640}>
      <PageHeader
        backHref="/history"
        className="absolute left-0 top-[60px]"
        description="대화에서 받은 피드백을 확인해보세요."
        title="Feedback"
        variant="back"
      />
      {!error && !feedbackPending && feedback.length === 0 ? (
        <p className="absolute inset-x-4 top-[399px] text-center text-body text-text-tertiary">
          아직 피드백이 없어요!
        </p>
      ) : null}
      <section ref={listRef} aria-label="대화 피드백" className="absolute bottom-[126px] left-[21px] right-[19px] top-[188px] flex flex-col gap-3 overflow-y-auto pb-4">
        {error ? (
          <div className="flex flex-col items-center gap-2 text-center text-body text-red-600" role="alert">
            <p>{error}</p>
            <button className="rounded-full border border-red-600 px-4 py-1 text-body-2" onClick={() => window.location.reload()} type="button">다시 시도</button>
          </div>
        ) : null}
        {feedbackPending ? (
          <div className="rounded-2xl bg-amber-50 px-4 py-3 text-body-2 text-text-secondary" role="status">
            {isActiveConversation ? "대화를 종료하면 피드백을 정리해요." : pollingStopped ? "피드백 정리에 시간이 걸리고 있어요. 잠시 후 다시 확인해 주세요." : "대화 피드백을 정리하고 있어요. 준비되면 자동으로 표시돼요."}
            {refreshError ? <p className="mt-2 text-red-600" role="alert">{refreshError}</p> : null}
            {pollingStopped && !isActiveConversation ? <button className="mt-2 min-h-11 underline underline-offset-4" onClick={() => setRefreshVersion((version) => version + 1)} type="button">다시 확인</button> : null}
          </div>
        ) : null}
        {feedback.map((item, index) => (
          <FeedbackCard
            corrected={item.corrected}
            explanation={item.explanation_ko}
            key={`${item.original}-${index}`}
            onOpen={() => {
              const conversationId = conversationIdRef.current;
              if (conversationId) recordFeedbackOpen(conversationId, item);
            }}
            original={item.original}
          />
        ))}
        <div aria-hidden="true" className="h-px shrink-0" ref={sentinelRef} />
        {isLoadingMore ? <p className="py-2 text-center text-body-2 text-text-tertiary" role="status">피드백을 더 불러오고 있어요</p> : null}
        {loadMoreError ? (
          <div className="flex flex-col items-center gap-2 py-2 text-center text-body-2 text-red-600" role="alert">
            <p>{loadMoreError}</p>
            <button className="rounded-full border border-red-600 px-4 py-1" onClick={() => { void loadMore(); }} type="button">다시 시도</button>
          </div>
        ) : null}
      </section>
      <BottomNav />
    </MobileShell>
  );
}
