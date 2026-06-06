'use client';

import { useCallback, useRef } from 'react';
import { pickMimeType } from './pickMimeType';

const MAX_DURATION_MS = 30_000;

const ERR_NO_MIME = '이 브라우저는 음성 녹음을 지원하지 않아요.';
const ERR_MIC_ACCESS = '마이크에 접근할 수 없어요.';

export interface RecorderHandlers {
  onStart: () => void;
  /**
   * blob: recorded audio (MediaRecorder path — iOS/Android).
   * transcript: Web Speech API result (Chrome Desktop path — blob is null).
   * Either blob or transcript is always set; never both null.
   */
  onStop: (blob: Blob | null, transcript?: string) => void;
  onPermissionDenied: () => void;
  onError: (message: string) => void;
}

export interface RecorderControls {
  start: () => Promise<void>;
  stop: () => void;
}

declare global {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  interface Window { SpeechRecognition?: any; webkitSpeechRecognition?: any; }
}

/**
 * On Chrome Desktop: use SpeechRecognition exclusively.
 * On Android: skip (SpeechRecognition triggers its own permission dialog every call).
 * On iOS: skip (WAV → backend STT already works fine).
 */
function getSpeechRecognitionCtor(): unknown {
  if (typeof window === 'undefined') return null;
  if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function useRecorder(handlers: RecorderHandlers): RecorderControls {
  // MediaRecorder path (iOS / Android)
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef   = useRef<Blob[]>([]);
  const streamRef   = useRef<MediaStream | null>(null);
  const mimeRef     = useRef<string | null>(null);

  // SpeechRecognition path (Chrome Desktop)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef   = useRef<any>(null);
  const liveTranscriptRef = useRef<string>('');

  const timerRef = useRef<number | null>(null);
  const modeRef  = useRef<'recognition' | 'recorder' | null>(null);

  const stop = useCallback((): void => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    if (modeRef.current === 'recognition') {
      // SpeechRecognition.stop() → Chrome finishes processing → onend fires → handlers.onStop
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch { /* ignore */ }
      }
    } else {
      // MediaRecorder path
      const r = recorderRef.current;
      if (r && r.state !== 'inactive') {
        try { r.requestData(); } catch { /* not all browsers support this */ }
        r.stop();
      }
    }
  }, []);

  const start = useCallback(async (): Promise<void> => {
    liveTranscriptRef.current = '';
    const SpeechRecognitionCtor = getSpeechRecognitionCtor();

    // ── Chrome Desktop: SpeechRecognition only (no MediaRecorder) ──────────
    if (SpeechRecognitionCtor) {
      modeRef.current = 'recognition';
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const recognition = new (SpeechRecognitionCtor as any)();
        recognition.lang = 'en-US';
        recognition.continuous = true;
        recognition.interimResults = true;  // update transcript in real-time

        recognition.onresult = (e: { results: { length: number; [i: number]: { [j: number]: { transcript: string } } } }) => {
          let text = '';
          for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript + ' ';
          liveTranscriptRef.current = text.trim();
        };

        recognition.onerror = () => { /* fall through — onend will still fire */ };

        recognition.onend = () => {
          recognitionRef.current = null;
          modeRef.current = null;
          const transcript = liveTranscriptRef.current;
          liveTranscriptRef.current = '';
          // blob is null — page.tsx uses transcript directly, no backend STT call
          handlers.onStop(null, transcript || undefined);
        };

        recognition.start();
        recognitionRef.current = recognition;
        handlers.onStart();
        timerRef.current = window.setTimeout(() => { stop(); }, MAX_DURATION_MS);
      } catch {
        modeRef.current = null;
        handlers.onError(ERR_MIC_ACCESS);
      }
      return;
    }

    // ── iOS / Android: MediaRecorder + WAV STT backend ─────────────────────
    modeRef.current = 'recorder';
    const mime = pickMimeType();
    if (!mime) { handlers.onError(ERR_NO_MIME); return; }
    mimeRef.current = mime;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: { ideal: 1 } } });
    } catch (err) {
      modeRef.current = null;
      const name = err instanceof DOMException ? err.name : '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        handlers.onPermissionDenied();
      } else {
        handlers.onError(ERR_MIC_ACCESS);
      }
      return;
    }
    streamRef.current = stream;

    const recorder = new MediaRecorder(stream, { mimeType: mime });
    recorderRef.current = recorder;
    chunksRef.current = [];

    recorder.ondataavailable = (e: BlobEvent) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      const captured  = chunksRef.current;
      const finalMime = mimeRef.current ?? mime;
      const blob = captured.length > 0 ? new Blob(captured, { type: finalMime }) : null;

      const s = streamRef.current;
      if (s) for (const t of s.getTracks()) t.stop();
      streamRef.current  = null;
      recorderRef.current = null;
      chunksRef.current  = [];
      modeRef.current    = null;

      handlers.onStop(blob, undefined);
    };

    recorder.start(250);
    handlers.onStart();
    timerRef.current = window.setTimeout(() => { stop(); }, MAX_DURATION_MS);
  }, [handlers, stop]);

  return { start, stop };
}
