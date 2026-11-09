"use client";

/**
 * Voice baseline registration logic, shared by the onboarding screens.
 *
 * Ported from components/audio/EnergyBaselineRegistration.tsx without its
 * markup: three prompts, one recording each, WAV conversion, length checks,
 * idempotent submission and per-clip server errors (1-based clip_index).
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { pallyApi, PallyApiError } from "@/lib/api";
import type { EnergyBaselineResponse } from "@/lib/api";
import { blobToMonoWav } from "@/lib/audio/blobToWav";
import { useRecorder } from "@/lib/audio/useRecorder";

export type BaselinePhase = "idle" | "starting" | "recording" | "processing" | "submitting";
export type BaselineConfiguration = Extract<EnergyBaselineResponse, { status: "required" }>;
type Clips = [Blob | null, Blob | null, Blob | null];

export type EnergyBaselineRecorder = {
  clips: Clips;
  /** 0–2 while answering, 3 once every prompt has a recording. */
  question: number;
  phase: BaselinePhase;
  /** Seconds recorded so far for the current clip. */
  elapsed: number;
  error: string | null;
  /** Every prompt has a clip and the user is on the review step. */
  complete: boolean;
  busy: boolean;
  recording: boolean;
  /** Start recording the current prompt, or stop the recording in progress. */
  record: () => void;
  /** Re-record one prompt. */
  retry: (index: number) => void;
  /** Jump to the review step while keeping existing clips. */
  keepExisting: () => void;
  save: () => Promise<void>;
  /** Abort any recording in progress (used when leaving the step). */
  cancel: () => void;
  clearError: () => void;
};

