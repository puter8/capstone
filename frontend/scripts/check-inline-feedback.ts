import { ok } from "node:assert/strict";
import * as React from "react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import type { Message } from "../lib/types/message";

// The script runner compiles JSX with the classic transform, which looks up a global React.
(globalThis as { React?: typeof React }).React = React;

// Feedback is generated after a conversation ends. While it is pending the chat bubble
// must show no feedback notice: it only took space from the message area and clipped
// Pally's reply.
async function main(): Promise<void> {
  // ChatBubble reaches the API client through the analytics helper, which needs these at import time.
  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://fixture.supabase.invalid";
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "fixture-public-anon-key";
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
    ok(!pending.includes("대화를 종료하면"), `${view}: no pending notice`);
    ok(!pending.includes("이번 발화 피드백"), `${view}: no feedback panel while pending`);

    const corrected = render(conversation({
      items: [{ original: "I go", corrected: "I went", explanation_ko: "과거 시제를 써요." }],
      pending: false,
    }), expanded);
    ok(corrected.includes("I went"), `${view}: a saved correction is listed`);
  }
  console.log("Inline feedback checks passed.");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
