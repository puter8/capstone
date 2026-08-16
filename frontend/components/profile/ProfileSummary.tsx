const TAG_COLORS = ["bg-[#39c951]", "bg-[#f6c319]", "bg-[#ff5b5b]", "bg-[#a560ff]", "bg-[#9bacff]"] as const;

type ProfileSummaryProps = {
  name?: string;
  onEditName?: () => void;
  traits?: string[];
};

export function ProfileSummary({ name = "Pally user", onEditName, traits = [] }: ProfileSummaryProps) {
  return (
    <section className="relative h-[228px] w-full" aria-label="프로필">
      <div className="absolute left-1/2 top-0 h-[118px] w-[123px] -translate-x-1/2 rounded-xl border-[3px] border-primary-soft bg-[#dedede]" />
      <div className="absolute left-0 right-0 top-[140px] flex items-center justify-center gap-2">
        <h2 className="text-title-2 text-text">{name}</h2>
        <button aria-label="이름 수정" className="grid size-6 place-items-center text-primary" onClick={onEditName} type="button">
          <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 16 16">
            <path d="m2.7 12.7.8-3.1L11.4 2l2.5 2.5-7.7 7.7-3.5.5Z" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.2" />
          </svg>
        </button>
      </div>
      <div className="absolute left-1/2 top-[179px] h-px w-[169px] -translate-x-1/2 bg-[#d9d9d9]" />
      <ul className="absolute inset-x-3 top-[200px] flex justify-center gap-1">
        {traits.map((trait, index) => (
          <li className={`grid h-7 place-items-center rounded-[20px] px-3 text-caption-1 text-white ${TAG_COLORS[index % TAG_COLORS.length]}`} key={trait}>
            {trait}
          </li>
        ))}
      </ul>
    </section>
  );
}
