import Link from "next/link";

import { PallyStarIcon } from "@/components/icons/PallyStarIcon";

type ConversationNoteCardProps = {
  feedbackCount: number;
  feedbackHref: string;
  startedAt: string;
  title: string;
};

export function ConversationNoteCard({ feedbackCount, feedbackHref, startedAt, title }: ConversationNoteCardProps) {
  const date = new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    day: "numeric",
  }).format(new Date(startedAt));

  return (
    <article className="relative h-[134px] w-full rounded-[10px] bg-primary-soft shadow-sm">
      <PallyStarIcon className="absolute left-3 top-2 size-5 text-white" />
      <h2 className="absolute left-[13px] top-[37px] text-button-2-sb text-white">{title}</h2>
      <p className="absolute left-[13px] top-[62px] text-caption-1 text-white/80">{date} · 피드백 {feedbackCount}개</p>
      <div className="absolute bottom-[14px] right-[10px] flex gap-4">
        <Link className="grid h-9 place-items-center rounded-full border border-white px-3 text-button-2 text-white" href="/home">대화하기</Link>
        <Link className="grid h-9 place-items-center rounded-full bg-primary px-3 text-button-2 text-white" href={feedbackHref}>피드백 보기</Link>
      </div>
    </article>
  );
}
