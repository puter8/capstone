import assert from "node:assert/strict";

import type { ConversationTurn } from "../lib/api/contracts";
import { conversationTurnsToMessages } from "../lib/api/conversation-messages";

const turns: ConversationTurn[] = [
  {
    id: "00000000-0000-0000-0000-000000000002",
    sequence: 2,
    status: "completed",
    user_transcript: "just working on my project",
    pally_text: null,
    feedback: [],
    feedback_pending: true,
    created_at: "2026-09-06T10:00:00+00:00",
  },
  {
    id: "00000000-0000-0000-0000-000000000001",
    sequence: 1,
    status: "completed",
    user_transcript: null,
    pally_text: "That's great you're focused on your project!",
    feedback: [],
    feedback_pending: false,
    created_at: "2026-09-06T10:00:00+00:00",
  },
  {
    id: "00000000-0000-0000-0000-000000000003",
    sequence: 3,
    status: "completed",
    user_transcript: "yeah but it's not a fun thing to do you know",
    pally_text: "Oh, I hear you; it's tough when your project feels more like a chore.",
    feedback: [{ id: "feedback-1", original: "a fun thing", corrected: "fun", explanation_ko: "더 자연스러운 표현이에요." }],
    feedback_pending: false,
    created_at: "2026-09-06T10:01:00+00:00",
  },
];

const messages = conversationTurnsToMessages("00000000-0000-0000-0000-000000000000", turns);

assert.deepEqual(
  messages.map(({ role, transcript }) => [role, transcript]),
  [
    ["user", "just working on my project"],
    ["pally", "That's great you're focused on your project!"],
    ["user", "yeah but it's not a fun thing to do you know"],
    ["pally", "Oh, I hear you; it's tough when your project feels more like a chore."],
  ],
);

console.log("Conversation ordering checks passed.");

const restoredFeedback = messages.find((message) => message.id === `${turns[2].id}-pally`);
assert.deepEqual(restoredFeedback?.feedback, { items: turns[2].feedback, pending: false }, "Restored feedback stays with its original reply");
const pendingFeedback = conversationTurnsToMessages("conversation", [{ ...turns[0], pally_text: "Keep going!" }]);
assert.deepEqual(pendingFeedback.find((message) => message.role === "pally")?.feedback, { items: [], pending: true }, "Deferred feedback survives conversation restoration");
assert(messages.filter((message) => message.role === "user").every((message) => message.feedback === undefined), "Feedback is shown once, under the reply");
console.log("Inline feedback restoration checks passed.");
