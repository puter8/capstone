'use client';

import { useCallback, useRef } from 'react';
import { pickMimeType } from './pickMimeType';

const MAX_DURATION_MS = 30_000;

const ERR_NO_MIME = '이 브라우저는 음성 녹음을 지원하지 않아요.';
const ERR_MIC_ACCESS = '마이크에 접근할 수 없어요.';

export interface RecorderHandlers {
  onStart: () => void;
  /** blob: recorded audio. transcript: Web Speech API result if available (Chrome). */
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

export function useRecorder(handlers: RecorderHandlers): RecorderControls {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const mimeRef = useRef<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  // Promise that resolves with the Web Speech API transcript when recognition ends.
  const recognitionResultRef = useRef<Promise<string>>(Promise.resolve(''));

  const stop = useCallback((): void => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    // Stop SpeechRecognition first so it processes any remaining audio
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
      recognitionRef.current = null;
    }
    const r = recorderRef.current;
    if (r && r.state !== 'inactive') {
      try { r.requestData(); } catch { /* not all browsers support this */ }
      r.stop();
    }
  }, []);

  const start = useCallback(async (): Promise<void> => {
    const mime = pickMimeType();
    if (!mime) {
      handlers.onError(ERR_NO_MIME);
      return;
    }
    mimeRef.current = mime;

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

    // Web Speech API (Chrome desktop / Android) — bypasses backend STT entirely.
    // Start after getUserMedia so mic permission is already granted (no double prompt).
    const SpeechRecognitionCtor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (SpeechRecognitionCtor) {
      recognitionResultRef.current = new Promise<string>((resolve) => {
        const recognition = new SpeechRecognitionCtor();
        recognition.lang = 'en-US';
        recognition.continuous = true;
        recognition.interimResults = false;
        let accumulated = '';
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        recognition.onresult = (e: any) => {
          // Results is a SpeechRecognitionResultList — cast through unknown for TS compat
          accumulated = (Array.from(e.results as unknown as ArrayLike<{ 0: { transcript: string } }>))
            .map((r) => r[0].transcript)
            .join(' ')
            .trim();
        };
        recognition.onend = () => resolve(accumulated);
        recognition.onerror = () => resolve(''); // fall back to WAV STT
        try { recognition.start(); } catch { resolve(''); return; }
        recognitionRef.current = recognition;
      });
    } else {
      recognitionResultRef.current = Promise.resolve('');
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

      // Wait for SpeechRecognition to finish before surfacing the result.
      // Resolves immediately if Web Speech API is not available.
      void recognitionResultRef.current.then((transcript) => {
        handlers.onStop(blob, transcript || undefined);
      });
    };

    recorder.start(250);
    handlers.onStart();

    timerRef.current = window.setTimeout(() => { stop(); }, MAX_DURATION_MS);
  }, [handlers, stop]);

  return { start, stop };
}
