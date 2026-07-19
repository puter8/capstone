import { PallyStarIcon } from "@/components/icons/PallyStarIcon";
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
        "relative h-[90px] w-full rounded-[10px] border-[3px] border-primary-soft",
        completed ? "bg-primary text-white" : "bg-white text-primary",
      )}
    >
      <PallyStarIcon className="absolute left-[7px] top-[17px] size-5" />
      <h3 className="absolute left-[46px] right-[64px] top-[17px] truncate text-subtitle-sb">{title}</h3>
      <p className={`absolute left-[46px] right-[64px] top-[55px] truncate text-caption-2 ${completed ? "text-white" : "text-text-secondary"}`}>
        {description}
      </p>
      <SelectionIndicator className="absolute right-[18px] top-[20px]" selected={completed} />
    </article>
  );
}
