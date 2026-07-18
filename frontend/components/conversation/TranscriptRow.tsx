import { cn } from "@/lib/utils";

export type TranscriptSpeaker = "you" | "pally" | "thinking";

type TranscriptRowProps = {
  className?: string;
  message: string;
  speaker: TranscriptSpeaker;
};

export function TranscriptRow({ className, message, speaker }: TranscriptRowProps) {
  const isYou = speaker === "you";
  const label = isYou ? "YOU" : speaker === "thinking" ? "Thinking..." : "Pally";

  return (
    <div className={cn("flex min-h-[60px] w-full flex-col items-center gap-1 text-center", className)}>
      <p className={`w-full text-title-2 ${isYou ? "text-primary" : "text-accent"}`}>
        {label}
      </p>
      <p className={`w-full text-body ${isYou ? "text-text-secondary" : "text-text"}`}>
        {message}
      </p>
    </div>
  );
}
