"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ChallengeTask } from "@/components/challenge/ChallengeTask";
import { StreakCard } from "@/components/challenge/StreakCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { ContentSkeleton } from "@/components/ui/ContentSkeleton";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { AchievementsResponse } from "@/lib/api";
import { getCurrentUserId, loadAchievements, peekAchievementsSnapshot } from "@/lib/api/route-data";
import type { RouteSnapshot } from "@/lib/api/route-data";

// Returning to this tab paints the last known achievements while the fresh read runs.
// Client-only: on a hard load the cache is empty, so server and client markup match.
function readAchievementsSnapshot(): RouteSnapshot<AchievementsResponse> | null {
  if (typeof window === "undefined") return null;
  return peekAchievementsSnapshot();
}

export default function RankingPage() {
  const router = useRouter();
  const [snapshot] = useState(readAchievementsSnapshot);
  const [data, setData] = useState<AchievementsResponse | null>(snapshot ? snapshot.data : null);
  const [isLoading, setIsLoading] = useState(snapshot === null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      const userId = await getCurrentUserId();
      if (!active) return;
      if (snapshot && snapshot.userId !== userId) {
        // The painted data belongs to a previous account: hide it until the fresh read.
        setData(null);
        setIsLoading(true);
      }
      void pallyApi.recordActivityEvent({
        event_id: crypto.randomUUID(),
        event_type: "achievements_opened",
        occurred_at: new Date().toISOString(),
      }).catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") return;
        console.error("Activity event failed", caught);
      });
      const response = await loadAchievements(userId);
      if (active) setData(response);
    };
    void load()
      .catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") {
          router.replace("/");
          return;
        }
        if (active) setError(caught instanceof Error ? caught.message : "Achievements를 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, [router, snapshot]);

  if (isLoading) {
    return (
      <MobileShell minHeight={770}>
        <h1 className="absolute left-5 top-[62px] text-display text-primary">Achievements</h1>
        <ContentSkeleton className="absolute left-4 right-6 top-[140px]" rows={1} />
        <h2 className="absolute left-5 top-[280px] text-title-1 text-text">Daily Tasks</h2>
        <ContentSkeleton className="absolute left-5 right-5 top-[336px]" rows={3} />
        <BottomNav />
      </MobileShell>
    );
  }

  return (
    <MobileShell minHeight={770}>
      <h1 className="absolute left-5 top-[62px] text-display text-primary">Achievements</h1>

      <div className="absolute left-4 right-6 top-[140px] h-[104px]">
        <StreakCard count={data?.streak_count ?? 0} />
      </div>

      <h2 className="absolute left-5 top-[280px] text-title-1 text-text">Daily Tasks</h2>
      <section aria-label="오늘의 과제" className="absolute left-5 right-5 top-[336px] flex flex-col gap-3">
        {error ? <p className="text-center text-body text-red-600" role="alert">{error}</p> : null}
        {data?.daily_tasks.map((task) => (
          <ChallengeTask
            completed={task.status === "completed"}
            description={task.description}
            key={task.id}
            title={task.title}
          />
        ))}
      </section>
      <BottomNav />
    </MobileShell>
  );
}
