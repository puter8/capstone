import { cn } from "@/lib/utils";

type OnboardingProgressProps = {
  className?: string;
  step: 1 | 2 | 3;
};

export function OnboardingProgress({ className, step }: OnboardingProgressProps) {
  return (
    <div
      aria-label={`온보딩 ${step}/3`}
      className={cn("flex h-[7px] items-center justify-center gap-2", className)}
      role="progressbar"
      aria-valuemax={3}
      aria-valuemin={1}
      aria-valuenow={step}
    >
      {([1, 2, 3] as const).map((item) => (
        <span
          aria-hidden="true"
          className={cn(
            "h-[7px] rounded-full",
            item === step ? "w-[18px] bg-primary" : "w-[7px] bg-border",
          )}
          key={item}
        />
      ))}
    </div>
  );
}
