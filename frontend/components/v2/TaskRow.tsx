import { cn } from "@/lib/utils";

import { IconCheck } from "./icons";

type TaskRowProps = {
  title: string;
  description: string;
  done: boolean;
  className?: string;
};

/** daily_tasks[] item. Done shows a butter check and a "완료" label, not color alone. */
export function TaskRow({ title, description, done, className }: TaskRowProps) {
  return (
    <li className={cn("flex items-center gap-p-3 rounded-p-card bg-p-surface p-p-4", className)}>
      {done ? (
        <span aria-hidden="true" className="grid size-[28px] shrink-0 place-items-center rounded-p-full bg-p-secondary text-p-on-secondary">
          <IconCheck size={18} />
        </span>
      ) : (
        <span aria-hidden="true" className="size-[28px] shrink-0 rounded-p-full border-2 border-p-border-control" />
      )}
      <span className="flex min-w-0 flex-1 flex-col gap-[2px]">
        <span className="text-p-button text-p-text">{title}</span>
        <span className="text-p-small text-p-text-secondary">{description}</span>
      </span>
      <span className={cn("shrink-0 text-p-eyebrow text-p-secondary", !done && "sr-only")}>{done ? "완료" : "미완료"}</span>
    </li>
  );
}
