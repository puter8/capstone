"use client";

import { cn } from "@/lib/utils";

import { IconCheck } from "./icons";

type LevelCardProps = {
  code: string;
  name: string;
  description: string;
  selected: boolean;
  /** The level saved on the profile right now. */
  current?: boolean;
  disabled?: boolean;
  onSelect: () => void;
  className?: string;
};

/** Radio card for a CEFR level. Selection shows container, 2px primary border and a check. */
export function LevelCard({ code, name, description, selected, current = false, disabled, onSelect, className }: LevelCardProps) {
  return (
    <button
      aria-checked={selected}
      className={cn(
        "flex w-full items-center gap-p-3 rounded-p-card py-p-4 pl-p-5 pr-p-4 text-left transition-colors duration-p-fast ease-p-out motion-reduce:transition-none",
        selected ? "border-2 border-p-primary bg-p-primary-container" : "border border-p-border bg-p-surface hover:bg-p-raised",
        "disabled:opacity-60",
        className,
      )}
      disabled={disabled}
      onClick={onSelect}
      role="radio"
      tabIndex={selected ? 0 : -1}
      type="button"
    >
      <span className="flex min-w-0 flex-1 flex-col gap-[6px]">
        <span className="flex items-center gap-p-2">
          <span className={cn("rounded-p-sm px-p-2 py-[2px] text-p-label", selected ? "bg-p-primary text-p-on-primary" : "bg-p-raised text-p-text-secondary")} lang="en">
            {code}
          </span>
          <span className="text-p-card tracking-[-0.02em] text-p-text">
            <span lang="en">{name}</span>
            {current ? " · 현재" : ""}
          </span>
        </span>
        <span className="text-p-small text-p-text-secondary">{description}</span>
      </span>
      {selected ? (
        <span aria-hidden="true" className="grid size-[24px] shrink-0 place-items-center rounded-p-full bg-p-primary text-p-on-primary">
          <IconCheck size={16} />
        </span>
      ) : (
        <span aria-hidden="true" className="size-[24px] shrink-0 rounded-p-full border-2 border-p-border-control" />
      )}
    </button>
  );
}

export const LEVEL_OPTIONS = [
  { code: "A2", name: "Elementary", description: "쉬운 단어로 일상을 말하고 간단한 표현을 이해해요." },
  { code: "B1", name: "Intermediate", description: "여행에서 필요한 말을 하고 취미·일·가족 이야기를 나눠요." },
  { code: "B2", name: "Upper Intermediate", description: "복잡한 주제도 이해하고 원어민과 막힘없이 대화해요." },
  { code: "C1", name: "Advanced", description: "사교·학업·업무 상황에서 영어를 자유롭게 쓰고 복잡한 대화도 따라가요." },
] as const;
