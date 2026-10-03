import { pallyApi } from "@/lib/api";

// Pally speaks first when the user taps "대화 시작하기".
// TODO(backend): the opener endpoint does not exist yet. Until it ships, use a
// fixed opener line voiced through the existing /api/tts endpoint. Replace this
// with the real API call (and its response schema) once the backend is ready.

// Keep the thinking state visible long enough to read, even when TTS is fast.
const MIN_THINKING_MS = 1_200;
const STUB_OPENER_TEXT = "Hey, I've been waiting for you! How's your day going so far?";

export interface PallyOpener {
  text: string;
  audio: string | null;
}

export async function requestPallyOpener(): Promise<PallyOpener> {
  const [speech] = await Promise.all([
    pallyApi.synthesizeSpeech(STUB_OPENER_TEXT),
    new Promise<void>((resolve) => {
      window.setTimeout(resolve, MIN_THINKING_MS);
    }),
  ]);
  return { text: STUB_OPENER_TEXT, audio: speech.audio_b64 };
}
