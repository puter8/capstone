import Image from "next/image";

import { ChatExchange, type ConversationMessage } from "@/components/conversation/ChatExchange";

type ConversationPanelProps = {
  expanded?: boolean;
  messages: readonly ConversationMessage[];
  onClose: () => void;
  onToggleExpanded: () => void;
};

function ExpandIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 20 10">
      <path
        d={expanded ? "m2 8 8-6 8 6" : "m2 2 8 6 8-6"}
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  );
}

export function ConversationPanel({ expanded = false, messages, onClose, onToggleExpanded }: ConversationPanelProps) {
  if (expanded) {
    return (
      <section aria-label="전체 대화" className="absolute left-0 top-0 z-20 h-[735px] w-full bg-primary-soft rounded-b-[30px]">
        <div className="absolute inset-x-0 top-0 h-[714px] rounded-b-[30px] bg-white" />
        <div className="absolute left-0 top-0 flex h-[516px] w-full flex-col items-center gap-3 overflow-hidden rounded-2xl bg-white px-4 pt-6">
          <ChatExchange className="w-full" messages={messages} />
        </div>
        <button aria-label="대화 접기" className="absolute right-[19px] top-[651px] grid size-10 place-items-center text-text" onClick={onToggleExpanded} type="button">
          <ExpandIcon expanded />
        </button>
      </section>
    );
  }

  return (
    <section aria-label="현재 대화" className="absolute left-0 top-0 z-20 h-[450px] w-full">
      <div className="absolute inset-x-0 top-0 h-[364px] rounded-b-[30px] bg-primary-soft" />
      <Image alt="" aria-hidden="true" className="absolute left-[274px] top-[277px] h-[173px] w-[106px]" height={173} src="/pally/chat-tail.svg" width={106} />
      <div className="absolute inset-x-0 top-0 h-[352px] rounded-b-[30px] bg-white" />
      <button aria-label="대화 닫기" className="absolute left-4 top-[23px] grid size-[41px] place-items-center border-0 bg-transparent p-0 text-xl leading-none text-text" onClick={onClose} type="button">
        ×
      </button>
      <ChatExchange className="absolute left-1/2 top-[110px] -translate-x-1/2" messages={messages.slice(-2)} />
      <button aria-label="대화 펼치기" className="absolute left-[340px] top-[281px] grid size-10 place-items-center text-text" onClick={onToggleExpanded} type="button">
        <ExpandIcon expanded={false} />
      </button>
    </section>
  );
}
