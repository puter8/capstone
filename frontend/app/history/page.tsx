"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FeedbackCard } from "@/components/feedback/FeedbackCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/PageLoader";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { ConversationTurn, FeedbackItem } from "@/lib/api";

export default function HistoryPage() {
  const router = useRouter();
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadFeedback = async () => {
      try {
        const requestedId = new URLSearchParams(window.location.search).get("conversation_id");
        const conversationId = requestedId ?? (await pallyApi.listConversations({ status: "completed", limit: 1 })).items[0]?.id;
        if (!conversationId) return;

        const turns: ConversationTurn[] = [];
        let cursor: string | undefined;
        do {
          const detail = await pallyApi.getConversation(conversationId, { cursor, limit: 50 });
          turns.push(...detail.turns);
          cursor = detail.next_cursor ?? undefined;
        } while (cursor);

        if (active) {
          const nextFeedback = turns.flatMap((turn) => turn.feedback);
          setFeedback(nextFeedback);
          void pallyApi.recordActivityEvent({
            event_id: crypto.randomUUID(),
            event_type: "conversation_detail_opened",
            occurred_at: new Date().toISOString(),
            conversation_id: conversationId,
          }).catch((eventError: unknown) => console.error("Activity event failed", eventError));
          if (nextFeedback.length > 0) {
            void pallyApi.recordActivityEvent({
              event_id: crypto.randomUUID(),
              event_type: "feedback_item_opened",
              occurred_at: new Date().toISOString(),
              conversation_id: conversationId,
              feedback_item_id: nextFeedback[0].id,
            }).catch((eventError: unknown) => console.error("Activity event failed", eventError));
          }
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

  return (
    <MobileShell>
      {isLoading ? <PageLoader message="피드백을 불러오고 있어요" /> : null}
      <PageHeader
        backHref="/history/note"
        className="absolute left-0 top-[60px]"
        description="대화에서 받은 피드백을 확인해보세요."
        title="Feedback"
        variant="back"
      />
      {!isLoading && !error && feedback.length === 0 ? (
        <p className="absolute left-[5px] top-[399px] flex h-6 w-[362px] items-center justify-center text-body text-text-tertiary">
          아직 피드백이 없어요!
        </p>
      ) : null}
      <section aria-label="대화 피드백" className="absolute left-[21px] right-[19px] top-[188px] flex max-h-[560px] flex-col gap-3 overflow-y-auto pb-4">
        {error ? <p className="text-center text-body text-red-600" role="alert">{error}</p> : null}
        {feedback.map((item, index) => (
          <FeedbackCard
            corrected={item.corrected}
            explanation={item.explanation_ko}
            key={`${item.original}-${index}`}
            original={item.original}
          />
        ))}
      </section>
      <BottomNav />
    </MobileShell>
  );
}
