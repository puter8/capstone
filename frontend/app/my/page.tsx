"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AccountDeletionDialog } from "@/components/dialogs/AccountDeletionDialog";
import { ConfirmDialog } from "@/components/dialogs/ConfirmDialog";
import { NameEditDialog } from "@/components/dialogs/NameEditDialog";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import { ProfileSummary } from "@/components/profile/ProfileSummary";
import { PageLoader } from "@/components/ui/PageLoader";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { UserProfile } from "@/lib/api";
import {
  clearUserRouteData,
  getCurrentUserId,
  invalidateProfile,
  loadProfile,
} from "@/lib/api/route-data";
import { supabase } from "@/lib/supabase/client";

type Dialog = "delete" | "logout" | "name" | "withdrawal" | null;

export default function MyPage() {
  const router = useRouter();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [accountDeleted, setAccountDeleted] = useState(false);
  const [isDeletingHistory, setIsDeletingHistory] = useState(false);
  const historyDeletionInFlight = useRef(false);
  const historyDeletionUserId = useRef<string | null>(null);
  const deletionInFlight = useRef(false);
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

  const updateName = async (nextName: string) => {
    setError(null);
    setNameError(null);
    try {
      const response = await pallyApi.updateProfile({ display_name: nextName });
      setProfile(response.profile);
      const userId = userIdRef.current;
      if (userId) invalidateProfile(userId);
      setDialog(null);
    } catch (caught) {
      console.error("Name change failed", caught);
      setNameError(caught instanceof Error ? caught.message : "이름을 변경하지 못했어요.");
    }
  };

  const deleteHistory = async () => {
    const userId = historyDeletionUserId.current;
    if (!userId || historyDeletionInFlight.current) return;
    historyDeletionInFlight.current = true;
    setIsDeletingHistory(true);
    setNotice(null);
    setError(null);
    try {
      await pallyApi.deleteConversationHistory(userId);
      clearUserRouteData(userId);
      window.localStorage.removeItem("pally:conversationId");
      setProfile(null);
      setDialog(null);
      setNotice("대화 기록을 삭제하고 Pally를 초기화했어요.");
      try {
        const response = await loadProfile(userId);
        setProfile(response.profile);
      } catch (caught) {
        console.error("Profile reload after history deletion failed", caught);
        setNotice(null);
        setError("삭제는 완료됐지만 프로필을 불러오지 못했어요. 페이지를 새로고침해 주세요.");
      }
    } catch (caught) {
      console.error("Conversation history deletion failed", caught);
      setError(caught instanceof Error ? caught.message : "대화 기록을 삭제하지 못했어요. 다시 시도해 주세요.");
      setDialog(null);
    } finally {
      historyDeletionInFlight.current = false;
      setIsDeletingHistory(false);
    }
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

  const deleteAccount = async () => {
    if (deletionInFlight.current || accountDeleted) return;
    deletionInFlight.current = true;
    setIsDeleting(true);
    setError(null);
    setNotice(null);
    try {
      await pallyApi.deleteAccount({ confirmation: "회원탈퇴" });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "회원탈퇴를 완료하지 못했어요.");
      setDialog(null);
      deletionInFlight.current = false;
      setIsDeleting(false);
      return;
    }

    setAccountDeleted(true);
    setProfile(null);
    setDialog(null);
    const userId = userIdRef.current;
    if (userId) clearUserRouteData(userId);
    window.localStorage.removeItem("pally:conversationId");
    const { error: signOutError } = await supabase.auth.signOut({ scope: "local" });
    if (signOutError) {
      console.error("Deleted account session cleanup failed", signOutError);
      setNotice("계정과 기록이 삭제됐어요. 로그아웃 버튼을 눌러 로그인 정보를 정리해 주세요.");
      setIsDeleting(false);
      return;
    }
    window.location.replace("/");
  };

  if (isLoading) {
    return (
      <MobileShell minHeight={810}>
        <PageLoader delayMs={200} />
      </MobileShell>
    );
  }

  return (
    <MobileShell minHeight={810}>
      <h1 className="absolute left-5 top-[62px] text-display text-primary">My Pally</h1>
      {profile ? (
        <div className="absolute left-5 right-5 top-[172px] h-[228px]">
          <ProfileSummary avatarUrl={profile.avatar_url} name={profile.display_name} onEditName={() => setDialog("name")} traits={profile.traits} />
        </div>
      ) : null}
      {error ? <p className="absolute left-5 right-5 top-[408px] max-h-12 overflow-y-auto text-center text-caption-1 text-red-600" role="alert">{error}</p> : null}
      {notice ? <p className="absolute left-5 right-5 top-[408px] max-h-12 overflow-y-auto text-center text-caption-1 text-success" role="status">{notice}</p> : null}

      <h2 className="absolute left-5 top-[460px] text-title-1 text-text">사용 설정</h2>
      <section aria-label="사용 설정" className="absolute left-0 right-0 top-[509px]">
        <Link className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-t border-[#e6e6e6] text-left font-sf text-[17px] leading-[22px] tracking-[-0.43px] text-black" href="/settings/plans">요금제 및 결제</Link>
        <Link className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-t border-[#e6e6e6] text-left font-sf text-[17px] leading-[22px] tracking-[-0.43px] text-black" href="/settings/level">영어 레벨 변경</Link>
        <button className="ml-6 flex h-[52px] w-[calc(100%-24px)] items-center border-t border-[#e6e6e6] text-left font-sf text-[17px] leading-[22px] tracking-[-0.43px] text-black disabled:opacity-50" disabled={!profile || isDeletingHistory || isDeleting || accountDeleted} onClick={() => { historyDeletionUserId.current = userIdRef.current; setError(null); setNotice(null); setDialog("delete"); }} type="button">데이터 삭제</button>
      </section>

      <div className="absolute bottom-[111px] left-0 right-0 z-20 text-center text-button-2 text-text-tertiary">
        <button className="hover:text-text" onClick={() => setDialog("logout")} type="button">로그아웃</button>
        <span aria-hidden="true"> | </span>
        <button
          className="hover:text-text disabled:cursor-not-allowed disabled:text-text-tertiary"
          disabled={isDeleting || accountDeleted}
          onClick={() => setDialog("withdrawal")}
          type="button"
        >
          {accountDeleted ? "회원탈퇴 완료" : isDeleting ? "탈퇴 처리 중..." : "회원탈퇴"}
        </button>
      </div>
      <BottomNav />

      {dialog === "name" && profile ? <NameEditDialog error={nameError} initialName={profile.display_name} onCancel={() => { setNameError(null); setDialog(null); }} onConfirm={(nextName) => { void updateName(nextName); }} /> : null}
      {dialog === "delete" ? (
        <ConfirmDialog
          body={"모든 대화 기록과 피드백이 삭제되고 Pally의 모습과 성향이 초기화돼요. 삭제한 기록은 복구할 수 없어요.\n\n계정, 요금제, 오늘의 사용량과 업적은 유지돼요."}
          confirmLabel={isDeletingHistory ? "삭제 중…" : "모두 삭제"}
          isPending={isDeletingHistory}
          onCancel={() => { if (!historyDeletionInFlight.current) setDialog(null); }}
          onConfirm={() => { void deleteHistory(); }}
          title="대화 기록을 모두 삭제할까요?"
          variant="compact"
        />
      ) : null}
      {dialog === "logout" ? <ConfirmDialog body="현재 계정에서 로그아웃할까요?" confirmLabel="로그아웃" onCancel={() => setDialog(null)} onConfirm={() => { void logout(); }} title="로그아웃할까요?" variant="compact" /> : null}
      {dialog === "withdrawal" ? (
        <AccountDeletionDialog
          isDeleting={isDeleting}
          onCancel={() => { if (!deletionInFlight.current) setDialog(null); }}
          onConfirm={() => { void deleteAccount(); }}
        />
      ) : null}
    </MobileShell>
  );
}
