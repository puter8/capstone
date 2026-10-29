"use client";

import { useId, useMemo, useState } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { BottomNav } from "@/components/v2/BottomNav";
import { Bubble } from "@/components/v2/Bubble";
import { Button } from "@/components/v2/Button";
import { Dock, type DockState } from "@/components/v2/Dock";
import { IconMicOff, IconSpinner, IconVolume } from "@/components/v2/icons";
import { Sheet } from "@/components/v2/Sheet";
import { Stage, type StageState } from "@/components/v2/Stage";
import { TalkCta } from "@/components/v2/TalkCta";
import { Toast } from "@/components/v2/Toast";
import { TopBar, type ConversationStatus } from "@/components/v2/TopBar";
import { UsageChip } from "@/components/v2/UsageChip";
import { UsagePopover } from "@/components/v2/UsagePopover";
import type { PallySegment } from "@/lib/api/contracts";
import { useHomeConversation, type HomeRoutes } from "@/lib/hooks/useHomeConversation";
import type { Message } from "@/lib/types/message";
import { routes } from "@/lib/v2/routes";
import { cn } from "@/lib/utils";

const HOME_ROUTES: HomeRoutes = {
  login: routes.login,
  home: routes.home,
  onboardingVoice: routes.onboardingVoice,
};

const WORDMARK_STYLE = { fontVariationSettings: '"SOFT" 0, "WONK" 1' } as const;

function formatTodayLabel(): string {
  return new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric", weekday: "long", timeZone: "Asia/Seoul" }).format(new Date());
}

function formatDividerDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const parts = new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: "Asia/Seoul" }).formatToParts(date);
  const pick = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${pick("year")}.${pick("month")}.${pick("day")}`;
}

function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("font-p-brand text-p-title-en text-p-text", className)} lang="en" style={WORDMARK_STYLE}>
      Pally
    </span>
  );
}

function SegmentLegend({ segments }: { segments: PallySegment[] }) {
  const correction = segments.find((segment) => segment.kind === "correction");
  if (!correction) return null;
  return (
    <ul aria-label="표시 안내" className="flex flex-wrap items-center gap-x-p-4 gap-y-p-1 px-p-1">
      <li className="flex items-center gap-p-2 text-p-caption text-p-text-muted">
        <span className="text-p-small font-semibold text-p-primary underline decoration-solid underline-offset-4" lang="en">{correction.text}</span>
        고친 표현
      </li>
    </ul>
  );
}

function ThinkingBubble() {
  return (
    <div className="flex w-full flex-col items-start gap-[6px]">
      <span className="text-p-caption text-p-text-muted">Pally</span>
      <div className="rounded-[20px] rounded-tl-[6px] bg-p-surface px-p-4 py-p-3" role="status" aria-label="답변을 준비하고 있어요">
        <span aria-hidden="true" className="flex h-[26px] items-center gap-[6px]">
          {[0, 1, 2].map((index) => (
            <span className="size-[6px] animate-pulse rounded-p-full bg-p-text-muted motion-reduce:animate-none" key={index} style={{ animationDelay: `${index * 150}ms` }} />
          ))}
        </span>
      </div>
    </div>
  );
}

function DateDivider({ iso }: { iso: string }) {
  const label = formatDividerDate(iso);
  if (!label) return null;
  return (
    <div className="flex w-full items-center gap-p-3" role="separator">
      <span className="h-px flex-1 bg-p-border" />
      <span className="text-p-eyebrow text-p-text-muted">{label}</span>
      <span className="h-px flex-1 bg-p-border" />
    </div>
  );
}

export default function HomeV2Page() {
  const home = useHomeConversation(HOME_ROUTES);
  const [usageOpen, setUsageOpen] = useState(false);
  const usagePopoverId = useId();
  const { state, usage, subscription } = home;
  const rec = state.rec;

  const { lastPally, lastUser } = useMemo(() => {
    let pally: Message | null = null;
    let user: Message | null = null;
    for (let index = state.messages.length - 1; index >= 0; index -= 1) {
      const message = state.messages[index];
      if (!pally && message.role === "pally") pally = message;
      else if (pally && !user && message.role === "user") {
        user = message;
        break;
      }
    }
    return { lastPally: pally, lastUser: user };
  }, [state.messages]);

  const isRecording = rec.kind === "recording";
  const isProcessing = rec.kind === "processing";
  const isSpeaking = rec.kind === "speaking" || home.replaying;
  const hasError = rec.kind === "error";
  const inConversation = state.messages.length > 0 || isRecording || isProcessing;
  const plan: "free" | "pro" = usage ? (usage.plan === "pro" ? "pro" : "free") : subscription?.entitled ? "pro" : "free";
  const remaining = usage?.remaining_turns ?? 0;

  const stageState: StageState = isSpeaking ? "speaking" : isRecording ? "listening" : isProcessing || home.isClosing ? "thinking" : "idle";
  const topStatus: ConversationStatus = home.isClosing ? "closing" : isSpeaking ? "speaking" : isRecording ? "listening" : isProcessing ? "processing" : "idle";
  const dockState: DockState = home.quotaExhausted && rec.kind === "idle" && !home.replaying
    ? "disabled"
    : isSpeaking
      ? "speaking"
      : isRecording
        ? "recording"
        : isProcessing
          ? "processing"
          : hasError
            ? "retry"
            : "ready";

  const handleMic = () => {
    switch (dockState) {
      case "ready":
      case "retry":
        home.pressStart();
        break;
      case "recording":
        home.pressStop();
        break;
      case "speaking":
        home.skipPlayback();
        break;
      default:
        break;
    }
  };

  const controlsLocked = home.isClosing || home.isRestoring || !home.hasRestoredPally || !home.baselineAllowed;

  const errorToast = hasError ? (
    <Toast
      className="top-[72px]"
      icon={rec.reason === "permission-denied" ? <IconMicOff size={20} /> : undefined}
      message={rec.message}
      onDismiss={home.dismissError}
      tone="error"
    />
  ) : null;
  const warningToast = home.warning ? <Toast className="top-[72px]" message={home.warning} onDismiss={home.dismissWarning} tone="info" /> : null;

  const limitSheet = (
    <Sheet
      actions={<Button fullWidth onClick={home.closeLimitSheet}>확인</Button>}
      description={`무료 대화 ${usage?.daily_limit ?? 10}회는 내일 0시에 다시 채워져요.`}
      onDismiss={home.closeLimitSheet}
      open={home.limitSheetOpen}
      title="오늘 무료 대화를 모두 썼어요"
    />
  );

  if (home.isRestoring && !home.paintedFromSnapshot) {
    return (
      <AppFrame className="items-center justify-center gap-p-4">
        <p className="flex items-center gap-p-2 text-p-label text-p-text-secondary" role="status">
          <IconSpinner className="animate-spin motion-reduce:animate-none" size={20} />
          대화를 불러오고 있어요
        </p>
        {errorToast}
      </AppFrame>
    );
  }

  if (!inConversation) {
    const ctaDisabled = controlsLocked || home.quotaExhausted;
    return (
      <AppFrame withBottomNav>
        <header className="relative flex items-center px-p-5 pt-p-4">
          <Wordmark className="flex-1" />
          {usage || plan === "pro" ? (
            <UsageChip
              context="home"
              controls={usagePopoverId}
              expanded={usageOpen}
              onClick={() => setUsageOpen((value) => !value)}
              plan={plan}
              remaining={remaining}
            />
          ) : null}
          {usage ? <UsagePopover id={usagePopoverId} onClose={() => setUsageOpen(false)} open={usageOpen} usage={usage} /> : null}
        </header>
        <section className="flex flex-col gap-p-2 px-p-5 pt-[28px]">
          <p className="text-p-eyebrow text-p-text-muted">{formatTodayLabel()}</p>
          <h1 className="text-p-heading tracking-[-0.02em] text-p-text">
            {home.displayName ? `${home.displayName}, 오늘은 어떤 이야기를 해볼까요?` : "오늘은 어떤 이야기를 해볼까요?"}
          </h1>
        </section>
        <div className="flex flex-1 flex-col items-center justify-center gap-p-1 py-p-4">
          <Stage axes={home.axes} size="large" state="idle" />
          <p className="font-p-brand text-p-quote italic text-p-text-secondary" lang="en">
            Pally&apos;s here to chat!
          </p>
          <p className="flex items-center gap-[6px] pt-[6px] text-p-caption text-p-text-muted">
            <IconVolume size={16} />
            소리를 켜고 시작해 주세요
          </p>
        </div>
        <div className="px-p-5 pb-p-4 pt-p-2">
          <TalkCta
            disabled={ctaDisabled}
            label={home.quotaExhausted ? "내일 0시에 다시 대화할 수 있어요" : "대화 시작하기"}
            onClick={home.startConversation}
          />
        </div>
        <BottomNav />
        {errorToast}
        {warningToast}
        {limitSheet}
      </AppFrame>
    );
  }

  if (state.historyOpen) {
    const firstMessage = state.messages[0];
    return (
      <AppFrame>
        <TopBar onBack={home.toggleHistory} title="전체 대화" variant="back" />
        <div className="flex flex-1 flex-col justify-end gap-p-4 px-p-5 py-p-2">
          {firstMessage ? <DateDivider iso={firstMessage.createdAt} /> : null}
          {state.messages.map((message) => (
            <Bubble
              key={message.id}
              segments={message.role === "pally" ? message.segments : undefined}
              speaker={message.role === "pally" ? "pally" : "me"}
              text={message.transcript}
            />
          ))}
          {isProcessing ? <ThinkingBubble /> : null}
        </div>
        <div className="sticky bottom-0 bg-p-bg px-p-5 pb-[calc(var(--p-space-6)+env(safe-area-inset-bottom))] pt-p-2">
          <Button fullWidth onClick={home.toggleHistory} variant="secondary">
            대화로 돌아가기
          </Button>
        </div>
        {errorToast}
        {warningToast}
        {limitSheet}
      </AppFrame>
    );
  }

  const pastPair = isRecording || isProcessing || home.isClosing;
  return (
    <AppFrame withDock>
      <div className="relative">
        <TopBar
          endDisabled={home.isClosing}
          onEnd={() => {
            void home.endSession();
          }}
          status={topStatus}
          trailing={
            usage || plan === "pro" ? (
              <UsageChip
                context="conversation"
                controls={usagePopoverId}
                expanded={usageOpen}
                onClick={() => setUsageOpen((value) => !value)}
                plan={plan}
                remaining={remaining}
              />
            ) : null
          }
          variant="conversation"
        />
        {usage ? <UsagePopover className="right-p-4" id={usagePopoverId} onClose={() => setUsageOpen(false)} open={usageOpen} usage={usage} /> : null}
      </div>
      <div className="flex min-h-[184px] flex-1 flex-col items-center justify-center">
        <Stage axes={home.axes} size="compact" state={stageState} />
      </div>
      <div className="flex flex-col gap-p-4 px-p-5 pb-p-2">
        {isRecording ? (
          <>
            {lastPally ? <Bubble emphasis="past" segments={lastPally.segments} speaker="pally" text={lastPally.transcript} /> : null}
            <Bubble placeholder speaker="me" text="" />
          </>
        ) : isProcessing ? (
          <>
            <Bubble emphasis="past" placeholder speaker="me" text="" />
            <ThinkingBubble />
          </>
        ) : (
          <>
            {lastUser ? <Bubble emphasis={pastPair ? "past" : "current"} speaker="me" text={lastUser.transcript} /> : null}
            {lastPally ? (
              <>
                <Bubble emphasis={home.isClosing ? "past" : "current"} segments={lastPally.segments} speaker="pally" text={lastPally.transcript} />
                {lastPally.segments && !home.isClosing ? <SegmentLegend segments={lastPally.segments} /> : null}
              </>
            ) : null}
          </>
        )}
      </div>
      {home.isClosing ? (
        <div className="sticky bottom-0 flex flex-col items-center gap-p-2 bg-p-bg px-p-5 pb-[calc(var(--p-space-8)+env(safe-area-inset-bottom))] pt-p-4">
          <p className="flex items-center gap-p-2 text-p-label text-p-text" role="status">
            <IconSpinner className="animate-spin motion-reduce:animate-none" size={20} />
            대화를 저장하고 있어요
          </p>
          <p className="text-center text-p-caption text-p-text-muted">저장이 끝나면 피드백 탭에서 고친 표현을 볼 수 있어요.</p>
        </div>
      ) : (
        <Dock
          canReplay={home.canReplay}
          className="sticky bottom-0 bg-p-bg"
          maxRecordingMs={home.maxRecordingMs}
          onPressMic={handleMic}
          onReplay={home.replayLastReply}
          onToggleTranscript={home.toggleHistory}
          recordingStartedAt={rec.kind === "recording" ? rec.startedAt : null}
          replaying={home.replaying}
          state={controlsLocked && dockState === "ready" ? "processing" : dockState}
          statusText={hasError && rec.reason === "permission-denied" ? "권한을 허용한 뒤 눌러 주세요" : undefined}
          transcriptOpen={state.historyOpen}
        />
      )}
      {errorToast}
      {warningToast}
      {limitSheet}
    </AppFrame>
  );
}
