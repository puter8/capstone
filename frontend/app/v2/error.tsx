"use client";

import { useEffect } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { Button } from "@/components/v2/Button";
import { Stage } from "@/components/v2/Stage";
import { routes } from "@/lib/v2/routes";

export default function ErrorV2({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("v2 screen error", error);
  }, [error]);

  return (
    <AppFrame>
      <div className="flex flex-1 flex-col items-center justify-center gap-p-2 px-p-6 text-center" role="alert">
        <Stage glow={false} size="compact" />
        <h1 className="text-p-section tracking-[-0.02em] text-p-text">화면을 표시하지 못했어요</h1>
        <p className="text-p-small text-p-text-secondary">잠시 후 다시 시도해 주세요. 계속되면 앱을 새로고침해 주세요.</p>
      </div>
      <div className="flex flex-col gap-p-1 px-p-5 pb-[calc(var(--p-space-6)+env(safe-area-inset-bottom))] pt-p-2">
        <Button fullWidth onClick={reset}>
          다시 시도
        </Button>
        <Button fullWidth onClick={() => window.location.assign(routes.home)} variant="text">
          홈으로 가기
        </Button>
      </div>
    </AppFrame>
  );
}
