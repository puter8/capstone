"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { FeedbackCard } from "@/components/feedback/FeedbackCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { PageLoader } from "@/components/ui/PageLoader";
import { PageHeader } from "@/components/ui/PageHeader";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { ConversationTurn, FeedbackItem } from "@/lib/api";
import { getCurrentUserId, loadConversationPage, loadHistoryPage } from "@/lib/api/route-data";
import { recordFeedbackItemOpened } from "@/lib/analytics/activity-events";

type FeedbackGroup = { turnId: string; utterance: string | null; items: FeedbackItem[] };

// One card per utterance, so the full sentence shows every correction made to it.
function toFeedbackGroups(turns: readonly ConversationTurn[]): FeedbackGroup[] {
  return turns
    .filter((turn) => turn.feedback.length > 0)
    .map((turn) => ({ turnId: turn.id, utterance: turn.user_transcript, items: turn.feedback }));
}

export default function FeedbackPage() {
  const router = useRouter();
  const [feedback, setFeedback] = useState<FeedbackGroup[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);
  const [feedbackPending, setFeedbackPending] = useState(false);
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
          setFeedback(toFeedbackGroups(detail.turns));
          setFeedbackPending(detail.turns.some((turn) => turn.feedback_pending));
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
    if (!userId || !conversationId || !cursor || loadingMoreRef.current) return;

    loadingMoreRef.current = true;
    setIsLoadingMore(true);
    setLoadMoreError(null);
    try {
      const detail = await loadConversationPage(userId, conversationId, cursor);
      setFeedback((current) => [...current, ...toFeedbackGroups(detail.turns)]);
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

  useEffect(() => {
    if (isLoading) return;
    const root = listRef.current;
    const sentinel = sentinelRef.current;
    if (!root || !sentinel || !nextCursor || loadMoreError) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMore();
    }, { root, rootMargin: "120px" });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [isLoading, loadMore, loadMoreError, nextCursor]);

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
      {!error && feedback.length === 0 ? (
        <p className="absolute left-[5px] top-[399px] flex h-6 w-[362px] items-center justify-center text-body text-text-tertiary">
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
          <p className="rounded-2xl bg-amber-50 px-4 py-3 text-body-2 text-text-secondary" role="status">
            일부 피드백이 아직 준비되지 않았어요. 잠시 후 다시 확인해 주세요.
          </p>
        ) : null}
        {feedback.map((group) => (
          <FeedbackCard
            items={group.items}
            key={group.turnId}
            onOpen={() => {
              const conversationId = conversationIdRef.current;
              if (conversationId) group.items.forEach((item) => recordFeedbackOpen(conversationId, item));
            }}
            utterance={group.utterance}
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
