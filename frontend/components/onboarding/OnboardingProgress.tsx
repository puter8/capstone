import { cn } from "@/lib/utils";

type OnboardingProgressProps = {
  className?: string;
  step: 1 | 2 | 3 | 4 | 5;
  totalSteps?: 3 | 5;
};

export function OnboardingProgress({ className, step, totalSteps = 3 }: OnboardingProgressProps) {
  return (
    <div
      aria-label={`온보딩 ${step}/${totalSteps}`}
      className={cn("flex h-[7px] items-center justify-center gap-2", className)}
      role="progressbar"
      aria-valuemax={totalSteps}
      aria-valuemin={1}
      aria-valuenow={step}
    >
      {Array.from({ length: totalSteps }, (_, index) => index + 1).map((item) => (
        <span
          aria-hidden="true"
          className={cn(
            "h-[7px] rounded-full",
            item === step ? "w-[18px]" : "w-[7px]",
            totalSteps === 5
              ? item === step ? "bg-[#ff6b35]" : "bg-[#ddd]"
              : item === step ? "bg-primary" : "bg-border",
          )}
          key={item}
        />
      ))}
    </div>
  );
}
