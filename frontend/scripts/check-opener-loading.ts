import { doesNotMatch, equal, match } from "node:assert/strict";
import React, { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { Dock } from "../components/v2/Dock";
import { ProcessingBubbles } from "../components/v2/ProcessingBubbles";
import { TopBar } from "../components/v2/TopBar";
import { initialState, reducer } from "../lib/state/conversation";

(globalThis as { React?: typeof React }).React = React;

const opening = reducer(initialState, { type: "opener/request" });
equal(opening.rec.kind, "processing");
if (opening.rec.kind !== "processing") throw new Error("Expected opener processing");
equal(opening.rec.phase, "opener");
const pendingOpener = renderToStaticMarkup(createElement(ProcessingBubbles, { phase: opening.rec.phase }));
doesNotMatch(pendingOpener, />나</, "Pally's first greeting must not show an invented user turn");
doesNotMatch(pendingOpener, /듣고 있어요|답변/, "The learner has not spoken yet");
match(pendingOpener, /Pally가 인사를 준비하고 있어요/);

const dockProps = {
  onPressMic: () => {}, onReplay: () => {}, onToggleTranscript: () => {},
  transcriptOpen: false, canReplay: false, maxRecordingMs: 30_000,
};
const openerDock = renderToStaticMarkup(createElement(Dock, { ...dockProps, state: "opening" }));
match(openerDock, /aria-label="Pally 인사 준비 중"[^>]*disabled=""/, "The greeting wait keeps the mic disabled");
match(openerDock, /Pally가 인사를 준비하고 있어요/);
doesNotMatch(openerDock, /답변/);
const openerBar = renderToStaticMarkup(createElement(TopBar, { variant: "conversation", status: "opening", onEnd: () => {} }));
match(openerBar, /인사 준비 중/);
doesNotMatch(openerBar, /답변 준비|내 차례/);

const received = reducer(opening, { type: "opener/received", pallyMsg: {
  id: "opener", sessionId: "conversation", role: "pally", transcript: "Hi! How are you?", createdAt: "2026-11-03T00:00:00Z",
} });
equal(received.rec.kind, "speaking");
const ready = reducer(received, { type: "rec/speakingDone" });
const reply = reducer(reducer(ready, { type: "rec/start" }), { type: "rec/stop" });
if (reply.rec.kind !== "processing") throw new Error("Expected reply processing");
equal(reply.rec.phase, "reply");
equal(reply.messages.filter((message) => message.role === "user").length, 0, "The first transcript has not returned from STT yet");
const pendingReply = renderToStaticMarkup(createElement(ProcessingBubbles, { phase: reply.rec.phase }));
match(pendingReply, />나</, "The first recorded user turn still has its placeholder while STT runs");
match(pendingReply, /답변을 준비하고 있어요/);
doesNotMatch(pendingReply, /인사를 준비/);
const replyDock = renderToStaticMarkup(createElement(Dock, { ...dockProps, state: "processing" }));
match(replyDock, /답변을 준비하고 있어요/);

const history = renderToStaticMarkup(createElement(ProcessingBubbles, { phase: "reply", showUserPlaceholder: false }));
doesNotMatch(history, />나</, "The transcript view preserves its existing message list without adding a second user placeholder");
const voiceDock = renderToStaticMarkup(createElement(Dock, { ...dockProps, state: "processing", sideControls: false, statusText: "목소리를 등록하고 있어요" }));
match(voiceDock, /목소리를 등록하고 있어요/, "Voice registration retains its custom status");
doesNotMatch(voiceDock, /인사를 준비/);
equal(reducer(opening, { type: "session/end" }).rec.kind, "idle");
equal(reducer(opening, { type: "rec/error", reason: "generic", message: "Retry" }).rec.kind, "error");

console.log("Opener loading checks passed: greeting-only speaker, distinct labels and the first user reply transition.");
