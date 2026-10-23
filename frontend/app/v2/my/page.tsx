"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { BottomNav } from "@/components/v2/BottomNav";
import { Button } from "@/components/v2/Button";
import { Field } from "@/components/v2/Field";
import { IconCard, IconGraduation, IconLogOut, IconPencil, IconTrash } from "@/components/v2/icons";
import { ListGroup, ListRow } from "@/components/v2/ListRow";
import { PallyThumb } from "@/components/v2/PallyThumb";
import { Sheet } from "@/components/v2/Sheet";
import { Toast } from "@/components/v2/Toast";
import { TraitChip } from "@/components/v2/TraitChip";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { ProfileResponse, Subscription, UserProfile } from "@/lib/api";
import { CONVERSATION_STORAGE_KEY } from "@/lib/api/resume-conversation";
import { clearUserRouteData, getCurrentUserId, invalidateProfile, loadProfile, loadSubscription, peekProfileSnapshot } from "@/lib/api/route-data";
import type { RouteSnapshot } from "@/lib/api/route-data";
import { DISPLAY_NAME_MAX_LENGTH } from "@/lib/display-name";
import { supabase } from "@/lib/supabase/client";
import { routes } from "@/lib/v2/routes";

type SheetKind = "name" | "delete-data" | "logout" | "withdraw" | null;

// Returning to this tab paints the last known profile while the fresh read runs.
// Client-only: on a hard load the cache is empty, so server and client markup match.
function readProfileSnapshot(): RouteSnapshot<ProfileResponse> | null {
  if (typeof window === "undefined") return null;
  return peekProfileSnapshot();
}

