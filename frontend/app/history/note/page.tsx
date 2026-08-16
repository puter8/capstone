"use client";

import { useEffect, useState } from "react";

import { ConversationNoteCard } from "@/components/feedback/ConversationNoteCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { pallyApi } from "@/lib/api";
import type { ConversationListItem } from "@/lib/api";

export default function FeedbackNotePage() {
  const [items, setItems] = useState<ConversationListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    pallyApi.listConversations({ status: "completed" })
      .then((response) => {
        if (active) setItems(response.items);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "대화 기록을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <MobileShell>
      <h1 className="absolute left-5 top-[62px] text-display text-primary">History</h1>
      <div className="absolute left-5 right-5 top-[180px] flex max-h-[560px] flex-col gap-3 overflow-y-auto pb-4">
        {isLoading ? <p className="text-center text-body text-text-tertiary">대화 기록을 불러오는 중...</p> : null}
        {error ? <p className="text-center text-body text-red-600" role="alert">{error}</p> : null}
        {!isLoading && !error && items.length === 0 ? <p className="text-center text-body text-text-tertiary">아직 대화 기록이 없어요!</p> : null}
        {items.map((item) => (
          <ConversationNoteCard
            feedbackCount={item.feedback_count}
            feedbackHref={`/history?conversation_id=${encodeURIComponent(item.id)}`}
            key={item.id}
            startedAt={item.started_at}
            title={item.title ?? item.preview ?? "Pally와 나눈 대화"}
          />
        ))}
      </div>
      <BottomNav />
    </MobileShell>
  );
}
