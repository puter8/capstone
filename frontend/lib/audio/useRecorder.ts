'use client';

import { useCallback, useRef } from 'react';
import { pickMimeType } from './pickMimeType';

const MAX_DURATION_MS = 30_000;

const ERR_NO_MIME = '이 브라우저는 음성 녹음을 지원하지 않아요.';
const ERR_MIC_ACCESS = '마이크에 접근할 수 없어요.';

export interface RecorderHandlers {
  onStart: () => void;
  /** blob: recorded audio from MediaRecorder. */
  onStop: (blob: Blob | null) => void;
  onPermissionDenied: () => void;
  onError: (message: string) => void;
}

export interface RecorderControls {
  start: () => Promise<void>;
  stop: () => void;
  cancel: () => void;
}

export function useRecorder(handlers: RecorderHandlers): RecorderControls {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const mimeRef = useRef<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const discardRecordingRef = useRef(false);
  const startingRef = useRef(false);

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

  const cancel = useCallback((): void => {
    discardRecordingRef.current = true;
    stop();
  }, [stop]);

  const start = useCallback(async (): Promise<void> => {
    if (startingRef.current || recorderRef.current?.state === 'recording') return;

    startingRef.current = true;
    discardRecordingRef.current = false;

    const mime = pickMimeType();
    if (!mime) {
      startingRef.current = false;
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
      startingRef.current = false;
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

    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(stream, { mimeType: mime });
    } catch (error) {
      startingRef.current = false;
      cleanupStream();
      console.error('MediaRecorder initialization failed.', error);
      handlers.onError(ERR_NO_MIME);
      return;
    }
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
      const shouldDiscard = discardRecordingRef.current;

      cleanupStream();
      recorderRef.current = null;
      chunksRef.current = [];
      discardRecordingRef.current = false;

      if (shouldDiscard) return;
      handlers.onStop(blob);
    };

    try {
      recorder.start(250);
    } catch (error) {
      startingRef.current = false;
      recorderRef.current = null;
      cleanupStream();
      console.error('MediaRecorder start failed.', error);
      handlers.onError(ERR_MIC_ACCESS);
      return;
    }
    startingRef.current = false;
    handlers.onStart();
    timerRef.current = window.setTimeout(() => {
      stop();
    }, MAX_DURATION_MS);
  }, [cleanupStream, handlers, stop]);

  return { start, stop, cancel };
}
