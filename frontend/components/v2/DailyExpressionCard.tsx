"use client";

import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/utils";

import { IconVolume } from "./icons";

// The approved design uses one fixed example until daily selection is defined.
const EXPRESSION = {
  phrase: "I’m into ~",
  meaning: "~에 푹 빠져 있어요",
  example: "I’m into baking these days.",
  audio: "/audio/daily-expression-into.mp3",
} as const;

export function DailyExpressionCard() {
  const titleId = useId();
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const audio = audioRef.current;
    return () => {
      audio?.pause();
    };
  }, []);

  function togglePlayback() {
    const audio = audioRef.current;
    if (!audio) return;
    if (!audio.paused) {
      audio.pause();
      audio.currentTime = 0;
      return;
    }
    setError(null);
    audio.currentTime = 0;
    void audio.play().catch((caught: unknown) => {
      if (audioRef.current !== audio) return;
      // A second click or unmount can cancel the pending play request.
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      console.error("Daily expression playback failed", caught);
      setPlaying(false);
      setError("소리를 재생하지 못했어요. 다시 눌러 주세요.");
    });
  }

  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-p-1 rounded-p-card border border-p-border bg-p-surface px-p-4 py-p-3">
      <div className="flex h-[44px] items-center justify-between gap-p-3">
        <h2 className="text-p-eyebrow text-p-secondary" id={titleId}>오늘의 표현</h2>
        <button
          aria-label={playing ? "오늘의 표현 예문 듣기 중지" : "오늘의 표현 예문 듣기"}
          aria-pressed={playing}
          className={cn(
            "flex size-[44px] shrink-0 items-center justify-center rounded-p-full bg-p-primary-container text-p-primary",
            "transition-colors duration-p-fast hover:bg-p-raised motion-reduce:transition-none",
            playing && "ring-2 ring-p-primary",
          )}
          onClick={togglePlayback}
          type="button"
        >
          <IconVolume size={20} />
        </button>
      </div>
      <p className="font-p-brand text-p-title-en tracking-[-0.02em] text-p-text" lang="en" style={{ fontVariationSettings: '"SOFT" 0, "WONK" 1' }}>{EXPRESSION.phrase}</p>
      <p className="text-p-small text-p-text-secondary">{EXPRESSION.meaning}</p>
      <p className="text-p-small text-p-text-secondary" lang="en">{EXPRESSION.example}</p>
      <p className="text-p-caption text-p-text-muted">오늘 대화에서 한번 써보세요</p>
      <audio
        onEnded={() => setPlaying(false)}
        onError={() => {
          console.error("Daily expression audio could not load", audioRef.current?.error);
          setPlaying(false);
          setError("소리를 불러오지 못했어요. 다시 눌러 주세요.");
        }}
        onPause={() => setPlaying(false)}
        onPlay={() => setPlaying(true)}
        preload="none"
        ref={audioRef}
        src={EXPRESSION.audio}
      />
      {error ? <p className="text-p-caption text-p-error" role="alert">{error}</p> : null}
    </section>
  );
}
