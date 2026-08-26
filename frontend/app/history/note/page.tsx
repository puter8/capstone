"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ConversationNoteCard } from "@/components/feedback/ConversationNoteCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { PageLoader } from "@/components/ui/PageLoader";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { ConversationListItem } from "@/lib/api";

export default function FeedbackNotePage() {
  const router = useRouter();
  const [items, setItems] = useState<ConversationListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadAll = async () => {
      const loaded: ConversationListItem[] = [];
      let cursor: string | undefined;
      do {
        const response = await pallyApi.listConversations({ status: "completed", cursor, limit: 50 });
        loaded.push(...response.items);
        cursor = response.next_cursor ?? undefined;
      } while (cursor);
      if (active) setItems(loaded);
    };

    void loadAll()
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
  }, [router]);

  return (
    <MobileShell>
      <h1 className="absolute left-5 top-[79px] text-display text-primary">History</h1>
      {isLoading ? <PageLoader message="대화 기록을 불러오고 있어요" /> : null}
      {!isLoading && !error && items.length === 0 ? (
        <p className="absolute left-5 right-5 top-1/2 -translate-y-1/2 text-center text-body text-text-tertiary">
          아직 대화 기록이 없어요!
        </p>
      ) : null}
      <div className="absolute left-5 right-5 top-[180px] flex max-h-[560px] flex-col gap-3 overflow-y-auto pb-4">
        {error ? <p className="text-center text-body text-red-600" role="alert">{error}</p> : null}
        {items.map((item) => (
          <ConversationNoteCard
            conversationId={item.id}
            feedbackHref={`/history?conversation_id=${encodeURIComponent(item.id)}`}
            key={item.id}
            title={item.title ?? item.preview ?? "Pally와 나눈 대화"}
          />
        ))}
      </div>
      <BottomNav />
    </MobileShell>
  );
}