export function useEnergyBaselineRecorder(configuration: BaselineConfiguration, onReady: () => void): EnergyBaselineRecorder {
  const { limits } = configuration;
  const [clips, setClips] = useState<Clips>([null, null, null]);
  const [question, setQuestion] = useState(0);
  const [phase, setPhase] = useState<BaselinePhase>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const clipsRef = useRef<Clips>([null, null, null]);
  const phaseRef = useRef<BaselinePhase>("idle");
  const activeQuestion = useRef(0);
  const generation = useRef(0);
  const startedAt = useRef(0);
  const requestKey = useRef<string | null>(null);
  const cancelRef = useRef<() => void>(() => undefined);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  const changePhase = useCallback((next: BaselinePhase) => {
    phaseRef.current = next;
    if (mounted.current) setPhase(next);
  }, []);

  const recorder = useRecorder({
    onStart: () => {
      if (!mounted.current || phaseRef.current !== "starting") {
        cancelRef.current();
        return;
      }
      startedAt.current = performance.now();
      setElapsed(0);
      changePhase("recording");
    },
    onStop: (blob) => {
      if (!mounted.current) return;
      const attempt = generation.current;
      const index = activeQuestion.current;
      changePhase("processing");
      void (async () => {
        try {
          if (!blob) {
            setError("목소리가 녹음되지 않았어요. 다시 시도해 주세요.");
            return;
          }
          const wav = await blobToMonoWav(blob, limits.max_seconds);
          if (!mounted.current || generation.current !== attempt) return;
          if ((wav.size - 44) / 32000 < limits.min_seconds) {
            setError(`${limits.min_seconds}초 이상 편안하게 이야기한 뒤 다시 녹음해 주세요.`);
            return;
          }
          const next: Clips = [...clipsRef.current];
          next[index] = wav;
          clipsRef.current = next;
          setClips(next);
          requestKey.current = null;
          const nextMissing = next.findIndex((clip) => clip === null);
          setQuestion(nextMissing === -1 ? 3 : nextMissing);
        } catch (caught) {
          console.error("Baseline recording processing failed", caught);
          if (mounted.current && generation.current === attempt) setError("녹음을 처리하지 못했어요. 다시 녹음해 주세요.");
        } finally {
          if (generation.current === attempt) changePhase("idle");
        }
      })();
    },
    onPermissionDenied: () => {
      changePhase("idle");
      if (mounted.current) setError("브라우저 설정에서 마이크 권한을 허용한 뒤 다시 눌러 주세요.");
    },
    onError: (message) => {
      changePhase("idle");
      if (mounted.current) setError(message);
    },
  });
  cancelRef.current = recorder.cancel;
  const { cancel: cancelRecording, stop } = recorder;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      generation.current += 1;
      phaseRef.current = "idle";
      cancelRecording();
      clipsRef.current = [null, null, null];
    };
  }, [cancelRecording]);

  useEffect(() => {
    if (phase !== "recording") return;
    const timer = window.setInterval(() => {
      const seconds = (performance.now() - startedAt.current) / 1000;
      setElapsed(Math.min(Math.floor(seconds), limits.max_seconds));
      if (seconds >= limits.max_seconds) stop();
    }, 100);
    return () => window.clearInterval(timer);
  }, [phase, limits.max_seconds, stop]);

  const retry = useCallback((index: number) => {
    if (phaseRef.current !== "idle") return;
    setQuestion(index);
    setError(null);
  }, []);

  const keepExisting = useCallback(() => {
    if (phaseRef.current !== "idle") return;
    setQuestion(3);
    setError(null);
  }, []);

  const record = useCallback(() => {
    if (phaseRef.current === "recording") {
      changePhase("processing");
      stop();
      return;
    }
    if (phaseRef.current !== "idle" || question > 2) return;
    setError(null);
    activeQuestion.current = question;
    generation.current += 1;
    changePhase("starting");
    void recorder.start();
  }, [changePhase, question, recorder, stop]);

  const save = useCallback(async () => {
    if (phaseRef.current !== "idle") return;
    const [first, second, third] = clipsRef.current;
    if (!first || !second || !third) return;
    changePhase("submitting");
    setError(null);
    requestKey.current ??= crypto.randomUUID();
    try {
      const response = await pallyApi.registerEnergyBaseline([first, second, third], requestKey.current);
      if (!mounted.current) return;
      if (response.status !== "ready") throw new Error("목소리 등록이 끝나지 않았어요. 다시 시도해 주세요.");
      clipsRef.current = [null, null, null];
      setClips([null, null, null]);
      onReadyRef.current();
    } catch (caught) {
      if (!mounted.current) return;
      console.error("Voice registration failed", caught);
      if (caught instanceof PallyApiError && caught.code === "invalid_audio") {
        const index = caught.details?.clip_index;
        if (typeof index === "number" && Number.isInteger(index) && index >= 1 && index <= 3) {
          const next: Clips = [...clipsRef.current];
          next[index - 1] = null;
          clipsRef.current = next;
          setClips(next);
          setQuestion(index - 1);
          setError(caught.details?.reason === "clip_too_short"
            ? `${limits.min_seconds}초 이상 편안하게 이야기한 뒤 다시 녹음해 주세요.`
            : "녹음에 목소리가 충분히 담기지 않았어요. 조용한 곳에서 다시 녹음해 주세요.");
        } else {
          setError("녹음을 확인하지 못했어요. 질문을 눌러 각각 다시 녹음해 주세요.");
        }
      } else {
        setError(caught instanceof PallyApiError ? caught.message : "등록하지 못했어요. 다시 시도해 주세요.");
      }
    } finally {
      changePhase("idle");
    }
  }, [changePhase, limits.min_seconds]);

  const cancel = useCallback(() => {
    if (phaseRef.current === "submitting") return;
    generation.current += 1;
    changePhase("idle");
    cancelRecording();
    setError(null);
  }, [cancelRecording, changePhase]);

  const clearError = useCallback(() => setError(null), []);

  const complete = question === 3 && clips.every((clip) => clip !== null);
  return {
    clips,
    question,
    phase,
    elapsed,
    error,
    complete,
    busy: phase !== "idle",
    recording: phase === "recording",
    record,
    retry,
    keepExisting,
    save,
    cancel,
    clearError,
  };
}
