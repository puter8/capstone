'use client';

import { useCallback, useRef } from 'react';
import { pickMimeType } from './pickMimeType';

const MAX_DURATION_MS = 30_000;
const RECOGNITION_TIMEOUT_MS = 1500; // max wait after recognition.stop() for onend

const ERR_NO_MIME = '이 브라우저는 음성 녹음을 지원하지 않아요.';
const ERR_MIC_ACCESS = '마이크에 접근할 수 없어요.';

export interface RecorderHandlers {
  onStart: () => void;
  /** transcript: Web Speech API result when available (Chrome desktop). */
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

// Web Speech API disabled on Android: its SpeechRecognition.start() triggers a separate
// microphone permission dialog on each use, independent of getUserMedia.
// iOS uses WAV STT backend path and works fine without Web Speech API.
function getSpeechRecognitionCtor(): unknown {
  if (typeof window === 'undefined') return null;
  if (/Android/i.test(navigator.userAgent)) return null;
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
  // Updated by onresult (interimResults:true) in real-time.
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
      // recognition.stop() is called inside recorder.onstop so Chrome has
      // time to process the last audio chunk before we ask it to finalize.
    }
  }, []);

  const start = useCallback(async (): Promise<void> => {
    const mime = pickMimeType();
    if (!mime) { handlers.onError(ERR_NO_MIME); return; }
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

    // Start Web Speech API after getUserMedia (mic permission already granted — no second prompt).
    const SpeechRecognitionCtor = getSpeechRecognitionCtor();
    if (SpeechRecognitionCtor) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const recognition = new (SpeechRecognitionCtor as any)();
        recognition.lang = 'en-US';
        recognition.continuous = true;
        // interimResults:true → liveTranscriptRef updated as speech is detected,
        // so we always have the latest text even before onend fires.
        recognition.interimResults = true;
        recognition.onresult = (e: { results: { length: number; [i: number]: { [j: number]: { transcript: string } } } }) => {
          let text = '';
          for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript + ' ';
          liveTranscriptRef.current = text.trim();
        };
        // onerror is handled per-call in onstop; don't override here.
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

      const recognition = recognitionRef.current;
      recognitionRef.current = null;

      if (!recognition) {
        // No Web Speech API — go straight to WAV STT fallback.
        liveTranscriptRef.current = '';
        handlers.onStop(blob, undefined);
        return;
      }

      // Wait for recognition to fully finalize after stop().
      // Chrome fires onresult → onend after stop(); onend is our signal that processing is done.
      // Safety timeout (RECOGNITION_TIMEOUT_MS) catches cases where onend is delayed.
      const getTranscript = new Promise<string>((resolve) => {
        let settled = false;
        const settle = (text: string) => {
          if (settled) return;
          settled = true;
          resolve(text);
        };
        recognition.onend = () => settle(liveTranscriptRef.current);
        recognition.onerror = () => settle(liveTranscriptRef.current || '');
        window.setTimeout(() => settle(liveTranscriptRef.current || ''), RECOGNITION_TIMEOUT_MS);
        try { recognition.stop(); } catch { settle(liveTranscriptRef.current || ''); }
      });

      void getTranscript.then((transcript) => {
        liveTranscriptRef.current = '';
        handlers.onStop(blob, transcript || undefined);
      });
    };

    recorder.start(250);
    handlers.onStart();
    timerRef.current = window.setTimeout(() => { stop(); }, MAX_DURATION_MS);
  }, [handlers, stop]);

  return { start, stop };
}
