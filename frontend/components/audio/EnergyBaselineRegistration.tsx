"use client";

import { useEffect, useRef, useState } from "react";
import { MobileShell } from "@/components/layout/MobileShell";
import { OnboardingProgress } from "@/components/onboarding/OnboardingProgress";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { EnergyBaselineResponse } from "@/lib/api";
import { blobToMonoWav } from "@/lib/audio/blobToWav";
import { useRecorder } from "@/lib/audio/useRecorder";
import { cn } from "@/lib/utils";

type Phase = "idle" | "starting" | "recording" | "processing" | "submitting";
type Clips = [Blob | null, Blob | null, Blob | null];
type Props = {
  configuration: Extract<EnergyBaselineResponse, { status: "required" }>;
  onReady: () => void;
  onBack: () => void;
};
const HELP: Record<string, string> = {
  "How was your day today?": "오늘 하루 어땠는지 이야기해 주세요 · 영어로 답해요",
  "What's your favorite food, and why?": "좋아하는 음식과 그 이유를 말해 주세요 · 영어로 답해요",
  "What do you want to do this week?": "이번 주 하고 싶은 일을 이야기해 주세요 · 영어로 답해요",
};
const ASSETS = "/onboarding/voice/";

export function EnergyBaselineRegistration({ configuration, onReady, onBack }: Props) {
  const { prompts, limits } = configuration;
  const [stage, setStage] = useState<"intro" | "record">("intro");
  const [clips, setClips] = useState<Clips>([null, null, null]);
  const [question, setQuestion] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const clipsRef = useRef<Clips>([null, null, null]);
  const phaseRef = useRef<Phase>("idle");
  const activeQuestion = useRef(0);
  const generation = useRef(0);
  const startedAt = useRef(0);
  const requestKey = useRef<string | null>(null);
  const cancelRef = useRef<() => void>(() => undefined);

  const changePhase = (next: Phase) => {
    phaseRef.current = next;
    if (mounted.current) setPhase(next);
  };
  const recorder = useRecorder({
    onStart: () => {
      if (!mounted.current || phaseRef.current !== "starting") { cancelRef.current(); return; }
      startedAt.current = performance.now();
      setElapsed(0);
      changePhase("recording");
    },
    onStop: (blob) => {
      if (!mounted.current) return;
      const attempt = generation.current;
      const index = activeQuestion.current;
      changePhase("processing");
      void (async () => {
        try {
          if (!blob) {
            setError("목소리가 녹음되지 않았어요. 다시 시도해 주세요.");
            return;
          }
          const wav = await blobToMonoWav(blob, limits.max_seconds);
          if (!mounted.current || generation.current !== attempt) return;
          if ((wav.size - 44) / 32000 < limits.min_seconds) {
            setError(`${limits.min_seconds}초 이상 편안하게 이야기한 뒤 다시 녹음해 주세요.`);
            return;
          }
          const next: Clips = [...clipsRef.current];
          next[index] = wav;
          clipsRef.current = next;
          setClips(next);
          requestKey.current = null;
          const nextMissing = next.findIndex((clip) => clip === null);
          setQuestion(nextMissing === -1 ? 3 : nextMissing);
        } catch (caught) {
          console.error("Baseline recording processing failed", caught);
          if (mounted.current && generation.current === attempt) setError("녹음을 처리하지 못했어요. 다시 녹음해 주세요.");
        } finally {
          if (generation.current === attempt) changePhase("idle");
        }
      })();
    },
    onPermissionDenied: () => {
      changePhase("idle");
      if (mounted.current) setError("브라우저 설정에서 마이크 권한을 허용한 뒤 다시 눌러 주세요.");
    },
    onError: (message) => {
      changePhase("idle");
      if (mounted.current) setError(message);
    },
  });
  cancelRef.current = recorder.cancel;
  const { cancel, stop } = recorder;
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      generation.current += 1;
      phaseRef.current = "idle";
      cancel();
      clipsRef.current = [null, null, null];
    };
  }, [cancel]);
  useEffect(() => {
    if (phase !== "recording") return;
    const timer = window.setInterval(() => {
      const seconds = (performance.now() - startedAt.current) / 1000;
      setElapsed(Math.min(Math.floor(seconds), limits.max_seconds));
      if (seconds >= limits.max_seconds) stop();
    }, 100);
    return () => window.clearInterval(timer);
  }, [phase, limits.max_seconds, stop]);

  const busy = phase !== "idle";
  const complete = question === 3 && clips.every((clip) => clip !== null);
  const recording = phase === "recording";
  const retry = (index: number) => {
    if (phaseRef.current !== "idle") return;
    setQuestion(index);
    setError(null);
  };
  const record = () => {
    if (phaseRef.current === "recording") { changePhase("processing"); stop(); return; }
    if (phaseRef.current !== "idle" || question > 2) return;
    setError(null);
    activeQuestion.current = question;
    generation.current += 1;
    changePhase("starting");
    void recorder.start();
  };
  const save = async () => {
    if (phaseRef.current !== "idle") return;
    const [first, second, third] = clipsRef.current;
    if (!first || !second || !third) return;
    changePhase("submitting");
    setError(null);
    requestKey.current ??= crypto.randomUUID();
    try {
      const response = await pallyApi.registerEnergyBaseline([first, second, third], requestKey.current);
      if (!mounted.current) return;
      if (response.status !== "ready") throw new Error("목소리 등록이 완료되지 않았어요. 다시 시도해 주세요.");
      clipsRef.current = [null, null, null];
      setClips([null, null, null]);
      onReady();
    } catch (caught) {
      if (!mounted.current) return;
      console.error("Voice registration failed", caught);
      if (caught instanceof PallyApiError && caught.code === "invalid_audio") {
        const index = caught.details?.clip_index;
        if (typeof index === "number" && Number.isInteger(index) && index >= 1 && index <= 3) {
          const next: Clips = [...clipsRef.current];
          next[index - 1] = null;
          clipsRef.current = next;
          setClips(next);
          setQuestion(index - 1);
          setError(caught.details?.reason === "clip_too_short"
            ? `${limits.min_seconds}초 이상 편안하게 이야기한 뒤 다시 녹음해 주세요.`
            : "녹음에 목소리가 충분히 담기지 않았어요. 조용한 곳에서 다시 녹음해 주세요.");
        } else setError("녹음을 확인하지 못했어요. 아래 질문을 눌러 각각 다시 녹음해 주세요.");
      } else setError(caught instanceof PallyApiError ? caught.message : "등록하지 못했어요. 다시 시도해 주세요.");
    } finally { changePhase("idle"); }
  };
  const back = () => {
    if (phaseRef.current === "submitting") return;
    generation.current += 1;
    changePhase("idle");
    cancel();
    setError(null);
    if (stage === "record") setStage("intro");
    else onBack();
  };

  return (
    <MobileShell className="flex flex-col px-5 pb-[90px] pt-[60px]" minHeight={874}>
      <button aria-label="이전 단계" className="-ml-2 grid size-11 shrink-0 place-items-center disabled:opacity-50" disabled={phase === "submitting"} onClick={back} type="button">
        <img alt="" className="-rotate-90" width={40} height={40} src={`${ASSETS}back.svg`} />
      </button>
      <header className="mt-8">
        <h1 className="text-title-1 text-[#1a1a1a]">{stage === "intro" ? "Pally가 말투를 닮아가요" : complete ? "녹음을 모두 마쳤어요" : "평소처럼 영어로 답해 주세요"}</h1>
        <p className="ml-[6px] mt-4 max-w-[321px] text-[16px] leading-5 text-text-tertiary">
          {stage === "intro" ? "평소 목소리를 기준으로, 대화할 때 억양이 얼마나 살아 있는지에 따라 Pally 모양이 바뀌어요." : complete ? <>잘했어요! 이제 등록하면 Pally가<br />당신의 말투를 알아가기 시작해요.</> : <>대본 읽듯 말고 평소처럼, 조용한 곳에서<br />{limits.min_seconds}초 이상 이야기해 주세요.</>}
        </p>
      </header>
      {stage === "intro" ? <>
        <img alt="Pally 캐릭터" className="mx-auto mt-[34px]" width={169.4} height={169.4} src={`${ASSETS}pally-intro.svg`} />
        <ul className="mt-[15px] flex flex-col gap-[14px] rounded-2xl border border-[#f1e6da] bg-white p-[18px]">
          {[
            ["영어로 짧게 3번 답해요", `질문마다 ${limits.min_seconds}~${Math.max(limits.min_seconds, Math.min(15, limits.max_seconds))}초, 평소 말하듯 편하게 이야기하면 돼요.`],
            ["억양 측정값만 저장해요", "녹음 원본은 측정이 끝나면 바로 지워요."],
            ["마이크 권한이 필요해요", "다음 화면에서 마이크 사용을 허용해 주세요."],
          ].map(([title, description]) => <li className="flex items-start gap-[10px]" key={title}>
            <img alt="" className="mt-1 shrink-0" width={8} height={8} src={`${ASSETS}bullet.svg`} />
            <div><p className="text-[15px] font-bold leading-[22px]">{title}</p><p className="max-w-[270px] text-[13px] leading-[18px] text-text-tertiary">{description}</p></div>
          </li>)}
        </ul>
      </> : <>
        <ol aria-label="녹음 진행 상태" className="mx-auto mt-[34px] flex h-[30px] w-[220px] items-center">
          {prompts.map((prompt, index) => <li className={cn("flex items-center", index < 2 && "flex-1")} key={prompt}>
            <button aria-label={`${index + 1}번 질문${clips[index] ? " 녹음 완료, 다시 녹음" : ""}`} aria-current={!complete && question === index ? "step" : undefined} className="relative grid size-7 shrink-0 place-items-center text-[13px] font-bold" disabled={busy || (!clips[index] && question !== index)} onClick={() => retry(index)} type="button">
              <img alt="" width={28} height={28} src={`${ASSETS}${clips[index] && question !== index ? "step-complete.svg" : question === index ? "step-active.svg" : "step-pending.svg"}`} />
              <span className={cn("absolute", clips[index] && question !== index ? "text-white" : question === index ? "text-[#ff6b35]" : "text-[#b5aca2]")}>{clips[index] && question !== index ? "✓" : index + 1}</span>
            </button>
            {index < 2 ? <span aria-hidden="true" className={cn("h-[2px] flex-1", clips[index] ? "bg-[#ff6b35]" : "bg-[#e6ddd3]")} /> : null}
          </li>)}
        </ol>
        {complete ? <ol className="mt-6 rounded-2xl border border-[#f1e6da] bg-white">
          {prompts.map((prompt, index) => <li key={prompt}><button aria-label={`${index + 1}번 질문 다시 녹음`} className="flex w-full items-center gap-[10px] px-[18px] py-[14px] text-left text-[14px] disabled:cursor-wait" disabled={busy} onClick={() => retry(index)} type="button"><span aria-hidden="true" className="grid size-5 shrink-0 place-items-center rounded-full bg-[#ff6b35] text-[11px] font-bold text-white">✓</span><span>{index + 1}. {prompt}</span></button></li>)}
        </ol> : <>
          <section aria-labelledby="voice-question" className="mt-6 flex flex-col gap-[6px] rounded-2xl border border-[#f1e6da] bg-white p-5">
            <p className="text-[13px] font-bold leading-[18px] text-[#ff6b35]">질문 {question + 1} / {limits.clips}</p>
            <h2 id="voice-question" className="text-[21px] font-bold leading-[1.4] text-[#1a1a1a]">{prompts[question]}</h2>
            <p className="text-[14px] leading-[1.4] text-text-tertiary">{HELP[prompts[question]] ?? "평소 말하듯 편하게 영어로 답해 주세요."}</p>
          </section>
          <div className="relative flex min-h-[230px] flex-col items-center pt-[45px]">
            {recording ? <p aria-label="녹음 시간" className="absolute top-2 text-[22px] font-bold text-[#ff5a5f]">{Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")}</p> : null}
            {error ? <p className="mb-3 rounded-lg border border-[#ffc9c9] bg-[#fff5f5] px-3 py-2 text-center text-[13px] leading-5 text-[#e5484d]" role="alert">{error}</p> : null}
            <button aria-label={recording ? "녹음 마치기" : `${question + 1}번째 녹음 시작`} className="relative grid size-[140px] shrink-0 place-items-center disabled:opacity-50" disabled={busy && !recording} onClick={record} type="button">
              {recording ? <><img alt="" className="absolute" width={140} height={140} src={`${ASSETS}recording-halo.svg`} /><img alt="" className="absolute" width={104} height={104} src={`${ASSETS}recording-disc.svg`} /><span className="relative size-[30px] rounded-md bg-white" /></> : <img alt="" width={104} height={105.051} src={`${ASSETS}microphone.svg`} />}
            </button>
            <p className="mt-1 text-center text-[14px] text-text-tertiary" role="status">{recording ? `다시 탭하면 녹음이 끝나요 · 최대 ${limits.max_seconds}초` : phase === "starting" ? "마이크를 준비하고 있어요" : phase === "processing" ? "녹음을 확인하고 있어요" : error ? "탭해서 다시 녹음" : "탭해서 녹음 시작"}</p>
            {!busy && clips.every((clip) => clip !== null) ? <button className="min-h-8 text-[12px] text-text-tertiary underline" onClick={() => { setQuestion(3); setError(null); }} type="button">기존 녹음 유지하기</button> : null}
          </div>
        </>}
        {complete && error ? <p className="mt-4 text-center text-[13px] text-[#e5484d]" role="alert">{error}</p> : null}
      </>}
      <footer className="mt-auto pt-8">
        <OnboardingProgress step={stage === "intro" ? 3 : 4} totalSteps={5} />
        <PrimaryButton className="mt-[30px]" disabled={stage === "record" && (!complete || busy)} onClick={() => { if (stage === "intro") setStage("record"); else void save(); }} type="button">
          {stage === "intro" ? "시작하기" : phase === "submitting" ? "목소리 확인 중…" : "목소리 등록하고 시작하기"}
        </PrimaryButton>
      </footer>
    </MobileShell>
  );
}
