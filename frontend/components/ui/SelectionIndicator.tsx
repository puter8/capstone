import { cn } from "@/lib/utils";

type SelectionIndicatorProps = {
  selected?: boolean;
  className?: string;
};

export function SelectionIndicator({ selected = false, className }: SelectionIndicatorProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "grid size-10 place-items-center rounded-full border-2",
        selected ? "border-white bg-white text-primary" : "border-primary bg-transparent text-primary",
        className,
      )}
    >
      {selected ? (
        <svg className="size-5" fill="none" viewBox="0 0 20 20">
          <path d="m4 10 4 4 8-9" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
        </svg>
      ) : null}
    </span>
  );
}
