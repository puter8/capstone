'use client';

import { useCallback, useRef } from 'react';
import { pickMimeType } from './pickMimeType';

const MAX_DURATION_MS = 30_000;

const ERR_NO_MIME = '이 브라우저는 음성 녹음을 지원하지 않아요.';
const ERR_MIC_ACCESS = '마이크에 접근할 수 없어요.';

export interface RecorderHandlers {
  onStart: () => void;
  /**
   * blob: recorded audio from MediaRecorder.
   * transcript: reserved for a pre-transcribed result; currently unused.
   */
  onStop: (blob: Blob | null, transcript?: string) => void;
  onPermissionDenied: () => void;
  onError: (message: string) => void;
}

export interface RecorderControls {
  start: () => Promise<void>;
  stop: () => void;
}

export function useRecorder(handlers: RecorderHandlers): RecorderControls {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const mimeRef = useRef<string | null>(null);
  const timerRef = useRef<number | null>(null);

  const cleanupStream = useCallback(() => {
    const stream = streamRef.current;
    if (stream) {
      for (const track of stream.getTracks()) {
        track.stop();
      }
    }
    streamRef.current = null;
  }, []);

  const stop = useCallback((): void => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    const recorder = recorderRef.current;
    if (!recorder || recorder.state === 'inactive') {
      cleanupStream();
      return;
    }

    try {
      recorder.requestData();
    } catch {
      // Some browsers do not support requestData while stopping.
    }
    recorder.stop();
  }, [cleanupStream]);

  const start = useCallback(async (): Promise<void> => {
    const mime = pickMimeType();
    if (!mime) {
      handlers.onError(ERR_NO_MIME);
      return;
    }
    mimeRef.current = mime;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: { ideal: 1 } },
      });
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
    chunksRef.current = [];

    const recorder = new MediaRecorder(stream, { mimeType: mime });
    recorderRef.current = recorder;

    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onerror = () => {
      cleanupStream();
      recorderRef.current = null;
      chunksRef.current = [];
      handlers.onError(ERR_MIC_ACCESS);
    };

    recorder.onstop = () => {
      const captured = chunksRef.current;
      const finalMime = mimeRef.current ?? mime;
      const blob = captured.length > 0 ? new Blob(captured, { type: finalMime }) : null;

      cleanupStream();
      recorderRef.current = null;
      chunksRef.current = [];

      handlers.onStop(blob, undefined);
    };

    recorder.start(250);
    handlers.onStart();
    timerRef.current = window.setTimeout(() => {
      stop();
    }, MAX_DURATION_MS);
  }, [cleanupStream, handlers, stop]);

  return { start, stop };
}