export default function MyV2Page() {
  const router = useRouter();
  const [snapshot] = useState(readProfileSnapshot);
  const [sheet, setSheet] = useState<SheetKind>(null);
  const [profile, setProfile] = useState<UserProfile | null>(snapshot ? snapshot.data.profile : null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(snapshot === null);
  // Account actions need the verified user id, even when the profile is painted from the snapshot.
  const [sessionVerified, setSessionVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [isSavingName, setIsSavingName] = useState(false);
  const [withdrawConfirmation, setWithdrawConfirmation] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [accountDeleted, setAccountDeleted] = useState(false);
  const [isDeletingHistory, setIsDeletingHistory] = useState(false);
  const historyDeletionInFlight = useRef(false);
  const deletionInFlight = useRef(false);
  const userIdRef = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      const userId = await getCurrentUserId();
      userIdRef.current = userId;
      if (!active) return;
      setSessionVerified(true);
      if (snapshot && snapshot.userId !== userId) {
        // The painted profile belongs to a previous account: hide it until the fresh read.
        setProfile(null);
        setIsLoading(true);
      }
      void pallyApi.recordActivityEvent({
        event_id: crypto.randomUUID(),
        event_type: "profile_opened",
        occurred_at: new Date().toISOString(),
      }).catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") return;
        console.error("Activity event failed", caught);
      });
      void loadSubscription(userId)
        .then((response) => {
          if (active) setSubscription(response.subscription);
        })
        .catch((caught: unknown) => console.error("Subscription status failed", caught));
      const { profile: nextProfile } = await loadProfile(userId);
      if (active) setProfile(nextProfile);
    };

    void load()
      .catch((caught: unknown) => {
        if (caught instanceof PallyApiError && caught.code === "unauthorized") {
          router.replace(routes.login);
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
  }, [router, snapshot]);

  const openNameSheet = () => {
    setNameDraft(profile?.display_name ?? "");
    setNameError(null);
    setSheet("name");
  };

  const saveName = async () => {
    const nextName = nameDraft.trim();
    if (!nextName || isSavingName) return;
    setIsSavingName(true);
    setError(null);
    setNameError(null);
    try {
      const response = await pallyApi.updateProfile({ display_name: nextName });
      setProfile(response.profile);
      const userId = userIdRef.current;
      if (userId) invalidateProfile(userId);
      setSheet(null);
    } catch (caught) {
      console.error("Name change failed", caught);
      setNameError(caught instanceof Error ? caught.message : "이름을 바꾸지 못했어요.");
    } finally {
      setIsSavingName(false);
    }
  };

  const deleteHistory = async () => {
    const userId = userIdRef.current;
    if (!userId || historyDeletionInFlight.current) return;
    historyDeletionInFlight.current = true;
    setIsDeletingHistory(true);
    setNotice(null);
    setError(null);
    try {
      await pallyApi.deleteConversationHistory(userId);
      clearUserRouteData(userId);
      window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
      setProfile(null);
      setSheet(null);
      setNotice("대화 기록을 삭제하고 Pally를 처음 모습으로 되돌렸어요.");
      try {
        const response = await loadProfile(userId);
        setProfile(response.profile);
      } catch (caught) {
        console.error("Profile reload after history deletion failed", caught);
        setNotice(null);
        setError("삭제는 끝났지만 프로필을 불러오지 못했어요. 페이지를 새로고침해 주세요.");
      }
    } catch (caught) {
      console.error("Conversation history deletion failed", caught);
      setError(caught instanceof Error ? caught.message : "대화 기록을 삭제하지 못했어요. 다시 시도해 주세요.");
      setSheet(null);
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
      setSheet(null);
      return;
    }
    if (userId) clearUserRouteData(userId);
    window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
    router.push(routes.login);
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
      setError(caught instanceof Error ? caught.message : "회원탈퇴를 마치지 못했어요.");
      setSheet(null);
      deletionInFlight.current = false;
      setIsDeleting(false);
      return;
    }

    setAccountDeleted(true);
    setProfile(null);
    setSheet(null);
    const userId = userIdRef.current;
    if (userId) clearUserRouteData(userId);
    window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
    const { error: signOutError } = await supabase.auth.signOut({ scope: "local" });
    if (signOutError) {
      console.error("Deleted account session cleanup failed", signOutError);
      setNotice("계정과 기록을 삭제했어요. 로그아웃을 눌러 로그인 정보를 정리해 주세요.");
      setIsDeleting(false);
      return;
    }
    window.location.replace(routes.login);
  };

  const isPro = subscription?.entitled ?? false;
  const planLabel = isPro ? "Pro" : "무료";
  const actionsLocked = !profile || !sessionVerified || isDeletingHistory || isDeleting || accountDeleted;

  return (
    <AppFrame withBottomNav>
      <header className="px-p-5 pb-p-4 pt-[28px]">
        <h1 className="text-p-heading tracking-[-0.02em] text-p-text">마이 페이지</h1>
      </header>
      <div className="flex flex-col gap-p-4 px-p-5 pb-p-6 pt-p-1">
        <section aria-label="프로필" className="flex flex-col gap-p-4 rounded-p-sheet bg-p-surface p-p-5">
          {profile ? (
            <>
              <div className="flex items-center gap-[14px]">
                <PallyThumb axes={profile.current_axes} size={64} />
                <div className="flex min-w-0 flex-1 flex-col gap-[2px]">
                  <h2 className="truncate text-p-section tracking-[-0.02em] text-p-text">{profile.display_name}</h2>
                  <p className="text-p-caption text-p-text-muted">
                    <span lang="en">{profile.english_level}</span> · {isPro ? "Pro 이용 중" : "무료 이용 중"}
                  </p>
                </div>
                <button
                  aria-label="이름 수정"
                  className="grid size-p-target shrink-0 place-items-center rounded-p-full bg-p-raised text-p-text"
                  disabled={actionsLocked}
                  onClick={openNameSheet}
                  type="button"
                >
                  <IconPencil size={18} />
                </button>
              </div>
              <hr className="border-0 border-t border-p-border" />
              <div className="flex flex-col gap-[10px]">
                <h3 className="text-p-eyebrow text-p-text-muted">대화하며 생긴 내 Pally의 성격</h3>
                {profile.traits.length > 0 ? (
                  <ul className="flex flex-wrap gap-[6px]">
                    {profile.traits.map((trait) => (
                      <TraitChip key={trait} trait={trait} />
                    ))}
                  </ul>
                ) : (
                  <p className="text-p-small text-p-text-secondary">첫 대화를 마치면 Pally의 성격이 여기에 생겨요.</p>
                )}
              </div>
            </>
          ) : (
            <div aria-busy="true" className="flex flex-col gap-p-4" role="status">
              <span className="sr-only">프로필을 불러오고 있어요</span>
              <div aria-hidden="true" className="flex items-center gap-[14px]">
                <span className="size-[64px] rounded-[18px] bg-p-raised" />
                <span className="flex flex-1 flex-col gap-p-2">
                  <span className="h-[22px] w-[120px] rounded-p-full bg-p-raised" />
                  <span className="h-[12px] w-[90px] rounded-p-full bg-p-raised" />
                </span>
              </div>
              {!isLoading && error ? <p className="text-p-small text-p-text-secondary">프로필을 표시할 수 없어요.</p> : null}
            </div>
          )}
        </section>

        <ListGroup label="사용 설정">
          <ListRow href={routes.level} icon={<IconGraduation size={22} />} label="영어 레벨" value={profile?.english_level} />
          <ListRow href={routes.plans} icon={<IconCard size={22} />} label="요금제 및 결제" value={planLabel} />
          <ListRow
            disabled={actionsLocked}
            icon={<IconTrash size={22} />}
            label="대화 기록 삭제"
            onClick={() => {
              setError(null);
              setNotice(null);
              setSheet("delete-data");
            }}
            tone="danger"
          />
        </ListGroup>

        <div className="flex items-center justify-center gap-p-1 text-p-label">
          <button className="flex min-h-p-target items-center gap-[6px] p-p-3 text-p-text-secondary" onClick={() => setSheet("logout")} type="button">
            <IconLogOut size={18} />
            로그아웃
          </button>
          <span aria-hidden="true" className="text-p-text-muted">
            ·
          </span>
          <button
            className="min-h-p-target p-p-3 text-p-error disabled:text-p-disabled-text"
            disabled={isDeleting || accountDeleted}
            onClick={() => {
              setWithdrawConfirmation("");
              setSheet("withdraw");
            }}
            type="button"
          >
            {accountDeleted ? "회원탈퇴 완료" : isDeleting ? "탈퇴 처리 중…" : "회원탈퇴"}
          </button>
        </div>
      </div>
      <BottomNav />

      {error ? <Toast className="top-p-4" message={error} onDismiss={() => setError(null)} tone="error" /> : null}
      {notice ? <Toast className="top-p-4" message={notice} onDismiss={() => setNotice(null)} tone="info" /> : null}

      <Sheet
        actions={
          <>
            <Button disabled={!nameDraft.trim()} fullWidth loading={isSavingName} loadingLabel="저장 중…" onClick={() => { void saveName(); }}>
              확인
            </Button>
            <Button disabled={isSavingName} fullWidth onClick={() => setSheet(null)} variant="text">
              돌아가기
            </Button>
          </>
        }
        onDismiss={isSavingName ? undefined : () => setSheet(null)}
        open={sheet === "name"}
        title="이름 바꾸기"
      >
        <Field
          autoComplete="nickname"
          error={nameError}
          hint="Pally가 이 이름으로 불러요."
          label="이름"
          maxLength={DISPLAY_NAME_MAX_LENGTH}
          onChange={(event) => setNameDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") void saveName();
          }}
          value={nameDraft}
        />
      </Sheet>

      <Sheet
        actions={
          <>
            <Button fullWidth loading={isDeletingHistory} loadingLabel="삭제 중…" onClick={() => { void deleteHistory(); }} variant="destructive">
              모두 삭제
            </Button>
            <Button disabled={isDeletingHistory} fullWidth onClick={() => setSheet(null)} variant="text">
              돌아가기
            </Button>
          </>
        }
        description="모든 대화 기록과 고친 표현이 지워지고 Pally의 모습과 성격이 처음으로 돌아가요. 지운 기록은 되돌릴 수 없어요. 계정, 요금제, 오늘의 사용량과 업적은 그대로예요."
        onDismiss={isDeletingHistory ? undefined : () => setSheet(null)}
        open={sheet === "delete-data"}
        title="대화 기록을 모두 지울까요?"
      />

      <Sheet
        actions={
          <>
            <Button fullWidth onClick={() => { void logout(); }}>
              로그아웃
            </Button>
            <Button fullWidth onClick={() => setSheet(null)} variant="text">
              돌아가기
            </Button>
          </>
        }
        description="현재 계정에서 로그아웃할까요?"
        onDismiss={() => setSheet(null)}
        open={sheet === "logout"}
        title="로그아웃할까요?"
      />

      <Sheet
        actions={
          <>
            <Button
              disabled={withdrawConfirmation !== "회원탈퇴"}
              fullWidth
              loading={isDeleting}
              loadingLabel="탈퇴 처리 중…"
              onClick={() => { void deleteAccount(); }}
              variant="destructive"
            >
              회원탈퇴
            </Button>
            <Button disabled={isDeleting} fullWidth onClick={() => setSheet(null)} variant="text">
              돌아가기
            </Button>
          </>
        }
        description="계정과 모든 대화·학습 기록이 바로 지워져요. 지운 기록은 되돌릴 수 없고, 다시 가입하면 처음부터 시작해요."
        onDismiss={isDeleting ? undefined : () => setSheet(null)}
        open={sheet === "withdraw"}
        title="정말 탈퇴할까요?"
      >
        <Field
          autoComplete="off"
          disabled={isDeleting}
          hint="계속하려면 ‘회원탈퇴’를 입력해 주세요."
          label="확인 문구"
          onChange={(event) => setWithdrawConfirmation(event.target.value)}
          value={withdrawConfirmation}
        />
      </Sheet>
    </AppFrame>
  );
}
