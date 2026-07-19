import { PallyStarIcon } from "@/components/icons/PallyStarIcon";

type ConversationNoteCardProps = {
  title: string;
};

export function ConversationNoteCard({ title }: ConversationNoteCardProps) {
  return (
    <article className="relative h-[134px] w-full rounded-[10px] bg-primary-soft shadow-sm">
      <PallyStarIcon className="absolute left-3 top-2 size-5 text-white" />
      <h2 className="absolute left-[13px] top-[37px] text-button-2-sb text-white">{title}</h2>
      <div className="absolute bottom-[14px] right-[10px] flex gap-4">
        <button className="h-9 rounded-full border border-white px-3 text-button-2 text-white" type="button">대화하기</button>
        <button className="h-9 rounded-full bg-primary px-3 text-button-2 text-white" type="button">피드백 보기</button>
      </div>
    </article>
  );
}
