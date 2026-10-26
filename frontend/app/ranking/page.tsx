"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { BottomNav } from "@/components/v2/BottomNav";
import { Button } from "@/components/v2/Button";
import { StreakHero } from "@/components/v2/StreakHero";
import { TaskRow } from "@/components/v2/TaskRow";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { AchievementsResponse } from "@/lib/api";
import { getCurrentUserId, loadAchievements, peekAchievementsSnapshot } from "@/lib/api/route-data";
import type { RouteSnapshot } from "@/lib/api/route-data";
import { routes } from "@/lib/v2/routes";
import { cn } from "@/lib/utils";

// Returning to this tab paints the last known achievements while the fresh read runs.
// Client-only: on a hard load the cache is empty, so server and client markup match.
function readAchievementsSnapshot(): RouteSnapshot<AchievementsResponse> | null {
  if (typeof window === "undefined") return null;
  return peekAchievementsSnapshot();
}

function PageHeading() {
  return (
    <header className="flex flex-col gap-[6px] px-p-5 pb-p-4 pt-[28px]">
      <h1 className="text-p-heading tracking-[-0.02em] text-p-text">업적</h1>
      <p className="text-p-small text-p-text-secondary">오늘의 과제를 마치고 연속 기록을 이어가요.</p>
    </header>
  );
}

export default function RankingV2Page() {
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
          router.replace(routes.login);
          return;
        }
        if (active) setError(caught instanceof Error ? caught.message : "업적을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, [router, snapshot]);

  const tasks = data?.daily_tasks ?? [];
  const doneCount = tasks.filter((task) => task.status === "completed").length;

  return (
    <AppFrame withBottomNav>
      <PageHeading />
      <div className="flex flex-col gap-[28px] px-p-5 pb-p-6 pt-p-1">
        {isLoading && !data ? (
          <div aria-busy="true" className="flex flex-col gap-[28px]" role="status">
            <span className="sr-only">업적을 불러오고 있어요</span>
            <div aria-hidden="true" className="h-[186px] rounded-p-sheet bg-p-surface" />
            <div aria-hidden="true" className="flex flex-col gap-p-3">
              <span className="h-[26px] w-[120px] rounded-p-full bg-p-surface" />
              <span className="h-[80px] rounded-p-card bg-p-surface" />
              <span className="h-[80px] rounded-p-card bg-p-surface" />
              <span className="h-[80px] rounded-p-card bg-p-surface" />
            </div>
          </div>
        ) : null}
        {error ? (
          <div className="flex flex-col items-center gap-p-3 py-p-6 text-center" role="alert">
            <p className="text-p-body text-p-text-secondary">{error}</p>
            <Button onClick={() => window.location.reload()} size="compact" variant="secondary">
              다시 시도
            </Button>
          </div>
        ) : null}
        {data ? (
          <>
            <StreakHero count={data.streak_count} />
            <section aria-label="오늘의 과제" className="flex flex-col gap-p-3">
              <div className="flex items-center">
                <h2 className="flex-1 text-p-card tracking-[-0.02em] text-p-text">오늘의 과제</h2>
                <p className="text-p-eyebrow text-p-secondary">
                  {doneCount} / {tasks.length} 완료
                </p>
              </div>
              <div aria-hidden="true" className="flex gap-p-1">
                {tasks.map((task, index) => (
                  <span className={cn("h-[4px] flex-1 rounded-[2px]", index < doneCount ? "bg-p-secondary" : "bg-p-raised")} key={task.id} />
                ))}
              </div>
              <ul className="flex flex-col gap-p-3">
                {tasks.map((task) => (
                  <TaskRow description={task.description} done={task.status === "completed"} key={task.id} title={task.title} />
                ))}
              </ul>
            </section>
          </>
        ) : null}
      </div>
      <BottomNav />
    </AppFrame>
  );
}
