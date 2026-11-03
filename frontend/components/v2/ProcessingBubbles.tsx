import type { ProcessingPhase } from "@/lib/state/conversation";

import { Bubble } from "./Bubble";

export function ProcessingBubbles({ phase, showUserPlaceholder = true }: { phase: ProcessingPhase; showUserPlaceholder?: boolean }) {
  return (
    <>
      {phase === "reply" && showUserPlaceholder ? <Bubble emphasis="past" placeholder speaker="me" text="" /> : null}
      <div className="flex w-full flex-col items-start gap-[6px]">
        <span className="text-p-caption text-p-text-muted">Pally</span>
        <div
          aria-label={phase === "opener" ? "Pally가 인사를 준비하고 있어요" : "답변을 준비하고 있어요"}
          className="rounded-[20px] rounded-tl-[6px] bg-p-surface px-p-4 py-p-3"
          role="status"
        >
          <span aria-hidden="true" className="flex h-[26px] items-center gap-[6px]">
            {[0, 1, 2].map((index) => (
              <span className="size-[6px] animate-pulse rounded-p-full bg-p-text-muted motion-reduce:animate-none" key={index} style={{ animationDelay: `${index * 150}ms` }} />
            ))}
          </span>
        </div>
      </div>
    </>
  );
}
