import type { FeedbackItem } from "@/lib/api";

// Mirrors ai/generate_feedback.py for English transcripts: case and punctuation do not affect the match.
const WORD = /[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*/g;

export interface SentenceEdit {
  start: number;
  end: number;
  item: FeedbackItem;
}

function words(text: string) {
  return Array.from(text.matchAll(WORD), (match) => ({
    word: match[0].replace(/’/g, "'").toLowerCase(),
    start: match.index,
    end: match.index + match[0].length,
  }));
}

/** Locates each item's original in the utterance. Unmatched or overlapping items are left out. */
export function locateEdits(utterance: string, items: readonly FeedbackItem[]): SentenceEdit[] {
  const source = words(utterance);
  const edits: SentenceEdit[] = [];
  for (const item of items) {
    const target = words(item.original).map((token) => token.word);
    const at = source.findIndex((_, i) => target.length > 0 && target.every((word, j) => source[i + j]?.word === word));
    if (at < 0) continue;
    const start = source[at].start;
    const end = source[at + target.length - 1].end;
    if (edits.every((edit) => end <= edit.start || edit.end <= start)) edits.push({ start, end, item });
  }
  return edits.sort((a, b) => a.start - b.start);
}

/** Splits the utterance around the edits and renders each edit with `piece`. */
export function spliceEdits<T>(utterance: string, edits: readonly SentenceEdit[], piece: (edit: SentenceEdit) => T): (string | T)[] {
  const parts: (string | T)[] = [];
  let cursor = 0;
  for (const edit of edits) {
    parts.push(utterance.slice(cursor, edit.start), piece(edit));
    cursor = edit.end;
  }
  parts.push(utterance.slice(cursor));
  return parts;
}
