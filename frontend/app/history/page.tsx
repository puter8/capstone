import { FeedbackCard } from "@/components/feedback/FeedbackCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { PageHeader } from "@/components/ui/PageHeader";

const FEEDBACK = [
  {
    original: "She want some cookie",
    corrected: "She wants some cookies",
    explanation: "She, He, it 같이 3인칭 단수를 이야기할 때는 동사에 s를 붙여서 이야기해요",
  },
  {
    original: "She want some cookie",
    corrected: "She wants some cookies",
    explanation: "She, He, it 같이 3인칭 단수를 이야기할 때는 동사에 s를 붙여서 이야기해요",
  },
  {
    original: "She want some cookie",
    corrected: "She wants some cookies",
    explanation: "She, He, it 같이 3인칭 단수를 이야기할 때는 동사에 s를 붙여서 이야기해요",
  },
] as const;

export default function HistoryPage() {
  return (
    <MobileShell>
      <PageHeader
        backHref="/home"
        className="absolute left-0 top-[60px]"
        description="대화에서 받은 피드백을 확인해보세요."
        title="Feedback"
        variant="back"
      />
      <section aria-label="대화 피드백" className="absolute left-5 right-5 top-[188px] flex flex-col gap-3">
        {FEEDBACK.map((item, index) => (
          <FeedbackCard key={index} {...item} />
        ))}
      </section>
      <BottomNav />
    </MobileShell>
  );
}
