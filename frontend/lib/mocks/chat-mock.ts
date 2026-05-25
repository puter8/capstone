/**
 * Phase 1A — Mock transport for /api/chat.
 *
 * SINGLE SWAP POINT (per CONTEXT D-01):
 *   Phase 2 replaces the body of `mockChat` with:
 *     const r = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/chat`, ...);
 *     return r.json() as ChatResponse;
 *   No other file in the codebase may construct a ChatResponse — only this one.
 *
 * Contract (locked, per CONTEXT D-02 → D-04 + UI-SPEC Copywriting Contract):
 *   - latency: fixed 800ms, no jitter
 *   - reply: "What a bummer! But don't be too sad." (Figma sample)
 *   - hint_ko: { hint: "자연스러운 표현이에요!", expression: "Keep it up!" }
 *   - axes / character: all zeros (1A does not render character morph)
 *   - character_labels: neutral / calm / mild
 *   - tts_audio: null (1A does not play TTS per D-10)
 *   - transcript: echoes req.utterance verbatim
 */

import type { ChatRequest, ChatResponse } from '@/lib/types/chat';

// Fixed 800ms — matches plausible Phase-1C E2E latency for deterministic demo
// screen recordings (per CONTEXT D-04). Do NOT add jitter in 1A.
const FIXED_LATENCY_MS = 800;

const FIXTURE: Omit<ChatResponse, 'transcript'> = {
  status: 'ok',
  reply: "What a bummer! But don't be too sad.",
  tts_audio: null,
  axes: {
    Formality: 0,
    Energy: 0,
    Intimacy: 0,
    Humor: 0,
    Curiosity: 0,
  },
  character: {
    tone_casual: 0,
    energy_level: 0,
    humor_level: 0,
  },
  character_labels: {
    tone: 'neutral',
    energy: 'calm',
    humor: 'mild',
  },
  hint_ko: {
    hint: '자연스러운 표현이에요!',
    expression: 'Keep it up!',
  },
};

export async function mockChat(req: ChatRequest): Promise<ChatResponse> {
  await new Promise<void>((resolve) => setTimeout(resolve, FIXED_LATENCY_MS));
  return {
    ...FIXTURE,
    transcript: req.utterance, // echo
  };
}
