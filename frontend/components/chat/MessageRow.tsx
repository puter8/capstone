type Speaker = 'you' | 'pally';

type MessageRowProps = {
  speaker: Speaker;
  transcript: string;
  state?: 'default' | 'thinking' | 'listening';
  compact?: boolean;
};

export function MessageRow({ speaker, transcript, state = 'default' }: MessageRowProps) {
  const isPally = speaker === 'pally';

  if (state === 'listening') {
    return (
      <div className="flex flex-col items-center w-full text-center">
        <p className="font-sans text-[20px] font-bold leading-7 text-accent">
          Listening...
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-1 w-full text-center">
      <p
        className={`font-sans text-[20px] font-bold leading-7 ${isPally ? 'text-accent' : 'text-primary'}`}
      >
        {isPally ? 'Pally' : 'YOU'}
      </p>
      {state === 'thinking' ? (
        <TypingDots />
      ) : (
        <p
          className={`font-sans text-[16px] font-normal leading-6 ${isPally ? 'text-text' : 'text-text-tertiary'}`}
        >
          {transcript}
        </p>
      )}
    </div>
  );
}

const TYPING_DOT_DELAYS_MS = [0, 160, 320] as const;

function TypingDots() {
  return (
    <span className="flex h-6 items-center gap-1.5" role="status">
      <span className="sr-only">Pally가 생각하고 있어요</span>
      {TYPING_DOT_DELAYS_MS.map((delay) => (
        <span
          aria-hidden="true"
          className="size-2 animate-bounce rounded-full bg-text-tertiary"
          key={delay}
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  );
}
