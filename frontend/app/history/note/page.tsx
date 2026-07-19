import { ConversationNoteCard } from "@/components/feedback/ConversationNoteCard";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";

export default function FeedbackNotePage() {
  return (
    <MobileShell>
      <h1 className="absolute left-5 top-[62px] text-display text-primary">History</h1>
      <div className="absolute left-5 right-5 top-[180px]">
        <ConversationNoteCard title="친구 생일 파티에 가기" />
      </div>
      <BottomNav />
    </MobileShell>
  );
}
