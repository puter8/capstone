import { cn } from "@/lib/utils";

import { IconFlame } from "./icons";

/** streak_count. A day counts when all three daily tasks are done (backend rule). */
export function StreakHero({ count, className }: { count: number; className?: string }) {
  return (
    <section aria-label={`연속 기록 ${count}일`} className={cn("flex flex-col gap-p-1 rounded-p-sheet bg-p-surface p-p-6", className)}>
      <div className="flex items-center">
        <p className="flex-1 text-p-eyebrow text-p-text-muted">연속 기록</p>
        <span aria-hidden="true" className="grid size-p-target place-items-center rounded-p-full bg-p-secondary-container text-p-secondary">
          <IconFlame size={22} />
        </span>
      </div>
      <p aria-hidden="true" className="flex items-baseline gap-[2px]">
        <span className="font-p-brand text-p-numeral tabular-nums text-p-secondary" style={{ fontVariationSettings: '"SOFT" 0, "WONK" 1' }}>
          {count}
        </span>
        <span className="text-p-card tracking-[-0.02em] text-p-text">일 연속</span>
      </p>
      <p className="text-p-small text-p-text-secondary">과제 3개를 모두 마치면 기록이 이어져요.</p>
    </section>
  );
}
