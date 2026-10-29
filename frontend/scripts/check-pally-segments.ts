import { deepEqual, equal, ok } from "node:assert/strict";
import * as React from "react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import type { PallySegment } from "../lib/api/contracts";
import { conversationTurnsToMessages } from "../lib/api/conversation-messages";
import { conversationDetailResponseSchema, turnResponseSchema } from "../lib/api/schemas";
import type { Message } from "../lib/types/message";

// Match the classic JSX transform used by the existing SSR checks.
(globalThis as { React?: typeof React }).React = React;

const conversationId = "00000000-0000-4000-8000-000000000001";
const turnId = "00000000-0000-4000-8000-000000000002";
const createdAt = "2026-10-15T03:00:00Z";
const segments: PallySegment[] = [
  { kind: "own_remark", text: "Oh, " },
  { kind: "correction", text: "you skipped lunch because you're on a diet?" },
  { kind: "plain", text: " " },
  { kind: "own_remark", text: "I tried that once and got super " },
  { kind: "own_remark", text: "hangry" },
  { kind: "own_remark", text: "." },
  { kind: "plain", text: " " },
  { kind: "question", text: "What do you eat instead?" },
];
const replyText = segments.map((segment) => segment.text).join("");
const turnFixture = {
  conversation_id: conversationId,
  turn_id: turnId,
  status: "completed",
  replayed: false,
  user: { transcript: "I skip lunch because I'm on a diet" },
  pally: { text: replyText, audio: "fixture-audio", segments },
  axes: { Formality: 30, Energy: 40, Intimacy: 50, Humor: 60, Curiosity: 70 },
  character: { tone_casual: 70, energy_level: 40, humor_level: 60 },
  feedback: [],
  feedback_pending: true,
  warnings: [],
  quota: { used_turns: 1, remaining_turns: 19, daily_limit: 20, exhausted: false, resets_at: "2026-10-15T15:00:00Z" },
  created_at: createdAt,
};
const historyTurn = {
  id: turnId,
  sequence: 1,
  status: "completed",
  user_transcript: turnFixture.user.transcript,
  pally_text: replyText,
  pally_segments: segments,
  feedback: [],
  feedback_pending: true,
  created_at: createdAt,
};
const detailFixture = {
  conversation: {
    id: conversationId,
    status: "active",
    title: "Lunch",
    started_at: createdAt,
    last_turn_at: createdAt,
    completed_at: null,
    turn_count: 1,
  },
  turns: [historyTurn],
  next_cursor: null,
};

function captureErrors<T>(run: () => T): { result: T; errors: unknown[][] } {
  const errors: unknown[][] = [];
  const originalError = console.error;
  console.error = (...args: unknown[]) => { errors.push(args); };
  try {
    return { result: run(), errors };
  } finally {
    console.error = originalError;
  }
}

function escapeText(text: string): string {
  return renderToStaticMarkup(createElement("span", null, text)).slice(6, -7);
}

function paragraphContents(markup: string): string[] {
  return Array.from(markup.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/g)).map((match) => match[1]);
}

