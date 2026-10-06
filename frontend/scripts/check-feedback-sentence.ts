import assert from "node:assert/strict";

import type { FeedbackItem } from "../lib/api/contracts";
import { locateEdits, spliceEdits } from "../lib/feedback-sentence";

const item = (original: string, replacement?: string): FeedbackItem => ({
  original,
  corrected: "unused",
  explanation_ko: "unused",
  ...(replacement ? { replacement } : {}),
});

function correctedSentence(utterance: string, items: FeedbackItem[]): string {
  const fixes = locateEdits(utterance, items).filter((edit) => edit.item.replacement);
  return spliceEdits(utterance, fixes, (edit) => edit.item.replacement).join("");
}

// The user's own fix replaces the wrong span inside the full sentence.
assert.equal(correctedSentence("yesterday I go to the park", [item("I go", "I went")]), "yesterday I went to the park");
// Case, punctuation, and curly apostrophes do not block the match.
assert.equal(correctedSentence("I’m go to school.", [item("i'm go", "I'm going")]), "I'm going to school.");
// Every fix in one utterance lands in the same corrected sentence.
assert.equal(correctedSentence("I has two dog.", [item("I has", "I have"), item("dog", "dogs")]), "I have two dogs.");
// Unmatched or overlapping spans never corrupt the sentence.
assert.equal(correctedSentence("I go home", [item("cats", "cat"), item("I go", "I went"), item("go", "goes")]), "I went home");
// Items without a fix are still located, so the card can highlight them.
assert.deepEqual(locateEdits("she want cookies", [item("she want")]).map(({ start, end }) => [start, end]), [[0, 8]]);

console.log("Feedback sentence checks passed.");
