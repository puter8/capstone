import Link from "next/link";

import { AppFrame } from "@/components/v2/AppFrame";
import { Stage } from "@/components/v2/Stage";
import { routes } from "@/lib/v2/routes";

export default function NotFoundV2() {
  return (
    <AppFrame>
      <div className="flex flex-1 flex-col items-center justify-center gap-p-2 px-p-6 text-center">
        <Stage glow={false} size="compact" />
        <h1 className="text-p-section tracking-[-0.02em] text-p-text">페이지를 찾을 수 없어요</h1>
        <p className="text-p-small text-p-text-secondary">주소가 바뀌었거나 삭제된 페이지일 수 있어요.</p>
      </div>
      <div className="px-p-5 pb-[calc(var(--p-space-6)+env(safe-area-inset-bottom))] pt-p-2">
        <Link
          className="flex min-h-p-control w-full items-center justify-center rounded-p-input bg-p-primary px-p-5 py-p-3 text-p-button text-p-on-primary"
          href={routes.home}
        >
          홈으로 가기
        </Link>
      </div>
    </AppFrame>
  );
}
