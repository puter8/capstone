'use client';

import { useCallback, useRef } from 'react';
import { pickMimeType } from './pickMimeType';

const MAX_DURATION_MS = 30_000;

const ERR_NO_MIME = '이 브라우저는 음성 녹음을 지원하지 않아요.';
const ERR_MIC_ACCESS = '마이크에 접근할 수 없어요.';

export interface RecorderHandlers {
  onStart: () => void;
  /** blob: recorded audio. transcript: Web Speech API result if available. */
  onStop: (blob: Blob | null, transcript?: string) => void;
  onPermissionDenied: () => void;
  onError: (message: string) => void;
}

export interface RecorderControls {
  start: () => Promise<void>;
  stop: () => void;
}

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    SpeechRecognition?: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    webkitSpeechRecognition?: any;
  }
}

// Web Speech API is only used on desktop Chrome (not Android — causes permission popup on every use;
// not iOS — already working via WAV STT backend path).
function getSpeechRecognitionCtor(): unknown {
  if (typeof window === 'undefined') return null;
  const isAndroid = /Android/i.test(navigator.userAgent);
  if (isAndroid) return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function useRecorder(handlers: RecorderHandlers): RecorderControls {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const mimeRef = useRef<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  // Updated in real-time via onresult (interimResults:true) so onstop always has the latest text.
  const liveTranscriptRef = useRef<string>('');

  const stop = useCallback((): void => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const r = recorderRef.current;
    if (r && r.state !== 'inactive') {
      try { r.requestData(); } catch { /* not all browsers support this */ }
      r.stop();
    }
    // NOTE: recognition is stopped AFTER onstop fires (500ms flush window) — not here.
  }, []);

  const start = useCallback(async (): Promise<void> => {
    const mime = pickMimeType();
    if (!mime) {
      handlers.onError(ERR_NO_MIME);
      return;
    }
    mimeRef.current = mime;
    liveTranscriptRef.current = '';

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: { ideal: 1 } } });
    } catch (err) {
      const name = err instanceof DOMException ? err.name : '';
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        handlers.onPermissionDenied();
      } else {
        handlers.onError(ERR_MIC_ACCESS);
      }
      return;
    }
    streamRef.current = stream;

    // Start Web Speech API after getUserMedia (mic permission already granted, no second prompt).
    // interimResults:true → liveTranscriptRef updated continuously so onstop always has latest text.
    const SpeechRecognitionCtor = getSpeechRecognitionCtor();
    if (SpeechRecognitionCtor) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const recognition = new (SpeechRecognitionCtor as any)();
        recognition.lang = 'en-US';
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.onresult = (e: { results: { length: number; [i: number]: { [j: number]: { transcript: string } } } }) => {
          let text = '';
          for (let i = 0; i < e.results.length; i++) {
            text += e.results[i][0].transcript + ' ';
          }
          liveTranscriptRef.current = text.trim();
        };
        recognition.onerror = () => { /* fall through to WAV STT */ };
        recognition.start();
        recognitionRef.current = recognition;
      } catch {
        recognitionRef.current = null;
      }
    }

    const recorder = new MediaRecorder(stream, { mimeType: mime });
    recorderRef.current = recorder;
    chunksRef.current = [];

    recorder.ondataavailable = (e: BlobEvent) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      const captured = chunksRef.current;
      const finalMime = mimeRef.current ?? mime;
      const blob = captured.length > 0 ? new Blob(captured, { type: finalMime }) : null;

      const s = streamRef.current;
      if (s) for (const t of s.getTracks()) t.stop();
      streamRef.current = null;
      recorderRef.current = null;
      chunksRef.current = [];

      // Give SpeechRecognition 500ms to flush any remaining results before reading transcript.
      window.setTimeout(() => {
        const transcript = liveTranscriptRef.current;
        if (recognitionRef.current) {
          try { recognitionRef.current.stop(); } catch { /* ignore */ }
          recognitionRef.current = null;
        }
        liveTranscriptRef.current = '';
        handlers.onStop(blob, transcript || undefined);
      }, 500);
    };

    recorder.start(250);
    handlers.onStart();

    timerRef.current = window.setTimeout(() => { stop(); }, MAX_DURATION_MS);
  }, [handlers, stop]);

  return { start, stop };
}
