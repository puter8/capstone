"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { resumeConversation } from "@/lib/api/resume-conversation";

type ConversationNoteCardProps = {
  conversationId: string;
  feedbackHref: string;
  title: string;
  titlePending?: boolean;
};

export function ConversationNoteCard({ conversationId, feedbackHref, title, titlePending = false }: ConversationNoteCardProps) {
  const router = useRouter();
  // Shares the v2 card's resume: it writes nothing, so opening a past conversation and
  // leaving it no longer re-saves it. The home screen reopens it on the first turn.
  const reopen = () => {
    router.push(resumeConversation(conversationId, "/home"));
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
      <div className="mt-[10px] flex justify-end gap-4 pr-[10px]">
        <button className="grid h-9 w-[83px] place-items-center rounded-full border border-surface text-button-2 text-surface" onClick={reopen} type="button">
          대화하기
        </button>
        <Link className="grid h-9 w-[102px] place-items-center rounded-full border border-primary bg-primary text-button-2 text-white" href={feedbackHref}>피드백 보기</Link>
      </div>
    </article>
  );
}