function segmentSpans(markup: string): Array<{ kind: string; classes: string[]; text: string }> {
  return Array.from(markup.matchAll(/<span\b([^>]*data-segment-kind="([^"]+)"[^>]*)>([\s\S]*?)<\/span>/g))
    .map((match) => ({
      kind: match[2],
      classes: (match[1].match(/class="([^"]*)"/)?.[1] ?? "").split(/\s+/),
      text: match[3],
    }));
}

function assertReply(markup: string, expected: PallySegment[], text: string, context: string): void {
  const spans = segmentSpans(markup);
  deepEqual(spans.map((span) => span.kind), expected.map((segment) => segment.kind), `${context}: segment order and count`);
  deepEqual(spans.map((span) => span.text), expected.map((segment) => escapeText(segment.text)), `${context}: text and spaces stay unchanged`);
  equal(spans.map((span) => span.text).join(""), escapeText(text), `${context}: segments reproduce the reply`);
  const replyParagraphs = paragraphContents(markup).filter((paragraph) => paragraph.includes("data-segment-kind"));
  equal(replyParagraphs.length, 1, `${context}: one reply paragraph`);
  equal(replyParagraphs[0].replace(/<[^>]*>/g, ""), escapeText(text), `${context}: no duplicated plain text`);
  for (const span of spans) {
    const has = (token: string): boolean => span.classes.includes(token);
    equal(has("font-bold"), span.kind === "correction", `${context}: ${span.kind} bold only for corrections`);
    equal(has("text-primary"), span.kind === "correction", `${context}: ${span.kind} orange only for corrections`);
    equal(has("text-accent"), false, `${context}: ${span.kind} no expression color`);
    equal(has("underline"), false, `${context}: ${span.kind} no underline styling`);
  }
}

async function main(): Promise<void> {
  const { MessageRow } = await import("../components/chat/MessageRow");
  const { ChatBubble } = await import("../components/chat/ChatBubble");
  const renderReply = (text: string, replySegments?: PallySegment[] | null): string => renderToStaticMarkup(
    createElement(MessageRow, { speaker: "pally", transcript: text, segments: replySegments }),
  );
  const assertPlain = (markup: string, text: string, context: string): void => {
    equal(segmentSpans(markup).length, 0, `${context}: no styled segments`);
    equal(paragraphContents(markup).filter((paragraph) => paragraph === escapeText(text)).length, 1, `${context}: plain reply appears once`);
  };

  const validTurn = captureErrors(() => turnResponseSchema.parse(turnFixture));
  equal(validTurn.errors.length, 0, "A valid turn does not log errors");
  deepEqual(validTurn.result.pally.segments, segments, "POST preserves validated segments");
  const rendered = renderReply(validTurn.result.pally.text, validTurn.result.pally.segments);
  assertReply(rendered, segments, replyText, "POST rendering");

  // Rolling deployments and stored History can still contain the removed kind.
  const legacySegments = segments.map((segment, index) => index === 4 ? { ...segment, kind: "new_expr" } : segment);
  const legacyTurn = captureErrors(() => turnResponseSchema.parse({
    ...turnFixture, pally: { ...turnFixture.pally, segments: legacySegments },
  }));
  equal(legacyTurn.errors.length, 0, "An old reply is normalized without errors");
  deepEqual(legacyTurn.result.pally.segments, segments, "Old turn expressions become ordinary remarks");
  equal(legacyTurn.result.pally.text, replyText, "Old turn text stays unchanged");
  const legacyDetail = captureErrors(() => conversationDetailResponseSchema.parse({
    ...detailFixture, turns: [{ ...historyTurn, pally_segments: legacySegments }],
  }));
  equal(legacyDetail.errors.length, 0, "Old History is normalized without errors");
  deepEqual(legacyDetail.result.turns[0].pally_segments, segments, "Old History expressions become ordinary remarks");
  assertReply(renderReply(legacyTurn.result.pally.text, legacyTurn.result.pally.segments), segments, replyText, "Old reply rendering");

  const correctionCases: Array<{ name: string; transcript: string; segments: PallySegment[]; correctionCount: number }> = [
    {
      name: "Partial correction",
      transcript: "I'm diet.",
      segments: [
        { kind: "plain", text: "Oh, " },
        { kind: "correction", text: "you're on a diet" },
        { kind: "plain", text: "?" },
        { kind: "plain", text: " " },
        { kind: "own_remark", text: "I " },
        { kind: "own_remark", text: "skip lunch" },
        { kind: "own_remark", text: " sometimes too." },
        { kind: "plain", text: " " },
        { kind: "question", text: "What do you eat for dinner?" },
      ],
      correctionCount: 1,
    },
    {
      name: "Correct sentence without correction",
      transcript: "I was just chilling.",
      segments: [
        { kind: "plain", text: "Oh, you were just chilling?" },
        { kind: "plain", text: " " },
        { kind: "own_remark", text: "That sounds like " },
        { kind: "own_remark", text: "a nice break" },
        { kind: "own_remark", text: "." },
        { kind: "plain", text: " " },
        { kind: "question", text: "Did you relax much?" },
      ],
      correctionCount: 0,
    },
  ];
  for (const scenario of correctionCases) {
    const text = scenario.segments.map((segment) => segment.text).join("");
    for (const replayed of [false, true]) {
      const context = `${scenario.name}: ${replayed ? "replay" : "POST"}`;
      const parsed = captureErrors(() => turnResponseSchema.parse({
        ...turnFixture,
        replayed,
        user: { transcript: scenario.transcript },
        pally: { ...turnFixture.pally, text, segments: scenario.segments },
      }));
      equal(parsed.errors.length, 0, `${context}: valid segments do not log errors`);
      equal(parsed.result.replayed, replayed);
      equal(parsed.result.pally.text, text);
      deepEqual(parsed.result.pally.segments, scenario.segments, `${context}: valid segments do not fall back to plain text`);
      const markup = renderReply(parsed.result.pally.text, parsed.result.pally.segments);
      assertReply(markup, scenario.segments, text, context);
      equal(segmentSpans(markup).filter((span) => span.kind === "correction").length, scenario.correctionCount, `${context}: only server corrections are orange`);
    }
    const history = captureErrors(() => conversationDetailResponseSchema.parse({
      ...detailFixture,
      turns: [{ ...historyTurn, user_transcript: scenario.transcript, pally_text: text, pally_segments: scenario.segments }],
    }));
    equal(history.errors.length, 0, `${scenario.name}: History does not log errors`);
    const restoredMessages = conversationTurnsToMessages(conversationId, history.result.turns);
    const restored = restoredMessages.find((message) => message.role === "pally");
    ok(restored);
    equal(restored.transcript, text);
    deepEqual(restored.segments, scenario.segments, `${scenario.name}: History preserves valid segments`);
    assertReply(renderReply(restored.transcript, restored.segments), scenario.segments, text, `${scenario.name}: History restoration`);
    if (scenario.correctionCount === 0) {
      for (const view of [
        { expanded: false, listening: false, name: "Short bubble" },
        { expanded: true, listening: false, name: "Expanded bubble" },
        { expanded: false, listening: true, name: "Previous reply while listening" },
      ]) {
        const markup = renderToStaticMarkup(createElement(ChatBubble, {
          messages: restoredMessages,
          expanded: view.expanded,
          listening: view.listening,
          onToggleExpand: () => undefined,
        }));
        assertReply(markup, scenario.segments, text, `${scenario.name}: ${view.name}`);
      }
    }
  }

  for (const raw of [null, undefined]) {
    const pally = raw === undefined
      ? { text: replyText, audio: turnFixture.pally.audio }
      : { ...turnFixture.pally, segments: raw };
    const parsed = captureErrors(() => turnResponseSchema.parse({ ...turnFixture, pally }));
    equal(parsed.errors.length, 0, "Absent or null POST segments are expected, not errors");
    equal(parsed.result.pally.segments, null);
    assertPlain(renderReply(parsed.result.pally.text, parsed.result.pally.segments), replyText, "POST fallback");
    const { pally_segments: omittedSegments, ...oldTurn } = historyTurn;
    void omittedSegments;
    const history = captureErrors(() => conversationDetailResponseSchema.parse({
      ...detailFixture,
      turns: [raw === undefined ? oldTurn : { ...historyTurn, pally_segments: raw }],
    }));
    equal(history.errors.length, 0, "Absent or null History segments are expected, not errors");
    equal(history.result.turns[0].pally_segments, null);
    const restored = conversationTurnsToMessages(conversationId, history.result.turns).find((message) => message.role === "pally");
    ok(restored);
    assertPlain(renderReply(restored.transcript, restored.segments), replyText, "History fallback");
  }

  const privateMarker = "PRIVATE-SEGMENT-PAYLOAD";
  const malformed: Array<{ name: string; raw: unknown }> = [
    { name: "wrong container", raw: privateMarker },
    { name: "wrong kind", raw: [{ kind: privateMarker, text: replyText }] },
    { name: "wrong text type", raw: [{ kind: "question", text: 42 }] },
    { name: "missing text", raw: [{ kind: "question" }] },
    { name: "null entry", raw: [null] },
    { name: "empty array", raw: [] },
    { name: "text mismatch", raw: [{ kind: "question", text: privateMarker }] },
    { name: "missing space", raw: segments.filter((segment) => segment.kind !== "plain") },
  ];
  for (const { name, raw } of malformed) {
    const parsed = captureErrors(() => turnResponseSchema.parse({
      ...turnFixture,
      pally: { ...turnFixture.pally, segments: raw },
    }));
    equal(parsed.result.pally.segments, null, `${name}: only segments are discarded`);
    deepEqual(parsed.result, { ...turnFixture, pally: { ...turnFixture.pally, segments: null } }, `${name}: text, audio, axes and remaining turn fields survive`);
    equal(parsed.errors.length, 1, `${name}: one error per invalid field`);
    const logged = JSON.stringify(parsed.errors);
    ok(logged.includes("turn") && logged.includes("segments"), `${name}: error identifies the response and field`);
    for (const secret of [privateMarker, replyText, turnFixture.user.transcript, turnFixture.pally.audio]) {
      ok(!logged.includes(secret), `${name}: log does not include conversation data`);
    }
    assertPlain(renderReply(parsed.result.pally.text, parsed.result.pally.segments), replyText, name);
  }
  const invalidBody = captureErrors(() => turnResponseSchema.safeParse({
    ...turnFixture,
    pally: { text: 42, audio: null, segments: malformed[0].raw },
  }));
  equal(invalidBody.result.success, false, "Invalid core response fields still fail validation");
  equal(invalidBody.errors.length, 0, "Segment normalization does not run before core validation succeeds");

  const replay = captureErrors(() => turnResponseSchema.parse({ ...turnFixture, replayed: true }));
  equal(replay.errors.length, 0);
  equal(replay.result.replayed, true);
  assertReply(renderReply(replay.result.pally.text, replay.result.pally.segments), segments, replyText, "Replay rendering");

  const damagedReplay = captureErrors(() => turnResponseSchema.parse({
    ...turnFixture,
    replayed: true,
    pally: { ...turnFixture.pally, segments: malformed[0].raw },
  }));
  equal(damagedReplay.errors.length, 1, "Malformed replay segments log once");
  deepEqual(damagedReplay.result, {
    ...turnFixture,
    replayed: true,
    pally: { ...turnFixture.pally, segments: null },
  }, "Malformed replay segments do not discard the successful replay or its audio");
  assertPlain(renderReply(damagedReplay.result.pally.text, damagedReplay.result.pally.segments), replyText, "Malformed replay fallback");

  for (const { name, raw } of [
    { name: "Invalid History shape", raw: malformed[0].raw },
    { name: "Mismatched History text", raw: [{ kind: "question", text: privateMarker }] },
  ]) {
    const history = captureErrors(() => conversationDetailResponseSchema.parse({
      ...detailFixture,
      turns: [
        historyTurn,
        { ...historyTurn, id: "00000000-0000-4000-8000-000000000003", sequence: 2, pally_segments: raw },
      ],
    }));
    equal(history.errors.length, 1, `${name}: one damaged turn logs once`);
    equal(history.result.turns.length, 2, `${name}: the entire History response remains available`);
    deepEqual(history.result.turns[0], historyTurn, `${name}: other turns remain unchanged`);
    equal(history.result.turns[1].pally_segments, null);
    const historyLog = JSON.stringify(history.errors);
    ok(historyLog.includes("conversation_detail") && historyLog.includes('"turns",1,"pally_segments"'), `${name}: error identifies the damaged turn index`);
    ok(!historyLog.includes(privateMarker), `${name}: error does not include the damaged payload`);
    const restored = conversationTurnsToMessages(conversationId, history.result.turns).filter((message) => message.role === "pally");
    assertReply(renderReply(restored[0].transcript, restored[0].segments), segments, replyText, `${name}: intact turn restoration`);
    assertPlain(renderReply(restored[1].transcript, restored[1].segments), replyText, `${name}: damaged turn fallback`);
  }
  const missingText = captureErrors(() => conversationDetailResponseSchema.parse({
    ...detailFixture,
    turns: [{ ...historyTurn, pally_text: null }],
  }));
  equal(missingText.errors.length, 1, "Segments without History text log once");
  equal(missingText.result.turns[0].pally_segments, null);
  equal(conversationTurnsToMessages(conversationId, missingText.result.turns).filter((message) => message.role === "pally").length, 0, "No phantom reply is created without text");

  const escapedSegments: PallySegment[] = [{ kind: "correction", text: '<script>alert("x")</script> & don\'t\n  trim' }];
  const escaped = turnResponseSchema.parse({ ...turnFixture, pally: { ...turnFixture.pally, text: escapedSegments[0].text, segments: escapedSegments } });
  const escapedMarkup = renderReply(escaped.pally.text, escaped.pally.segments);
  assertReply(escapedMarkup, escapedSegments, escaped.pally.text, "Escaping and whitespace");
  ok(!escapedMarkup.includes("<script>"), "Segment text is escaped rather than interpreted as HTML");
  ok(escapedMarkup.includes("whitespace-pre-wrap"), "Reply whitespace remains visible");

  const messages: Message[] = [
    { id: "user", sessionId: conversationId, role: "user", transcript: turnFixture.user.transcript, createdAt },
    { id: "pally", sessionId: conversationId, role: "pally", transcript: replyText, segments: validTurn.result.pally.segments, createdAt },
  ];
  for (const expanded of [false, true]) {
    const markup = renderToStaticMarkup(createElement(ChatBubble, { messages, expanded, onToggleExpand: () => undefined }));
    assertReply(markup, segments, replyText, expanded ? "Expanded bubble" : "Short bubble");
  }
  const listening = renderToStaticMarkup(createElement(ChatBubble, { messages, expanded: false, listening: true, onToggleExpand: () => undefined }));
  assertReply(listening, segments, replyText, "Previous reply while listening");
  ok(listening.includes("Listening..."));
  const userRow = renderToStaticMarkup(createElement(MessageRow, { speaker: "you", transcript: turnFixture.user.transcript, segments }));
  assertPlain(userRow, turnFixture.user.transcript, "User messages ignore Pally segments");
  assertPlain(renderReply("How was your day?"), "How was your day?", "Plain opener");

  // Only corrections receive emphasis and hidden labels; other reply text stays plain.
  const { Bubble } = await import("../components/v2/Bubble");
  const v2Markup = renderToStaticMarkup(createElement(Bubble, { speaker: "pally", text: replyText, segments }));
  const v2Spans = segmentSpans(v2Markup);
  deepEqual(v2Spans.map((span) => span.kind), segments.map((segment) => segment.kind), "v2 bubble: segment order and count");
  equal(v2Spans.map((span) => span.text).join(""), escapeText(replyText), "v2 bubble: the highlighted spans reproduce the reply");
  equal((v2Markup.match(/<span class="sr-only">고친 표현: <\/span>/g) ?? []).length, segments.filter((segment) => segment.kind === "correction").length, "v2 bubble: one hidden label per correction");
  ok(!v2Markup.includes("새 표현"), "v2 bubble: no obsolete expression label");
  for (const span of v2Spans) {
    const has = (token: string): boolean => span.classes.includes(token);
    equal(has("font-semibold"), span.kind === "correction", `v2 bubble: ${span.kind} semibold only for corrections`);
    equal(has("text-p-primary"), span.kind === "correction", `v2 bubble: ${span.kind} lilac only for corrections`);
    equal(has("decoration-solid"), span.kind === "correction", `v2 bubble: ${span.kind} solid underline only for corrections`);
    equal(has("text-p-secondary"), false, `v2 bubble: ${span.kind} no expression color`);
    equal(has("decoration-dotted"), false, `v2 bubble: ${span.kind} no expression underline`);
    equal(has("underline"), span.kind === "correction", `v2 bubble: ${span.kind} underline only for corrections`);
  }
  ok(/<p[^>]*lang="en"/.test(v2Markup), "v2 bubble: the English reply carries lang=\"en\"");
  ok(!v2Markup.includes("text-primary\"") && !v2Markup.includes("text-accent"), "v2 bubble: no v1 colour classes leak in");
  const v2Plain = renderToStaticMarkup(createElement(Bubble, { speaker: "pally", text: "How was your day?", segments: null }));
  equal(segmentSpans(v2Plain).length, 0, "v2 bubble: plain replies have no styled segments");
  ok(v2Plain.includes("How was your day?"), "v2 bubble: plain replies render their text");
  const v2Listening = renderToStaticMarkup(createElement(Bubble, { speaker: "me", text: "", placeholder: true }));
  ok(!v2Listening.includes("Listening"), "v2 bubble: the listening placeholder shows no transcript-like text");
  ok(v2Listening.includes("듣고 있어요"), "v2 bubble: the listening placeholder is announced to screen readers");

  console.log("Pally segment checks passed: independent validation, private error logs, POST/GET/replay, fallbacks, chat rendering and the v2 bubble.");
}

void main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
