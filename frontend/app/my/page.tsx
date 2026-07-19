"use client";

import Link from "next/link";
import { useState } from "react";

import { ConfirmDialog } from "@/components/dialogs/ConfirmDialog";
import { NameEditDialog } from "@/components/dialogs/NameEditDialog";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { ProfileSummary } from "@/components/profile/ProfileSummary";

type Dialog = "delete" | "logout" | "name" | "withdrawal" | null;

export default function MyPage() {
  const [dialog, setDialog] = useState<Dialog>(null);
  const [name, setName] = useState("Ewhain");

  return (
    <MobileShell>
      <h1 className="absolute left-5 top-[62px] text-display text-primary">My Pally</h1>
      <div className="absolute left-5 right-5 top-[172px] h-[228px]">
        <ProfileSummary name={name} onEditName={() => setDialog("name")} />
      </div>

      <h2 className="absolute left-5 top-[460px] text-title-1 text-text">사용 설정</h2>
      <section aria-label="사용 설정" className="absolute left-0 right-0 top-[509px]">
        <Link className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-t border-[#e6e6e6] text-left text-[17px] leading-[22px] text-black" href="/settings/plans">요금제 및 결제</Link>
        <Link className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-t border-[#e6e6e6] text-left text-[17px] leading-[22px] text-black" href="/settings/level">영어 레벨 변경</Link>
        <button className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-y border-[#e6e6e6] text-left text-[17px] leading-[22px] text-black" onClick={() => setDialog("delete")} type="button">데이터 삭제</button>
      </section>

      <div className="absolute left-0 right-0 top-[722px] z-20 text-center text-button-2 text-text-tertiary">
        <button className="hover:text-text" onClick={() => setDialog("logout")} type="button">로그아웃</button>
        <span aria-hidden="true"> | </span>
        <button className="hover:text-text" onClick={() => setDialog("withdrawal")} type="button">회원탈퇴</button>
      </div>
      <BottomNav />

      {dialog === "name" ? <NameEditDialog initialName={name} onCancel={() => setDialog(null)} onConfirm={(nextName) => { setName(nextName); setDialog(null); }} /> : null}
      {dialog === "delete" ? <ConfirmDialog body={"삭제하면 모든 대화 기록이 사라지며\n다시 복구할 수 없어요."} confirmLabel="삭제하기" onCancel={() => setDialog(null)} onConfirm={() => setDialog(null)} title="데이터를 삭제할까요?" /> : null}
      {dialog === "logout" ? <ConfirmDialog body="현재 계정에서 로그아웃할까요?" confirmLabel="로그아웃" onCancel={() => setDialog(null)} onConfirm={() => setDialog(null)} title="로그아웃할까요?" /> : null}
      {dialog === "withdrawal" ? <ConfirmDialog body={"탈퇴하면 모든 대화 기록과 설정이 삭제되며\n다시 복구할 수 없어요."} confirmLabel="탈퇴하기" onCancel={() => setDialog(null)} onConfirm={() => setDialog(null)} title="정말 탈퇴할까요?" /> : null}
    </MobileShell>
  );
}
