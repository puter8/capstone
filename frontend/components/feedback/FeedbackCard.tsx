type FeedbackCardProps = {
  original: string;
  corrected: string;
  explanation: string;
};

export function FeedbackCard({ original, corrected, explanation }: FeedbackCardProps) {
  return (
    <article className="relative h-40 shrink-0">
      <img
        alt=""
        className="pointer-events-none absolute left-0 top-0 h-[163px] w-[calc(100%+1px)]"
        src="/icons/feedback-card-background.svg"
      />
      <p className="absolute left-[21px] right-5 top-[23px] truncate text-subtitle-sb text-text">“{original}”</p>
      <div className="absolute left-[21px] right-6 top-[54px] h-px bg-accent" />
      <p className="absolute left-[21px] right-5 top-[62px] truncate text-subtitle text-accent">“{corrected}”</p>
      <div className="absolute left-[21px] top-[93px] h-[42px] w-0.5 bg-accent" />
      <p className="absolute left-[30.5px] right-[14px] top-[89px] line-clamp-2 text-body-2 text-text-secondary">{explanation}</p>
    </article>
  );
}
