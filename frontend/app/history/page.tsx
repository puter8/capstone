"use client";

import { useEffect, useState } from "react";

import { FeedbackCard } from "@/components/feedback/FeedbackCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { PageHeader } from "@/components/ui/PageHeader";
import { pallyApi } from "@/lib/api";
import type { FeedbackItem } from "@/lib/api";

export default function HistoryPage() {
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

        const detail = await pallyApi.getConversation(conversationId, { limit: 50 });
        if (active) setFeedback(detail.turns.flatMap((turn) => turn.feedback));
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "피드백을 불러오지 못했어요.");
      } finally {
        if (active) setIsLoading(false);
      }
    };

    void loadFeedback();
    return () => {
      active = false;
    };
  }, []);

  return (
    <MobileShell>
      <PageHeader
        backHref="/history/note"
        className="absolute left-0 top-[60px]"
        description="대화에서 받은 피드백을 확인해보세요."
        title="Feedback"
        variant="back"
      />
      <section aria-label="대화 피드백" className="absolute left-5 right-5 top-[188px] flex max-h-[560px] flex-col gap-3 overflow-y-auto pb-4">
        {isLoading ? <p className="text-center text-body text-text-tertiary">피드백을 불러오는 중...</p> : null}
        {error ? <p className="text-center text-body text-red-600" role="alert">{error}</p> : null}
        {!isLoading && !error && feedback.length === 0 ? <p className="text-center text-body text-text-tertiary">아직 피드백이 없어요!</p> : null}
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
