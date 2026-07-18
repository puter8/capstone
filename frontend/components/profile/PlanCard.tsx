import { cn } from "@/lib/utils";

type PlanCardProps = {
  caption: string;
  className?: string;
  name: string;
  onSelect: () => void;
  plan: "monthly" | "yearly";
  price: string;
  selected: boolean;
};

export function PlanCard({ caption, className, name, onSelect, plan, price, selected }: PlanCardProps) {
  const yearly = plan === "yearly";

  return (
    <button
      aria-checked={selected}
      className={cn(
        "relative flex h-[200px] min-w-0 flex-col items-start gap-3 rounded-[20px] border-0 pb-7 pt-[35px] text-left transition-[box-shadow,transform] duration-150 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/40 active:scale-[0.99]",
        yearly
          ? "bg-gradient-to-b from-primary-soft to-primary px-[13px]"
          : "bg-gradient-to-b from-[#ffe3b8] to-primary-soft pl-3 pr-[15px]",
        selected && "z-10 shadow-[0_0_0_3px_#00c3d0]",
        className,
      )}
      onClick={onSelect}
      role="radio"
      type="button"
    >
      {selected ? (
        <span aria-hidden="true" className="absolute right-3 top-3 grid size-6 place-items-center rounded-full bg-accent text-[14px] font-bold leading-none text-white shadow-sm">
          ✓
        </span>
      ) : null}
      <p className={`whitespace-nowrap text-[clamp(30px,8.95vw,36px)] font-black leading-[44px] ${yearly ? "text-white" : "text-primary"}`}>
        {price}
      </p>
      <h2 className="whitespace-nowrap text-title-2 text-white">{name}</h2>
      <div className="h-px w-full bg-white/80" />
      <p className="whitespace-nowrap text-caption-2 text-white">{caption}</p>
    </button>
  );
}
