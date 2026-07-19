import { TranscriptRow, type TranscriptSpeaker } from "@/components/conversation/TranscriptRow";
import { cn } from "@/lib/utils";

export type ConversationMessage = {
  id: string;
  message: string;
  speaker: TranscriptSpeaker;
};

type ChatExchangeProps = {
  className?: string;
  messages: readonly ConversationMessage[];
};

export function ChatExchange({ className, messages }: ChatExchangeProps) {
  return (
    <div className={cn("flex w-[328px] flex-col items-center gap-3", className)}>
      {messages.map((message) => (
        <TranscriptRow key={message.id} message={message.message} speaker={message.speaker} />
      ))}
    </div>
  );
}
