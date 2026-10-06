import type { FeedbackItem } from "@/lib/api";
import { locateEdits, spliceEdits } from "@/lib/feedback-sentence";

type FeedbackCardProps = {
  utterance: string | null;
  items: readonly FeedbackItem[];
  onOpen?: () => void;
};

export function FeedbackCard({ utterance, items, onOpen }: FeedbackCardProps) {
  const edits = utterance ? locateEdits(utterance, items) : [];
  // Only fixes written in the user's own words can be placed back into the sentence.
  const fixes = edits.filter((edit) => edit.item.replacement);
  const fixed = new Set(fixes.map((edit) => edit.item));
  const correctedText = utterance && fixes.length > 0
    ? spliceEdits(utterance, fixes, (edit) => edit.item.replacement).join("")
    : items.map((item) => item.corrected).join(" / ");
  const showPairs = items.length > 1;

  return (
    <button
      aria-label={`피드백 열기: ${correctedText}`}
      className="block w-full shrink-0 rounded-[10px] border-0 bg-gradient-to-br from-white to-surface px-[21px] pb-6 pt-[23px] text-left shadow-[1px_3px_0_rgba(0,0,0,0.1)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/30"
      onClick={onOpen}
      type="button"
    >
      <p className="whitespace-pre-wrap break-words text-subtitle-sb text-text">
        “{utterance
          ? spliceEdits(utterance, edits, (edit) => (
            <mark className="rounded-sm bg-red-100 px-0.5 text-red-700" key={edit.start}>{utterance.slice(edit.start, edit.end)}</mark>
          ))
          : items.map((item) => item.original).join(" / ")}”
      </p>
      <div className="my-[7px] h-px bg-accent" />
      <p className="whitespace-pre-wrap break-words text-subtitle text-accent">
        “{utterance && fixes.length > 0
          ? spliceEdits(utterance, fixes, (edit) => (
            <mark className="rounded-sm bg-accent/15 px-0.5 font-bold text-accent" key={edit.start}>{edit.item.replacement}</mark>
          ))
          : correctedText}”
      </p>
      {items.map((item, index) => (item.explanation_ko.trim() ? (
        <p className="mt-1 whitespace-pre-wrap break-words border-l-2 border-accent pl-2 text-body-2 text-text-secondary" key={index}>
          {showPairs ? <span className="font-semibold">{item.original} → {fixed.has(item) ? item.replacement : item.corrected}: </span> : null}
          {item.explanation_ko}
        </p>
      ) : null))}
    </button>
  );
}
