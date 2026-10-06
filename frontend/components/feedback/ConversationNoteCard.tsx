"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { pallyApi, PallyApiError } from "@/lib/api";
import { invalidateCurrentUserConversationData } from "@/lib/api/route-data";

type ConversationNoteCardProps = {
  conversationId: string;
  feedbackHref: string;
  title: string;
  titlePending?: boolean;
};

export function ConversationNoteCard({ conversationId, feedbackHref, title, titlePending = false }: ConversationNoteCardProps) {
  const router = useRouter();
  const [isReopening, setIsReopening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reopen = async () => {
    setIsReopening(true);
    setError(null);
    try {
      await pallyApi.reopenConversation(conversationId);
    } catch (caught) {
      if (!(caught instanceof PallyApiError && caught.code === "conversation_already_active")) {
        setError(caught instanceof Error ? caught.message : "대화를 재개하지 못했어요.");
        setIsReopening(false);
        return;
      }
    }
    await invalidateCurrentUserConversationData(conversationId).catch((caught: unknown) => {
      console.error("Conversation cache invalidation failed", caught);
    });
    window.localStorage.setItem("pally:conversationId", conversationId);
    router.push(`/home?conversation_id=${encodeURIComponent(conversationId)}`);
  };

  return (
    <article className="relative flex min-h-[134px] w-full shrink-0 flex-col rounded-[10px] bg-primary-soft pb-[14px] pt-10">
      <span className="absolute left-2 top-0 grid size-[30px] place-items-center" aria-hidden="true">
        <img alt="" className="size-[21.17px] rotate-[35.03deg]" src="/icons/history-star.svg" />
      </span>
      {titlePending ? (
        <div aria-busy="true" className="mx-[23px] flex h-[30px] items-center" role="status">
          <span className="sr-only">대화 제목을 만들고 있어요</span>
          <span aria-hidden="true" className="h-[18px] w-[150px] animate-pulse rounded-full bg-surface/50" />
        </div>
      ) : (
        <h2 className="mx-[23px] flex min-h-[30px] items-center text-body-sb text-surface [overflow-wrap:anywhere]">{title}</h2>
      )}
      <img
        alt=""
        aria-hidden="true"
        className="pointer-events-none mx-[18px] mt-[2.5px] h-[1.5px] w-[calc(100%-36px)] max-w-none"
        src="/icons/history-title-line.svg"
      />
      {error ? <p className="absolute bottom-1 left-[13px] text-[11px] text-red-100" role="alert">{error}</p> : null}
      <div className="mt-[10px] flex justify-end gap-4 pr-[10px]">
        <button aria-busy={isReopening} className="grid h-9 w-[83px] place-items-center rounded-full border border-surface text-button-2 text-surface disabled:opacity-60" disabled={isReopening} onClick={() => { void reopen(); }} type="button">
          대화하기
        </button>
        <Link className="grid h-9 w-[102px] place-items-center rounded-full border border-primary bg-primary text-button-2 text-white" href={feedbackHref}>피드백 보기</Link>
      </div>
    </article>
  );
}
