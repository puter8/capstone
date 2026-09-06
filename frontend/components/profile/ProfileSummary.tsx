const TAG_COLORS = ["bg-[#39c951]", "bg-[#f6c319]", "bg-[#ff5b5b]", "bg-[#a560ff]", "bg-[#9bacff]"] as const;
const TAG_WIDTHS = [62, 72, 55, 68, 62] as const;

type ProfileSummaryProps = {
  avatarUrl?: string | null;
  name?: string;
  onEditName?: () => void;
  traits?: string[];
};

export function ProfileSummary({ avatarUrl, name = "Pally user", onEditName, traits = [] }: ProfileSummaryProps) {
  return (
    <section className="relative h-[228px] w-full" aria-label="프로필">
      <div className="absolute left-1/2 top-0 size-[120px] -translate-x-1/2 overflow-hidden rounded-full border-[3px] border-primary-soft bg-[#dedede]">
        <img
          alt={`${name} 프로필 사진`}
          className="size-full object-cover"
          src={avatarUrl ?? "/pally/pally-character.svg"}
        />
      </div>
      <h2 className="absolute left-0 right-0 top-[143px] text-center text-title-2 text-text">{name}</h2>
      <button aria-label="이름 수정" className="absolute left-[242px] top-[145px] grid size-6 place-items-center text-primary" onClick={onEditName} type="button">
        <img alt="" className="size-6" src="/icons/edit-profile.svg" />
      </button>
      <div className="absolute left-1/2 top-[178px] h-0.5 w-[169px] -translate-x-1/2 bg-primary-soft" />
      <ul className="absolute left-[13px] top-[200px] flex gap-[5px]">
        {traits.map((trait, index) => (
          <li
            className={`grid h-7 place-items-center rounded-[20px] px-2 text-caption-1 text-white ${TAG_COLORS[index % TAG_COLORS.length]}`}
            key={trait}
            style={{ minWidth: TAG_WIDTHS[index % TAG_WIDTHS.length] }}
          >
            {trait}
          </li>
        ))}
      </ul>
    </section>
  );
}
