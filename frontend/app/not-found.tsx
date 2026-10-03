import Link from "next/link";

import { MobileShell } from "@/components/layout/MobileShell";

export default function NotFound() {
  return (
    <MobileShell minHeight={560}>
      <div className="absolute inset-x-5 top-1/2 flex -translate-y-1/2 flex-col items-center gap-8 text-center">
        <div className="flex flex-col items-center gap-2">
          <h1 className="text-title-1 text-text">페이지를 찾을 수 없어요</h1>
          <p className="text-body text-text-tertiary">주소가 바뀌었거나 삭제된 페이지일 수 있어요.</p>
        </div>
        <Link
          className="flex h-14 w-full items-center justify-center rounded-xl bg-primary transition-transform active:scale-[0.99]"
          href="/home"
        >
          <span className="text-button-2-sb text-white">홈으로 가기</span>
        </Link>
      </div>
    </MobileShell>
  );
}
