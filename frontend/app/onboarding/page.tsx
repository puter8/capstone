"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type KeyboardEvent } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { Button } from "@/components/v2/Button";
import { Dock, type DockState } from "@/components/v2/Dock";
import { Field } from "@/components/v2/Field";
import { IconCheck, IconInfo, IconMic, IconSpinner, IconWaveform } from "@/components/v2/icons";
import { LEVEL_OPTIONS, LevelCard } from "@/components/v2/LevelCard";
import { PallyThumb } from "@/components/v2/PallyThumb";
import { Stage } from "@/components/v2/Stage";
import { StepProgress } from "@/components/v2/StepProgress";
import { Toast } from "@/components/v2/Toast";
import { TopBar } from "@/components/v2/TopBar";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { EnergyBaselineResponse } from "@/lib/api";
import { DISPLAY_NAME_MAX_LENGTH } from "@/lib/display-name";
import { useEnergyBaselineRecorder, type BaselineConfiguration } from "@/lib/hooks/useEnergyBaselineRecorder";
import { saveOnboardingProfile } from "@/lib/onboarding-save";
import type { Level } from "@/lib/types/session";
import { routes } from "@/lib/v2/routes";
import { cn } from "@/lib/utils";

type Step = "level" | "name" | "voice-intro" | "voice-record" | "done";

const PROMPT_HELP: Record<string, string> = {
  "How was your day today?": "오늘 하루 어땠는지 이야기해 주세요",
  "What's your favorite food, and why?": "좋아하는 음식과 그 이유를 말해 주세요",
  "What do you want to do this week?": "이번 주 하고 싶은 일을 이야기해 주세요",
};

const WORDMARK_STYLE = { fontVariationSettings: '"SOFT" 0, "WONK" 1' } as const;

function TitleBlock({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col gap-p-2 p-p-5">
      <h1 className="text-p-heading tracking-[-0.02em] text-p-text">{title}</h1>
      <p className="text-p-small text-p-text-secondary">{description}</p>
    </div>
  );
}

function StickyCta({ children, caption }: { children: React.ReactNode; caption?: string }) {
  return (
    <div className="sticky bottom-0 flex flex-col gap-p-2 bg-p-bg px-p-5 pb-[calc(var(--p-space-6)+env(safe-area-inset-bottom))] pt-p-2">
      {caption ? <p className="text-center text-p-caption text-p-text-muted">{caption}</p> : null}
      {children}
    </div>
  );
}

type VoiceStepProps = {
  configuration: BaselineConfiguration;
  stepNumber: number;
  totalSteps: number;
  onBack: () => void;
  onReady: () => void;
};

