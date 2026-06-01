import { cn } from '@/lib/utils';

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
        <p className="font-sans font-semibold text-[20px] leading-7 text-primary">
          Listening...
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-1 w-full text-center">
      <p
        className={cn(
          'font-sans font-semibold text-[20px] leading-7',
          isPally ? 'text-primary' : 'text-accent',
        )}
      >
        {isPally ? 'Pally' : 'YOU'}
      </p>
      <p
        className={cn(
          'font-sans font-normal text-[16px] leading-6',
          isPally ? 'text-text' : 'text-text-tertiary',
        )}
      >
        {state === 'thinking' ? 'Thinking...' : transcript}
      </p>
    </div>
  );
}
