import { cn } from "@/lib/utils";

type StepProgressProps = {
  step: number;
  total: number;
  className?: string;
};

/** Single onboarding progress bar. Remaining segments use border-control for 3:1 contrast. */
export function StepProgress({ step, total, className }: StepProgressProps) {
  return (
    <div
      aria-valuemax={total}
      aria-valuemin={1}
      aria-valuenow={step}
      aria-valuetext={`${total}단계 중 ${step}단계`}
      className={cn("flex w-full items-center gap-[6px]", className)}
      role="progressbar"
    >
      {Array.from({ length: total }, (_, index) => (
        <span className={cn("h-[4px] flex-1 rounded-[2px]", index < step ? "bg-p-primary" : "bg-p-border-control")} key={index} />
      ))}
    </div>
  );
}