function VoiceRecordStep({ configuration, stepNumber, totalSteps, onBack, onReady }: VoiceStepProps) {
  const { prompts, limits } = configuration;
  const recorder = useEnergyBaselineRecorder(configuration, onReady);
  const { complete, question, phase, clips } = recorder;

  const dockState: DockState = phase === "recording"
    ? "recording"
    : phase === "starting" || phase === "processing" || phase === "submitting"
      ? "processing"
      : recorder.error
        ? "retry"
        : "ready";
  const statusText = phase === "starting"
    ? "마이크를 준비하고 있어요"
    : phase === "processing"
      ? "녹음을 확인하고 있어요"
      : phase === "submitting"
        ? "목소리를 확인하고 있어요"
        : recorder.error
          ? "눌러서 다시 녹음"
          : undefined;

  return (
    <AppFrame>
      <TopBar
        backHidden={phase === "submitting"}
        hideTitle
        onBack={() => {
          recorder.cancel();
          onBack();
        }}
        title="목소리 등록"
        variant="back"
      />
      <div className="px-p-5">
        <StepProgress step={stepNumber} total={totalSteps} />
      </div>
      <TitleBlock
        description={complete ? "등록하면 Pally가 이 억양을 기준으로 모습을 바꿔요." : "조용한 곳에서, 대본을 읽지 말고 편하게 이야기해 주세요."}
        title={complete ? "녹음을 모두 마쳤어요" : "평소처럼 영어로 답해 주세요"}
      />
      <div className="flex flex-1 flex-col gap-p-3 px-p-5 pb-p-2">
        {complete ? (
          <ol aria-label="녹음한 질문" className="flex flex-col gap-p-2">
            {prompts.map((prompt, index) => (
              <li className="flex items-center gap-p-3 rounded-p-card bg-p-surface py-p-3 pl-p-4 pr-p-2" key={prompt}>
                <span aria-hidden="true" className="grid size-[24px] shrink-0 place-items-center rounded-p-full bg-p-secondary text-p-on-secondary">
                  <IconCheck size={16} />
                </span>
                <span className="min-w-0 flex-1 font-p-brand text-p-quote-sm italic text-p-text" lang="en" style={WORDMARK_STYLE}>
                  {prompt}
                </span>
                <Button
                  aria-label={`${index + 1}번 질문 다시 녹음`}
                  disabled={recorder.busy}
                  onClick={() => recorder.retry(index)}
                  size="compact"
                  variant="text"
                >
                  다시 녹음
                </Button>
              </li>
            ))}
          </ol>
        ) : (
          <>
            <section aria-labelledby="voice-question" className="flex flex-col gap-p-3 rounded-p-sheet bg-p-surface p-p-5">
              <div className="flex items-center">
                <ol aria-label="녹음 진행 상태" className="flex items-center gap-[6px]">
                  {prompts.map((prompt, index) => {
                    const done = clips[index] !== null;
                    const active = question === index;
                    return (
                      <li className="flex items-center gap-[6px]" key={prompt}>
                        <button
                          aria-current={active ? "step" : undefined}
                          aria-label={`${index + 1}번 질문${done ? " 녹음 완료, 다시 녹음" : ""}`}
                          className={cn(
                            "grid size-[24px] place-items-center rounded-p-full text-p-eyebrow",
                            active ? "border-2 border-p-primary text-p-primary" : done ? "bg-p-secondary text-p-on-secondary" : "border border-p-border-control text-p-text-muted",
                          )}
                          disabled={recorder.busy || (!done && !active)}
                          onClick={() => recorder.retry(index)}
                          type="button"
                        >
                          {done && !active ? <IconCheck size={14} /> : index + 1}
                        </button>
                        {index < prompts.length - 1 ? <span aria-hidden="true" className={cn("h-[2px] w-[16px] rounded-[1px]", done ? "bg-p-primary" : "bg-p-border")} /> : null}
                      </li>
                    );
                  })}
                </ol>
                <span className="flex-1" />
                <p className="text-p-eyebrow text-p-text-muted">질문 {question + 1} / {limits.clips}</p>
              </div>
              <h2 className="font-p-brand text-p-title-en-sm text-p-text" id="voice-question" lang="en" style={WORDMARK_STYLE}>
                {prompts[question]}
              </h2>
              <p className="text-p-small text-p-text-secondary">{PROMPT_HELP[prompts[question]] ?? "평소 말하듯 편하게 영어로 답해 주세요."}</p>
            </section>
            <div className="flex-1" />
            <Dock
              canReplay={false}
              elapsedMs={recorder.elapsed * 1000}
              maxRecordingMs={limits.max_seconds * 1000}
              onPressMic={recorder.record}
              onReplay={() => undefined}
              onToggleTranscript={() => undefined}
              sideControls={false}
              state={dockState}
              statusText={statusText}
              transcriptOpen={false}
            />
            {!recorder.busy && clips.every((clip) => clip !== null) ? (
              <Button className="self-center" onClick={recorder.keepExisting} size="compact" variant="text">
                기존 녹음 유지하기
              </Button>
            ) : null}
          </>
        )}
      </div>
      <StickyCta caption={complete ? undefined : `질문 ${limits.clips}개에 모두 답하면 등록할 수 있어요`}>
        <Button
          disabled={!complete || recorder.busy}
          fullWidth
          loading={phase === "submitting"}
          loadingLabel="목소리 확인 중…"
          onClick={() => {
            void recorder.save();
          }}
        >
          목소리 등록하고 시작하기
        </Button>
      </StickyCta>
      {recorder.error ? <Toast className="top-[64px]" message={recorder.error} onDismiss={recorder.clearError} tone="error" /> : null}
    </AppFrame>
  );
}

