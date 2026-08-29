import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { cn } from "@/lib/utils";

type ChallengeTaskProps = {
  completed?: boolean;
  description: string;
  title: string;
};

export function ChallengeTask({ completed = false, description, title }: ChallengeTaskProps) {
  return (
    <article
      className={cn(
        "relative h-[90px] w-full overflow-hidden rounded-[10px]",
        completed ? "text-white" : "text-primary",
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "absolute inset-0 rounded-[10px] border-[3px]",
          completed ? "border-primary bg-primary" : "border-primary-soft bg-transparent",
        )}
      />
      <span aria-hidden="true" className="absolute left-[7.85px] top-[14px] grid h-[42.3px] w-[38.8px] place-items-center">
        <img
          alt=""
          className="h-[29.46px] w-[28.5px] rotate-[37.69deg] skew-x-[5.24deg]"
          src={completed ? "/icons/challenge-star-completed.svg" : "/icons/challenge-star-default.svg"}
        />
      </span>
      <h3 className="absolute left-[46px] right-[64px] top-[22px] truncate text-[18px] font-bold leading-[24px]">{title}</h3>
      <p className={cn("absolute left-[46px] right-[64px] top-[56px] truncate text-[11px] font-normal leading-[12px]", completed ? "text-white" : "text-text-secondary")}>
        {description}
      </p>
      <SelectionIndicator className={cn("absolute right-[19px]", completed ? "top-[22px]" : "top-[24px]")} selected={completed} />
    </article>
  );
}
