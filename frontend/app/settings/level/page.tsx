"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { Button } from "@/components/v2/Button";
import { IconSpinner } from "@/components/v2/icons";
import { LEVEL_OPTIONS, LevelCard } from "@/components/v2/LevelCard";
import { Sheet } from "@/components/v2/Sheet";
import { Toast } from "@/components/v2/Toast";
import { TopBar } from "@/components/v2/TopBar";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { ProfileResponse } from "@/lib/api";
import { cacheProfile, getCurrentUserId, loadDailyExpression, loadProfile, peekProfileSnapshot } from "@/lib/api/route-data";
import type { RouteSnapshot } from "@/lib/api/route-data";
import type { Level } from "@/lib/types/session";
import { routes } from "@/lib/v2/routes";

// Coming from the My page the profile is already in the cache, so paint it instead of
// a spinner. Client-only: on a hard load the cache is empty, so server and client match.
function readProfileSnapshot(): RouteSnapshot<ProfileResponse> | null {
  if (typeof window === "undefined") return null;
  return peekProfileSnapshot();
}

export default function LevelSettingsV2Page() {
  const router = useRouter();
  const [snapshot] = useState(readProfileSnapshot);
  const snapshotLevel = snapshot ? snapshot.data.profile.english_level : null;
  const [level, setLevel] = useState<Level | null>(snapshotLevel);
  const [savedLevel, setSavedLevel] = useState<Level | null>(snapshotLevel);
  const [completedLevel, setCompletedLevel] = useState<Level | null>(null);
  const [isLoading, setIsLoading] = useState(snapshot === null);
  // Saving waits for the session and a fresh profile even when the level is already
  // painted: the cached one may be from another account or changed on another device.
  const [verified, setVerified] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const userIdRef = useRef<string | null>(null);
  const savingRef = useRef(false);

  useEffect(() => {
    let active = true;
    getCurrentUserId()
      .then(async (userId) => {
        userIdRef.current = userId;
        if (active && snapshot && snapshot.userId !== userId) {
          // The painted level belongs to a previous account: hide it until the fresh read.
          setLevel(null);
          setSavedLevel(null);
          setIsLoading(true);
        }
        return loadProfile(userId);
      })
      .then(({ profile }) => {
        if (active) {
          // Keep a choice the user already made on the painted list.
          setLevel((current) => (current === null || current === snapshotLevel ? profile.english_level : current));
          setSavedLevel(profile.english_level);
          setVerified(true);
        }
      })
      .catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") {
          router.replace(routes.login);
          return;
        }
        if (active) setError(caught instanceof Error ? caught.message : "영어 레벨을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router, snapshot, snapshotLevel]);

  const saveLevel = async () => {
    const userId = userIdRef.current;
    if (savingRef.current || isLoading || !verified || !userId || !level || savedLevel === null || level === savedLevel) return;
    savingRef.current = true;
    setIsSaving(true);
    setError(null);
    try {
      const response = await pallyApi.updateProfile({ english_level: level });
      cacheProfile(userId, response);
      void loadDailyExpression(userId).catch((caught: unknown) => console.error("Updated level expression prefetch failed", caught));
      setLevel(response.profile.english_level);
      setSavedLevel(response.profile.english_level);
      setCompletedLevel(response.profile.english_level);
    } catch (caught) {
      console.error("English level update failed", caught);
      setError("저장하지 못했어요. 다시 시도해 주세요.");
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  };

  // Arrow keys move the selection like a native radio group.
  const handleGroupKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!level) return;
    const index = LEVEL_OPTIONS.findIndex((option) => option.code === level);
    if (index < 0) return;
    let next = index;
    if (event.key === "ArrowDown" || event.key === "ArrowRight") next = (index + 1) % LEVEL_OPTIONS.length;
    else if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = (index - 1 + LEVEL_OPTIONS.length) % LEVEL_OPTIONS.length;
    else return;
    event.preventDefault();
    setLevel(LEVEL_OPTIONS[next].code);
    const radios = event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="radio"]');
    radios[next]?.focus();
  };

  const locked = isLoading || isSaving || savedLevel === null;

  return (
    <AppFrame>
      <TopBar backHref={routes.my} title="영어 레벨 변경" variant="back" />
      <p className="px-p-5 pb-p-4 pt-p-2 text-p-small text-p-text-secondary">다음 대화부터 Pally가 고른 레벨에 맞춰 말해요.</p>
      {isLoading ? (
        <p className="flex items-center justify-center gap-p-2 px-p-5 py-p-8 text-p-label text-p-text-secondary" role="status">
          <IconSpinner className="animate-spin motion-reduce:animate-none" size={20} />
          영어 레벨을 불러오고 있어요
        </p>
      ) : null}
      <div aria-label="영어 레벨" className="flex flex-1 flex-col gap-[10px] px-p-5 pb-p-4" onKeyDown={handleGroupKeyDown} role="radiogroup">
        {!isLoading
          ? LEVEL_OPTIONS.map((option) => (
              <LevelCard
                code={option.code}
                current={savedLevel === option.code}
                description={option.description}
                disabled={locked}
                key={option.code}
                name={option.name}
                onSelect={() => setLevel(option.code)}
                selected={level === option.code}
              />
            ))
          : null}
      </div>
      <div className="sticky bottom-0 bg-p-bg px-p-5 pb-[calc(var(--p-space-6)+env(safe-area-inset-bottom))] pt-p-2">
        <Button
          disabled={locked || !verified || level === savedLevel}
          fullWidth
          loading={isSaving}
          loadingLabel="저장 중…"
          onClick={() => {
            void saveLevel();
          }}
        >
          변경하기
        </Button>
      </div>
      {error ? <Toast className="top-[64px]" message={error} onDismiss={() => setError(null)} tone="error" /> : null}
      <Sheet
        actions={
          <Button
            fullWidth
            onClick={() => {
              setCompletedLevel(null);
              router.push(routes.my);
            }}
          >
            확인
          </Button>
        }
        description={completedLevel ? `영어 레벨을 ${completedLevel}로 바꿨어요. 다음 대화부터 적용돼요.` : undefined}
        open={completedLevel !== null}
        title="변경 완료"
      />
    </AppFrame>
  );
}
