import { PallyStarIcon } from "@/components/icons/PallyStarIcon";
import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { cn } from "@/lib/utils";

type LevelOptionProps = {
  code: string;
  description: string;
  name: string;
  onSelect: () => void;
  selected?: boolean;
};

export function LevelOption({ code, description, name, onSelect, selected = false }: LevelOptionProps) {
  return (
    <button
      aria-pressed={selected}
      className={cn(
        "relative h-[90px] w-full overflow-hidden rounded-[10px] border-[3px] border-primary text-left transition-colors",
        selected ? "bg-primary text-white" : "bg-transparent text-primary",
      )}
      onClick={onSelect}
      type="button"
    >
      <PallyStarIcon className="absolute left-[7px] top-[17px] size-5" />
      <p className="absolute left-[46px] right-[62px] top-[17px] truncate text-subtitle-sb">
        {code} - <span className="font-normal">{name}</span>
      </p>
      <p
        className={`absolute left-[46px] right-[58px] top-[49px] line-clamp-2 text-caption-2 ${
          selected ? "text-white" : "text-text-secondary"
        }`}
      >
        {description}
      </p>
      <SelectionIndicator className="absolute right-[18px] top-[20px]" selected={selected} />
    </button>
  );
}
