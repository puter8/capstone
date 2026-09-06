"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ConfirmDialog } from "@/components/dialogs/ConfirmDialog";
import { NameEditDialog } from "@/components/dialogs/NameEditDialog";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { ProfileSummary } from "@/components/profile/ProfileSummary";
import { ContentSkeleton } from "@/components/ui/ContentSkeleton";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { AccountDeletionStatusResponse, UserProfile } from "@/lib/api";
import {
  clearUserRouteData,
  getCurrentUserId,
  invalidateProfile,
  loadProfile,
} from "@/lib/api/route-data";
import { supabase } from "@/lib/supabase/client";

type Dialog = "delete" | "logout" | "name" | "withdrawal" | null;
const accountDeletionEnabled = process.env.NEXT_PUBLIC_ACCOUNT_DELETION_ENABLED === "true";

export default function MyPage() {
  const router = useRouter();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [deletionStatus, setDeletionStatus] = useState<AccountDeletionStatusResponse>({ status: "none" });
  const userIdRef = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      const userId = await getCurrentUserId();
      userIdRef.current = userId;
      void pallyApi.recordActivityEvent({
        event_id: crypto.randomUUID(),
        event_type: "profile_opened",
        occurred_at: new Date().toISOString(),
      }).catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") return;
        console.error("Activity event failed", caught);
      });
      const { profile: nextProfile } = await loadProfile(userId);
      if (active) setProfile(nextProfile);
    };

    void load()
      .catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") {
          router.replace("/");
          return;
        }
        if (active) setError(caught instanceof Error ? caught.message : "프로필을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => {
    if (!accountDeletionEnabled) return;
    let active = true;
    void pallyApi.getAccountDeletion()
      .then((status) => {
        if (active) setDeletionStatus(status);
      })
      .catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") return;
        console.error("Account deletion status failed", caught);
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
      const userId = userIdRef.current;
      if (userId) invalidateProfile(userId);
      setDialog(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "이름을 변경하지 못했어요.");
    }
  };

  const showUnavailableDeletion = (message: string) => {
    setNotice(null);
    setError(message);
    setDialog(null);
  };

  const logout = async () => {
    setError(null);
    const userId = userIdRef.current;
    const { error: signOutError } = await supabase.auth.signOut();
    if (signOutError) {
      setError(signOutError.message);
      return;
    }
    if (userId) clearUserRouteData(userId);
    window.localStorage.removeItem("pally:conversationId");
    router.push("/");
  };

  const requestAccountDeletion = async () => {
    setError(null);
    setNotice(null);
    try {
      const status = await pallyApi.requestAccountDeletion({ reason: "user_requested" });
      setDeletionStatus(status);
      setDialog(null);
      setNotice("회원탈퇴 요청을 접수했어요.");
    } catch (caught) {
      setDialog(null);
      setError(caught instanceof Error ? caught.message : "회원탈퇴 요청을 접수하지 못했어요.");
    }
  };

  return (
    <MobileShell>
      <h1 className="absolute left-5 top-[62px] text-display text-primary">My Pally</h1>
      {isLoading ? (
        <ContentSkeleton className="absolute left-5 right-5 top-[172px]" rows={2} />
      ) : profile ? (
        <div className="absolute left-5 right-5 top-[172px] h-[228px]">
          <ProfileSummary avatarUrl={profile.avatar_url} name={profile.display_name} onEditName={() => setDialog("name")} traits={profile.traits} />
        </div>
      ) : null}
      {error ? <p className="absolute left-5 right-5 top-[420px] text-center text-body-2 text-red-600" role="alert">{error}</p> : null}
      {notice ? <p className="absolute left-5 right-5 top-[420px] text-center text-body-2 text-success" role="status">{notice}</p> : null}

      <h2 className="absolute left-5 top-[460px] text-title-1 text-text">사용 설정</h2>
      <section aria-label="사용 설정" className="absolute left-0 right-0 top-[509px]">
        <Link className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-t border-[#e6e6e6] text-left font-sf text-[17px] leading-[22px] tracking-[-0.43px] text-black" href="/settings/plans">요금제 및 결제</Link>
        <Link className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-t border-[#e6e6e6] text-left font-sf text-[17px] leading-[22px] tracking-[-0.43px] text-black" href="/settings/level">영어 레벨 변경</Link>
        <button className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-t border-[#e6e6e6] text-left font-sf text-[17px] leading-[22px] tracking-[-0.43px] text-black" onClick={() => setDialog("delete")} type="button">데이터 삭제</button>
      </section>

      <div className="absolute left-0 right-0 top-[722px] z-20 text-center text-button-2 text-text-tertiary">
        <button className="hover:text-text" onClick={() => setDialog("logout")} type="button">로그아웃</button>
        <span aria-hidden="true"> | </span>
        <button
          className="hover:text-text disabled:cursor-not-allowed disabled:text-text-tertiary"
          disabled={!accountDeletionEnabled || deletionStatus.status === "pending"}
          onClick={() => setDialog("withdrawal")}
          type="button"
        >
          {deletionStatus.status === "pending" ? "회원탈퇴 처리 중" : accountDeletionEnabled ? "회원탈퇴" : "회원탈퇴(준비 중)"}
        </button>
      </div>
      <BottomNav />

      {dialog === "name" && profile ? <NameEditDialog initialName={profile.display_name} onCancel={() => setDialog(null)} onConfirm={(nextName) => { void updateName(nextName); }} /> : null}
      {dialog === "delete" ? <ConfirmDialog body="대화 기록 삭제 API가 아직 준비되지 않았어요." confirmLabel="확인" onCancel={() => setDialog(null)} onConfirm={() => showUnavailableDeletion("대화 기록 삭제는 백엔드 준비 후 사용할 수 있어요.")} title="데이터 삭제 준비 중" variant="compact" /> : null}
      {dialog === "logout" ? <ConfirmDialog body="현재 계정에서 로그아웃할까요?" confirmLabel="로그아웃" onCancel={() => setDialog(null)} onConfirm={() => { void logout(); }} title="로그아웃할까요?" variant="compact" /> : null}
      {dialog === "withdrawal" && accountDeletionEnabled ? (
        <ConfirmDialog
          body="탈퇴 요청 후 데이터는 정책에 따라 보관된 뒤 삭제돼요. 계속할까요?"
          confirmLabel="탈퇴 요청"
          onCancel={() => setDialog(null)}
          onConfirm={() => { void requestAccountDeletion(); }}
          title="회원탈퇴를 요청할까요?"
        />
      ) : null}
    </MobileShell>
  );
}
