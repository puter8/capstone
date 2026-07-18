type FeedbackCardProps = {
  original: string;
  corrected: string;
  explanation: string;
};

export function FeedbackCard({ original, corrected, explanation }: FeedbackCardProps) {
  return (
    <article className="h-40 rounded-[10px] border border-[#eee9e3] bg-white px-5 pt-[21px] shadow-[0_2px_2.5px_rgba(0,0,0,0.16)]">
      <p className="text-subtitle-sb text-text">“{original}”</p>
      <div className="mt-[7px] h-px bg-success/60" />
      <p className="mt-[3px] text-subtitle text-success">“{corrected}”</p>
      <div className="mt-[5px] border-l-2 border-success/80 pl-2">
        <p className="text-body-2 text-text-secondary">{explanation}</p>
      </div>
    </article>
  );
}
