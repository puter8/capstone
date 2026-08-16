"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ConfirmDialog } from "@/components/dialogs/ConfirmDialog";
import { NameEditDialog } from "@/components/dialogs/NameEditDialog";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { ProfileSummary } from "@/components/profile/ProfileSummary";
import { pallyApi } from "@/lib/api";
import type { UserProfile } from "@/lib/api";

type Dialog = "delete" | "logout" | "name" | "withdrawal" | null;

export default function MyPage() {
  const router = useRouter();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    pallyApi.getProfile()
      .then(({ profile: nextProfile }) => {
        if (active) setProfile(nextProfile);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "프로필을 불러오지 못했어요.");
      });
    return () => {
      active = false;
    };
  }, []);

  const updateName = async (nextName: string) => {
    setError(null);
    try {
      const response = await pallyApi.updateProfile({ display_name: nextName });
      setProfile(response.profile);
      setDialog(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "이름을 변경하지 못했어요.");
    }
  };

  const deleteConversations = async () => {
    setError(null);
    try {
      await pallyApi.deleteConversations(crypto.randomUUID());
      setNotice("대화 기록을 모두 삭제했어요.");
      setDialog(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "대화 기록을 삭제하지 못했어요.");
    }
  };

  const deleteAccount = async () => {
    setError(null);
    try {
      await pallyApi.deleteAccount(crypto.randomUUID());
      router.push("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "계정을 삭제하지 못했어요.");
    }
  };

  return (
    <MobileShell>
      <h1 className="absolute left-5 top-[62px] text-display text-primary">My Pally</h1>
      <div className="absolute left-5 right-5 top-[172px] h-[228px]">
        <ProfileSummary name={profile?.display_name || "불러오는 중..."} onEditName={() => setDialog("name")} traits={profile?.traits} />
      </div>
      {error ? <p className="absolute left-5 right-5 top-[420px] text-center text-body-2 text-red-600" role="alert">{error}</p> : null}
      {notice ? <p className="absolute left-5 right-5 top-[420px] text-center text-body-2 text-success" role="status">{notice}</p> : null}

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

      {dialog === "name" && profile ? <NameEditDialog initialName={profile.display_name} onCancel={() => setDialog(null)} onConfirm={(nextName) => { void updateName(nextName); }} /> : null}
      {dialog === "delete" ? <ConfirmDialog body={"삭제하면 모든 대화 기록이 사라지며\n다시 복구할 수 없어요."} confirmLabel="삭제하기" onCancel={() => setDialog(null)} onConfirm={() => { void deleteConversations(); }} title="데이터를 삭제할까요?" /> : null}
      {dialog === "logout" ? <ConfirmDialog body="현재 계정에서 로그아웃할까요?" confirmLabel="로그아웃" onCancel={() => setDialog(null)} onConfirm={() => router.push("/")} title="로그아웃할까요?" /> : null}
      {dialog === "withdrawal" ? <ConfirmDialog body={"탈퇴하면 모든 대화 기록과 설정이 삭제되며\n다시 복구할 수 없어요."} confirmLabel="탈퇴하기" onCancel={() => setDialog(null)} onConfirm={() => { void deleteAccount(); }} title="정말 탈퇴할까요?" /> : null}
    </MobileShell>
  );
}
