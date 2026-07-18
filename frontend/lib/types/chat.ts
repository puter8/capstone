/**
 * Phase 1A wire types for POST /api/chat.
 *
 * SOURCE OF TRUTH: backend/main.py (Phase 1C Pydantic models).
 * Any shape divergence breaks the Phase 2 mock-to-real swap, so this file
 * mirrors backend/main.py exactly. Re-shape only when Phase 1C ships a change.
 *
 * Note on Axes / CharacterParams: Phase 1B owns frontend/lib/types/character.ts
 * (per .planning/ROADMAP.md Phase 1B SC #5). 1A intentionally defines its own
 * wire-shape copies here so 1A can compile without waiting for 1B. When 1B
 * merges, Phase 2 will re-export from character.ts in one line.
 */

import type { Level } from './session';

export interface ChatRequest {
  utterance: string;
  session_id: string;
  level: Level;
  current_axes?: Axes;
  conversation_history?: Array<{
    role: 'user' | 'pally';
    content: string;
  }>;
}

export interface Axes {
  Formality: number;
  Energy: number;
  Intimacy: number;
  Humor: number;
  Curiosity: number;
}

export interface CharacterParams {
  tone_casual: number;
  energy_level: number;
  humor_level: number;
}

export interface CharacterLabels {
  tone: string;
  energy: string;
  humor: string;
}

export interface InlineHintKo {
  hint: string;
  expression: string;
}

export interface ChatResponse {
  status: string;
  transcript: string;
  reply: string;
  tts_audio: string | null;
  axes: Axes;
  character: CharacterParams;
  character_labels: CharacterLabels;
  hint_ko: InlineHintKo | null;
}
