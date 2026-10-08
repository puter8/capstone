import { MobileShell } from "@/components/layout/MobileShell";
import { PrimaryButton } from "@/components/ui/PrimaryButton";

type ErrorScreenProps = {
  onRetry: () => void;
};

// Shared by app/error.tsx and app/global-error.tsx. The home link is a plain anchor so
// that leaving this screen reloads the app instead of reusing the state that just failed.
export function ErrorScreen({ onRetry }: ErrorScreenProps) {
  return (
    <MobileShell minHeight={560}>
      <div className="absolute inset-x-5 top-1/2 flex -translate-y-1/2 flex-col items-center gap-8 text-center">
        <div className="flex flex-col items-center gap-2">
          <h1 className="text-title-1 text-text">문제가 생겼어요</h1>
          <p className="break-keep text-body text-text-tertiary">화면을 불러오는 중에 오류가 났어요. 다시 시도해 주세요.</p>
        </div>
        <div className="flex w-full flex-col items-center gap-4">
          <PrimaryButton onClick={onRetry}>다시 시도</PrimaryButton>
          <a className="text-body text-text-tertiary underline" href="/home">홈으로 가기</a>
        </div>
      </div>
    </MobileShell>
  );
}
