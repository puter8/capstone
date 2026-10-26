"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { BottomNav } from "@/components/v2/BottomNav";
import { Button } from "@/components/v2/Button";
import { CorrectionCard } from "@/components/v2/CorrectionCard";
import { IconSpinner } from "@/components/v2/icons";
import { Stage } from "@/components/v2/Stage";
import { TopBar } from "@/components/v2/TopBar";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { Conversation, ConversationTurn, FeedbackItem } from "@/lib/api";
import { recordFeedbackItemOpened } from "@/lib/analytics/activity-events";
import { getCurrentUserId, invalidateConversationData, loadConversationPage, loadHistoryPage } from "@/lib/api/route-data";
import { formatClockTime, formatLongDate } from "@/lib/v2/format";
import { routes } from "@/lib/v2/routes";

type FeedbackGroup = { turnId: string; utterance: string | null; items: FeedbackItem[] };

// One card per utterance, so the full sentence shows every correction made to it.
function toFeedbackGroups(turns: readonly ConversationTurn[]): FeedbackGroup[] {
  return turns
    .filter((turn) => turn.feedback.length > 0)
    .map((turn) => ({ turnId: turn.id, utterance: turn.user_transcript, items: turn.feedback }));
}

const WORDMARK_STYLE = { fontVariationSettings: '"SOFT" 0, "WONK" 1' } as const;

export default function FeedbackV2Page() {
  const router = useRouter();
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [feedback, setFeedback] = useState<FeedbackGroup[]>([]);
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
          setConversation(detail.conversation);
          setFeedback(toFeedbackGroups(detail.turns));
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
          router.replace(routes.login);
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
      setFeedback((current) => [...current, ...toFeedbackGroups(detail.turns)]);
      setFeedbackPending((current) => current || detail.turns.some((turn) => turn.feedback_pending));
      setNextCursor(detail.next_cursor);
    } catch (caught) {
      if (caught instanceof PallyApiError && caught.code === "unauthorized") {
        router.replace(routes.login);
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
        setConversation(pages[0].conversation);
        setFeedback(toFeedbackGroups(turns));
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
    const sentinel = sentinelRef.current;
    if (!sentinel || !nextCursor || loadMoreError) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMore();
    }, { rootMargin: "160px" });
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

  const totalCorrections = feedback.reduce((sum, group) => sum + group.items.length, 0);
  const title = conversation?.title ?? "Pally와 나눈 대화";

  return (
    <AppFrame withBottomNav>
      <TopBar backHref={routes.history} title="대화 피드백" variant="back" />
      {isLoading ? (
        <div aria-busy="true" className="flex flex-col items-center gap-p-4 px-p-5 pt-p-12 text-center" role="status">
          <IconSpinner className="animate-spin text-p-text-secondary motion-reduce:animate-none" size={24} />
          <p className="text-p-label text-p-text-secondary">피드백을 불러오고 있어요</p>
        </div>
      ) : null}
      {!isLoading && conversation ? (
        <header className="flex flex-col gap-[6px] px-p-5 pb-p-5 pt-p-2">
          <p className="text-p-eyebrow text-p-text-muted">
            {formatLongDate(conversation.started_at)} · {formatClockTime(conversation.started_at)}
          </p>
          <h1 className="font-p-brand text-p-title-en text-p-text [overflow-wrap:anywhere]" lang="en" style={WORDMARK_STYLE}>
            {title}
          </h1>
          <div className="flex flex-wrap gap-[6px] pt-[6px]">
            {totalCorrections > 0 ? (
              <span className="rounded-p-full bg-p-primary-container px-[10px] py-p-1 text-p-eyebrow text-p-primary">고친 표현 {totalCorrections}개</span>
            ) : null}
            <span className="rounded-p-full bg-p-raised px-[10px] py-p-1 text-p-eyebrow text-p-text-secondary">{conversation.turn_count}번 주고받음</span>
          </div>
        </header>
      ) : null}
      {error ? (
        <div className="flex flex-col items-center gap-p-4 px-p-5 pt-p-8 text-center" role="alert">
          <Stage glow={false} size="compact" />
          <div className="flex flex-col gap-p-2">
            <h2 className="text-p-section text-p-text">피드백을 불러오지 못했어요</h2>
            <p className="text-p-body text-p-text-secondary">{error}</p>
          </div>
          <Button onClick={() => window.location.reload()} variant="secondary">
            다시 시도
          </Button>
        </div>
      ) : null}
      {!isLoading && !error && !conversation ? (
        <div className="flex flex-col items-center gap-p-4 px-p-5 pt-p-8 text-center">
          <Stage glow={false} size="compact" />
          <div className="flex flex-col gap-p-2">
            <h1 className="text-p-section text-p-text">아직 나눈 대화가 없어요</h1>
            <p className="text-p-body text-p-text-secondary">첫 대화를 마치면 고친 표현을 여기에서 볼 수 있어요.</p>
          </div>
          <Button onClick={() => router.push(routes.home)}>대화하러 가기</Button>
        </div>
      ) : null}
      {!isLoading && !error && conversation ? (
        <section aria-label="대화 피드백" className="flex flex-col gap-p-3 px-p-5 pb-p-6">
          {feedbackPending ? (
            <div className="flex flex-col gap-p-2 rounded-p-card bg-p-info-container px-p-4 py-p-3 text-p-small text-p-text" role="status">
              <p>
                {isActiveConversation
                  ? "대화를 종료하면 고친 표현을 정리해요."
                  : pollingStopped
                    ? "고친 표현을 정리하는 데 시간이 걸리고 있어요. 잠시 후 다시 확인해 주세요."
                    : "고친 표현을 정리하고 있어요. 준비되면 자동으로 표시돼요."}
              </p>
              {refreshError ? <p className="text-p-error" role="alert">{refreshError}</p> : null}
              {pollingStopped && !isActiveConversation ? (
                <Button className="self-start" onClick={() => setRefreshVersion((version) => version + 1)} size="compact" variant="text">
                  다시 확인
                </Button>
              ) : null}
            </div>
          ) : null}
          {!feedbackPending && feedback.length === 0 ? (
            <div className="flex flex-col items-center gap-p-4 pt-p-6 text-center">
              <Stage glow={false} size="compact" />
              <div className="flex flex-col gap-p-2">
                <h2 className="text-p-section text-p-text">이번 대화에는 고친 표현이 없어요</h2>
                <p className="text-p-body text-p-text-secondary">자연스럽게 잘 말했어요. 다음 대화도 이어서 해 봐요.</p>
              </div>
              <Button onClick={() => router.push(routes.history)} variant="secondary">
                피드백 목록으로
              </Button>
            </div>
          ) : null}
          {feedback.map((group, index) => (
            <CorrectionCard
              index={index + 1}
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
          {isLoadingMore ? (
            <p className="py-p-2 text-center text-p-small text-p-text-muted" role="status">
              피드백을 더 불러오고 있어요
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
        </section>
      ) : null}
      <BottomNav />
    </AppFrame>
  );
}
