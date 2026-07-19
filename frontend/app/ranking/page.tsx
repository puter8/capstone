import { ChallengeTask } from "@/components/challenge/ChallengeTask";
import { StreakCard } from "@/components/challenge/StreakCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";

const TASKS = [
  { title: "Pally에게 말 걸기", description: "Pally에게 먼저 말을 걸어보세요", completed: false },
  { title: "Pally에게 말 걸기", description: "Pally에게 먼저 말을 걸어보세요", completed: false },
  { title: "Pally에게 말 걸기", description: "Pally에게 먼저 말을 걸어보세요", completed: true },
] as const;

export default function RankingPage() {
  return (
    <MobileShell>
      <h1 className="absolute left-5 top-[62px] text-display text-primary">Achievements</h1>

      <div className="absolute left-4 right-6 top-[140px] h-[91px]">
        <StreakCard />
      </div>

      <h2 className="absolute left-5 top-[280px] text-title-1 text-text">Daily Tasks</h2>
      <section aria-label="오늘의 과제" className="absolute left-5 right-5 top-[336px] flex flex-col gap-3">
        {TASKS.map((task, index) => (
          <ChallengeTask key={index} {...task} />
        ))}
      </section>
      <BottomNav />
    </MobileShell>
  );
}