export default function OnboardingV2Page() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("level");
  const [baseline, setBaseline] = useState<EnergyBaselineResponse | null>(null);
  const [isLoadingVoice, setIsLoadingVoice] = useState(false);
  const [voiceEntryFailed, setVoiceEntryFailed] = useState(false);
  const [level, setLevel] = useState<Level | null>(null);
  const [name, setName] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const voiceOnly = new URLSearchParams(window.location.search).get("step") === "voice";
    if (voiceOnly) setIsLoadingVoice(true);
    void pallyApi.getEnergyBaseline()
      .then(async (result) => {
        if (!active) return;
        setBaseline(result);
        if (voiceOnly) {
          const { profile } = await pallyApi.getProfile();
          if (!active) return;
          setName(profile.display_name);
          setLevel(profile.english_level);
          setStep(result.status === "required" ? "voice-intro" : "done");
        }
      })
      .catch((caught: unknown) => {
        console.error("Voice registration status fetch failed", caught);
        if (!active) return;
        if (caught instanceof PallyApiError && caught.code === "unauthorized") router.replace(routes.login);
        else if (caught instanceof PallyApiError && caught.code === "profile_not_found") setStep("level");
        else {
          setError(caught instanceof Error ? caught.message : "목소리 등록 상태를 불러오지 못했어요.");
          if (voiceOnly) setVoiceEntryFailed(true);
        }
      })
      .finally(() => {
        if (active) setIsLoadingVoice(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  const voiceSteps = baseline?.status !== "disabled";
  const totalSteps = voiceSteps ? 5 : 3;
  const stepNumber: Record<Step, number> = { level: 1, name: 2, "voice-intro": 3, "voice-record": 4, done: totalSteps };

  const saveProfile = async () => {
    if (level === null) {
      setError("영어 레벨을 골라 주세요.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await saveOnboardingProfile(pallyApi, { display_name: name.trim(), english_level: level });
      const result = await pallyApi.getEnergyBaseline();
      setBaseline(result);
      setStep(result.status === "required" ? "voice-intro" : "done");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "설정을 저장하지 못했어요.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleLevelKeyDown = useCallback((event: KeyboardEvent<HTMLDivElement>) => {
    const index = LEVEL_OPTIONS.findIndex((option) => option.code === level);
    let next = index < 0 ? 0 : index;
    if (event.key === "ArrowDown" || event.key === "ArrowRight") next = (next + 1) % LEVEL_OPTIONS.length;
    else if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = (next - 1 + LEVEL_OPTIONS.length) % LEVEL_OPTIONS.length;
    else return;
    event.preventDefault();
    setLevel(LEVEL_OPTIONS[next].code);
    event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="radio"]')[next]?.focus();
  }, [level]);

  if (isLoadingVoice) {
    return (
      <AppFrame className="items-center justify-center gap-p-4">
        <Stage glow={false} size="compact" />
        <p className="flex items-center gap-p-2 text-p-label text-p-text-secondary" role="status">
          <IconSpinner className="animate-spin motion-reduce:animate-none" size={20} />
          목소리 등록 상태를 확인하고 있어요
        </p>
      </AppFrame>
    );
  }

  if (voiceEntryFailed) {
    return (
      <AppFrame className="items-center justify-center gap-p-4 px-p-5 text-center">
        <Stage glow={false} size="compact" />
        <div className="flex flex-col gap-p-2">
          <h1 className="text-p-section text-p-text">목소리 등록 상태를 불러오지 못했어요</h1>
          <p className="text-p-body text-p-text-secondary">{error}</p>
        </div>
        <Button onClick={() => window.location.reload()} variant="secondary">
          다시 불러오기
        </Button>
      </AppFrame>
    );
  }

  if (step === "voice-record" && baseline?.status === "required") {
    return (
      <VoiceRecordStep
        configuration={baseline}
        onBack={() => setStep("voice-intro")}
        onReady={() => setStep("done")}
        stepNumber={stepNumber["voice-record"]}
        totalSteps={totalSteps}
      />
    );
  }

  if (step === "done") {
    return (
      <AppFrame>
        <TopBar backHidden hideTitle title="온보딩 완료" variant="back" />
        <div className="px-p-5">
          <StepProgress step={totalSteps} total={totalSteps} />
        </div>
        <div className="flex flex-1 flex-col items-center justify-center gap-p-2 px-p-6 text-center">
          <Stage glow={false} size="large" />
          <h1 className="text-p-display tracking-[-0.02em] text-p-text">다 됐어요!</h1>
          <p className="text-p-small text-p-text-secondary">
            이제 Pally와 영어로 이야기해 봐요.
            <br />
            이름과 영어 레벨은 마이 페이지에서 언제든 바꿀 수 있어요.
          </p>
        </div>
        <StickyCta>
          <Button fullWidth onClick={() => router.push(routes.home)}>
            시작하기
          </Button>
        </StickyCta>
      </AppFrame>
    );
  }

  if (step === "voice-intro" && baseline?.status === "required") {
    const rows = [
      { icon: <IconMic size={20} />, title: "영어로 짧게 3번 답해요", description: `질문마다 ${baseline.limits.min_seconds}초 넘게, 평소 말하듯 편하게 이야기하면 돼요.` },
      { icon: <IconWaveform size={20} />, title: "억양 측정값만 저장해요", description: "녹음 원본은 측정이 끝나면 바로 지워요." },
      { icon: <IconInfo size={20} />, title: "마이크 권한이 필요해요", description: "다음 화면에서 마이크 사용을 허용해 주세요." },
    ];
    return (
      <AppFrame>
        <TopBar hideTitle onBack={() => setStep("name")} title="목소리 등록 소개" variant="back" />
        <div className="px-p-5">
          <StepProgress step={stepNumber["voice-intro"]} total={totalSteps} />
        </div>
        <TitleBlock description="평소 목소리를 기준으로, 대화할 때 억양이 얼마나 살아 있는지에 따라 Pally 모양이 바뀌어요." title="내 목소리로 Pally가 달라져요" />
        <ul className="flex flex-1 flex-col gap-p-3 px-p-5 pb-p-4">
          {rows.map((row) => (
            <li className="flex items-start gap-[14px] rounded-p-card bg-p-surface p-p-4" key={row.title}>
              <span aria-hidden="true" className="grid size-[40px] shrink-0 place-items-center rounded-p-input bg-p-primary-container text-p-primary">
                {row.icon}
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-[2px]">
                <span className="text-p-button text-p-text">{row.title}</span>
                <span className="text-p-small text-p-text-secondary">{row.description}</span>
              </span>
            </li>
          ))}
        </ul>
        <StickyCta>
          <Button fullWidth onClick={() => setStep("voice-record")}>
            시작하기
          </Button>
        </StickyCta>
      </AppFrame>
    );
  }

  const isLevel = step === "level";
  return (
    <AppFrame>
      <TopBar
        backHidden={isLevel}
        hideTitle
        onBack={() => setStep("level")}
        title={isLevel ? "영어 레벨" : "이름 정하기"}
        variant="back"
      />
      <div className="px-p-5">
        <StepProgress step={stepNumber[step]} total={totalSteps} />
      </div>
      {isLevel ? (
        <>
          <TitleBlock description="Pally가 쓰는 단어와 문장 길이를 맞출게요." title="영어 레벨을 골라 주세요" />
          <div aria-label="영어 레벨" className="flex flex-1 flex-col gap-[10px] px-p-5 pb-p-4" onKeyDown={handleLevelKeyDown} role="radiogroup">
            {LEVEL_OPTIONS.map((option) => (
              <LevelCard
                code={option.code}
                description={option.description}
                disabled={isSaving}
                key={option.code}
                name={option.name}
                onSelect={() => setLevel(option.code)}
                selected={level === option.code}
              />
            ))}
          </div>
        </>
      ) : (
        <>
          <TitleBlock description="Pally가 부를 이름을 알려 주세요." title="이름 정하기" />
          <div className="flex flex-1 flex-col items-center gap-p-6 px-p-5 pb-p-4">
            <PallyThumb size={96} />
            <Field
              autoComplete="nickname"
              hint="나중에 마이 페이지에서 바꿀 수 있어요."
              label="이름"
              maxLength={DISPLAY_NAME_MAX_LENGTH}
              onChange={(event) => setName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && name.trim() && !isSaving) void saveProfile();
              }}
              placeholder="이름을 입력해 주세요"
              value={name}
            />
          </div>
        </>
      )}
      <StickyCta>
        <Button
          disabled={isSaving || (isLevel && level === null) || (!isLevel && !name.trim())}
          fullWidth
          loading={isSaving}
          loadingLabel="저장 중…"
          onClick={() => {
            if (isLevel) {
              if (level !== null) setStep("name");
              return;
            }
            void saveProfile();
          }}
        >
          확인
        </Button>
      </StickyCta>
      {error ? <Toast className="top-[64px]" message={error} onDismiss={() => setError(null)} tone="error" /> : null}
    </AppFrame>
  );
}
