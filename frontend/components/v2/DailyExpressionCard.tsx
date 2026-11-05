"use client";

import { useEffect, useId, useRef, useState } from "react";

import { pallyApi, type DailyExpressionResponse } from "@/lib/api";
import { getCurrentUserId, invalidateDailyExpression, loadDailyExpression, peekDailyExpressionSnapshot } from "@/lib/api/route-data";
import { cn } from "@/lib/utils";

import { IconSpinner, IconVolume } from "./icons";

const CARD_CLASS = "flex flex-col gap-p-1 rounded-p-card border border-p-border bg-p-surface px-p-4 py-p-3";

export function DailyExpressionCard() {
  const [snapshot] = useState(peekDailyExpressionSnapshot);
  const [data, setData] = useState<DailyExpressionResponse | null>(snapshot?.data ?? null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    let request = 0;
    let midnightTimer: ReturnType<typeof setTimeout>;

    const refresh = async (force = false) => {
      const current = ++request;
      clearTimeout(midnightTimer);
      const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
      setData((previous) => previous?.date === today ? previous : null);
      setError(false);
      try {
        const userId = await getCurrentUserId();
        if (!active || request !== current) return;
        if (snapshot && snapshot.userId !== userId) setData(null);
        if (force) invalidateDailyExpression(userId);
        const response = await loadDailyExpression(userId);
        if (!active || request !== current) return;
        setData(response);
        // The server's KST bucket changes at midnight, even with this page open.
        const midnight = Date.parse(`${response.date}T00:00:00+09:00`) + 86_400_000;
        midnightTimer = setTimeout(() => void refresh(true), Math.max(1_000, midnight - Date.now()));
      } catch (caught: unknown) {
        console.error("Daily expression load failed", caught);
        if (active && request === current) {
          setData(null);
          setError(true);
        }
      }
    };
    const onVisible = () => {
      if (document.visibilityState === "visible") void refresh(true);
    };

    void refresh();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      active = false;
      clearTimeout(midnightTimer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [attempt, snapshot]);

  if (data) {
    return <DailyExpressionContent data={data} key={`${data.date}:${data.expression.id}:${data.expression.example_en}`} />;
  }

  return (
    <section aria-label="오늘의 표현" aria-busy={!error} className={CARD_CLASS}>
      <h2 className="text-p-eyebrow text-p-secondary">오늘의 표현</h2>
      {error ? (
        <>
          <p className="text-p-small text-p-text-secondary" role="alert">오늘의 표현을 불러오지 못했어요.</p>
          <button className="min-h-[44px] self-start text-p-label text-p-primary" onClick={() => setAttempt((value) => value + 1)} type="button">다시 불러오기</button>
        </>
      ) : <p className="text-p-small text-p-text-muted" role="status">오늘의 표현을 불러오고 있어요</p>}
    </section>
  );
}

export function DailyExpressionContent({ data }: { data: DailyExpressionResponse }) {
  const titleId = useId();
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const bufferRef = useRef<AudioBuffer | null>(null);
  const requestRef = useRef(0);
  const [playing, setPlaying] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { expression } = data;

  useEffect(() => () => {
    requestRef.current += 1;
    const source = sourceRef.current;
    if (source) {
      source.onended = null;
      source.stop();
      source.disconnect();
    }
    const context = audioContextRef.current;
    if (context && context.state !== "closed") {
      void context.close().catch((caught: unknown) => console.error("Daily expression audio cleanup failed", caught));
    }
    // Strict Mode re-runs effect setup after cleanup in development.
    sourceRef.current = null;
    audioContextRef.current = null;
    bufferRef.current = null;
  }, []);

  async function togglePlayback() {
    const current = ++requestRef.current;
    if (sourceRef.current) {
      sourceRef.current.stop();
      sourceRef.current.disconnect();
      sourceRef.current = null;
      setPlaying(false);
      return;
    }
    if (preparing) {
      setPreparing(false);
      return;
    }
    setError(null);
    setPreparing(true);
    try {
      // Resume within the click gesture, before awaiting TTS, for mobile audio.
      if (!audioContextRef.current) {
        const AudioContextConstructor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioContextRef.current = new AudioContextConstructor();
      }
      const context = audioContextRef.current;
      await context.resume();
      if (requestRef.current !== current) return;
      let buffer = bufferRef.current;
      if (!buffer) {
        const speech = await pallyApi.synthesizeSpeech(expression.example_en);
        if (requestRef.current !== current) return;
        const bytes = Uint8Array.from(atob(speech.audio_b64), (character) => character.charCodeAt(0));
        buffer = await context.decodeAudioData(bytes.buffer);
        if (requestRef.current !== current) return;
        bufferRef.current = buffer;
      }
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);
      source.onended = () => {
        source.disconnect();
        if (sourceRef.current !== source) return;
        sourceRef.current = null;
        setPlaying(false);
      };
      sourceRef.current = source;
      source.start();
      setPreparing(false);
      setPlaying(true);
    } catch (caught: unknown) {
      console.error("Daily expression playback failed", caught);
      if (requestRef.current !== current) return;
      setPreparing(false);
      setPlaying(false);
      setError("소리를 재생하지 못했어요. 다시 눌러 주세요.");
    }
  }

  return (
    <section aria-labelledby={titleId} className={CARD_CLASS}>
      <div className="flex min-h-[44px] items-center justify-between gap-p-3">
        <h2 className="text-p-eyebrow text-p-secondary" id={titleId}>오늘의 표현</h2>
        <button
          aria-label={preparing ? "오늘의 표현 예문 듣기 취소" : playing ? "오늘의 표현 예문 듣기 중지" : "오늘의 표현 예문 듣기"}
          aria-pressed={playing || preparing}
          className={cn(
            "flex size-[44px] shrink-0 items-center justify-center rounded-p-full bg-p-primary-container text-p-primary",
            "transition-colors duration-p-fast hover:bg-p-raised motion-reduce:transition-none",
            playing && "ring-2 ring-p-primary",
          )}
          onClick={() => void togglePlayback()}
          type="button"
        >
          {preparing ? <IconSpinner className="animate-spin motion-reduce:animate-none" size={20} /> : <IconVolume size={20} />}
        </button>
      </div>
      <p className="font-p-brand text-p-title-en tracking-[-0.02em] text-p-text [overflow-wrap:anywhere]" lang="en" style={{ fontVariationSettings: '"SOFT" 0, "WONK" 1' }}>{expression.text}</p>
      <p className="text-p-small text-p-text-secondary">{expression.meaning_ko}</p>
      <p className="text-p-small text-p-text-secondary [overflow-wrap:anywhere]" lang="en">{expression.example_en}</p>
      {error ? <p className="text-p-caption text-p-error" role="alert">{error}</p> : null}
    </section>
  );
}
