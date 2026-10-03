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
        "relative min-h-[90px] w-full overflow-hidden rounded-[10px] py-[22px] pl-[46px] pr-[62px]",
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
      <h3 className="relative text-body-sb">{title}</h3>
      <p className={cn("relative mt-[10px] text-[11px] font-normal leading-[12px]", completed ? "text-white" : "text-text-secondary")}>
        {description}
      </p>
      <SelectionIndicator className="absolute right-5 top-1/2 h-7 w-7 -translate-y-1/2" selected={completed} />
    </article>
  );
}
