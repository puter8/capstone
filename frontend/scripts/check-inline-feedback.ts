import { ok } from "node:assert/strict";
import * as React from "react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import type { Message } from "../lib/types/message";

// The script runner compiles JSX with the classic transform, which looks up a global React.
(globalThis as { React?: typeof React }).React = React;

// Feedback panels stay out of chat bubbles, even when saved feedback is available.
// The conversation itself remains visible in both short and expanded views.
async function main(): Promise<void> {
  const { ChatBubble } = await import("../components/chat/ChatBubble");

  const conversation = (feedback: NonNullable<Message["feedback"]>): Message[] => [
    { id: "u1", sessionId: "s1", role: "user", transcript: "um what does wolf down mean", createdAt: "2026-10-07T00:00:00Z" },
    { id: "p1", sessionId: "s1", role: "pally", transcript: "It means to eat something very quickly!", createdAt: "2026-10-07T00:00:01Z", feedback },
  ];
  const render = (messages: Message[], expanded: boolean): string => renderToStaticMarkup(
    createElement(ChatBubble, { messages, expanded, onToggleExpand: () => undefined }),
  );

  for (const expanded of [false, true]) {
    const view = expanded ? "expanded" : "short";
    const pending = render(conversation({ items: [], pending: true }), expanded);
    ok(pending.includes("wolf down"), `${view}: the conversation is rendered`);
    ok(pending.includes("It means to eat something very quickly!"), `${view}: Pally's reply is rendered`);
    ok(!pending.includes("대화를 종료하면"), `${view}: no pending notice`);
    ok(!pending.includes("이번 발화 피드백"), `${view}: no feedback panel while pending`);

    const corrected = render(conversation({
      items: [{ original: "I go", corrected: "I went", explanation_ko: "과거 시제를 써요." }],
      pending: false,
    }), expanded);
    ok(corrected.includes("wolf down"), `${view}: saved feedback preserves the user message`);
    ok(corrected.includes("It means to eat something very quickly!"), `${view}: saved feedback preserves Pally's reply`);
    ok(!corrected.includes("I went"), `${view}: no saved correction card`);
    ok(!corrected.includes("피드백 보기"), `${view}: no feedback button`);
    ok(!corrected.includes("이번 발화 피드백"), `${view}: no saved feedback panel`);
  }
  console.log("Inline feedback checks passed.");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
