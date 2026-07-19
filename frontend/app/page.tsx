import Link from "next/link";

import { MobileShell } from "@/components/layout/MobileShell";
import { PallyCharacter } from "@/components/pally/PallyCharacter";

function GoogleMark() {
  return (
    <svg aria-hidden="true" className="size-6" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.9h5.4a4.7 4.7 0 0 1-2 3v2.5h3.3c1.9-1.8 2.9-4.4 2.9-7.4Z" />
      <path fill="#34A853" d="M12 22c2.7 0 5-.9 6.7-2.4l-3.3-2.5c-.9.6-2.1 1-3.4 1-2.6 0-4.8-1.8-5.6-4.2H3v2.6A10 10 0 0 0 12 22Z" />
      <path fill="#FBBC05" d="M6.4 13.9a6 6 0 0 1 0-3.8V7.5H3a10 10 0 0 0 0 9l3.4-2.6Z" />
      <path fill="#EA4335" d="M12 5.9c1.5 0 2.8.5 3.9 1.5l2.9-2.8A9.8 9.8 0 0 0 3 7.5l3.4 2.6C7.2 7.7 9.4 5.9 12 5.9Z" />
    </svg>
  );
}

function KakaoMark() {
  return (
    <svg aria-hidden="true" className="h-5 w-6" viewBox="0 0 24 20" fill="none">
      <path d="M12 1C5.9 1 1 4.8 1 9.4c0 3 2.1 5.7 5.2 7.2l-1.1 3.2c-.1.3.2.5.5.3l4.2-2.7c.7.1 1.4.2 2.2.2 6.1 0 11-3.7 11-8.3S18.1 1 12 1Z" fill="#17120f" />
    </svg>
  );
}

export default function LoginPage() {
  return (
    <MobileShell>
      <div className="absolute left-1/2 top-[-152px] size-[450px] -translate-x-1/2 rounded-full bg-[#08bdca]" />
      <div className="absolute left-3 top-[216px] size-[138px] rounded-full bg-[#ffb84a]" />
      <PallyCharacter className="absolute left-1/2 top-[171px] -translate-x-1/2" priority />

      <h1 className="absolute left-1/2 top-[479px] w-full -translate-x-1/2 text-center text-title-1 font-normal text-black">
        당신을 가장 잘 아는
        <br />
        영어 공부 파트너, <strong className="font-bold">Pally</strong>
      </h1>

      <div className="absolute left-5 right-5 top-[633px] flex flex-col gap-3">
        <Link
          className="flex h-14 items-center justify-center gap-3 rounded-xl border border-[#d9d9d9] bg-white text-sm font-bold text-[#33363f] transition-transform active:scale-[0.99]"
          href="/onboarding"
        >
          <GoogleMark />
          Sign up with Google
        </Link>
        <Link
          className="flex h-14 items-center justify-center gap-3 rounded-xl bg-[#fee500] text-sm font-bold text-[#17120f] transition-transform active:scale-[0.99]"
          href="/onboarding"
        >
          <KakaoMark />
          카카오로 시작하기
        </Link>
      </div>
    </MobileShell>
  );
}
