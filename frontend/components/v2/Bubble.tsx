import { Fragment } from "react";

import type { PallySegment } from "@/lib/api/contracts";
import { cn } from "@/lib/utils";

type BubbleProps = {
  speaker: "pally" | "me";
  text: string;
  /** Server-provided reply pieces; rendered verbatim when present. */
  segments?: PallySegment[] | null;
  /** Past turns keep full opacity and only lower the text color. */
  emphasis?: "current" | "past";
  /** Dotted placeholder while the user is still speaking (no transcript yet). */
  placeholder?: boolean;
  className?: string;
};

const SEGMENT_CLASS: Partial<Record<PallySegment["kind"], string>> = {
  correction: "font-semibold text-p-primary underline decoration-solid underline-offset-4",
};

const SEGMENT_PREFIX: Partial<Record<PallySegment["kind"], string>> = {
  correction: "고친 표현: ",
};

export function Bubble({ speaker, text, segments, emphasis = "current", placeholder = false, className }: BubbleProps) {
  const isMe = speaker === "me";
  return (
    <div className={cn("flex w-full flex-col gap-[6px]", isMe ? "items-end" : "items-start", className)}>
      <span className="text-p-caption text-p-text-muted">{isMe ? "나" : "Pally"}</span>
      <div
        className={cn(
          "max-w-[85%] rounded-[20px] px-p-4 py-p-3",
          isMe ? "rounded-tr-[6px] bg-p-primary-container" : "rounded-tl-[6px] bg-p-surface",
        )}
      >
        {placeholder ? (
          <p className="flex h-[26px] items-center">
            <span aria-hidden="true" className="inline-block w-[96px] border-b-2 border-dotted border-p-border-control" />
            <span className="sr-only">듣고 있어요</span>
          </p>
        ) : (
          <p
            className={cn(
              "whitespace-pre-wrap [overflow-wrap:anywhere] [word-break:normal] text-p-body",
              emphasis === "past" ? "text-p-text-secondary" : "text-p-text",
            )}
            lang="en"
          >
            {segments
              ? segments.map((segment, index) => {
                  const prefix = SEGMENT_PREFIX[segment.kind];
                  // The hidden label is a sibling so the highlighted span holds only the reply text.
                  return (
                    <Fragment key={index}>
                      {prefix ? <span className="sr-only">{prefix}</span> : null}
                      <span className={SEGMENT_CLASS[segment.kind]} data-segment-kind={segment.kind}>
                        {segment.text}
                      </span>
                    </Fragment>
                  );
                })
              : text}
          </p>
        )}
      </div>
    </div>
  );
}
