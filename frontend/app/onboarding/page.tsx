"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MobileShell } from "@/components/layout/MobileShell";
import { EnergyBaselineRegistration } from "@/components/audio/EnergyBaselineRegistration";
import { LevelOption } from "@/components/onboarding/LevelOption";
import { OnboardingProgress } from "@/components/onboarding/OnboardingProgress";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/PageLoader";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { TextInput } from "@/components/ui/TextInput";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { EnergyBaselineResponse } from "@/lib/api";
import { DISPLAY_NAME_MAX_LENGTH } from "@/lib/display-name";
import { saveOnboardingProfile } from "@/lib/onboarding-save";
import type { Level } from "@/lib/types/session";
import { cn } from "@/lib/utils";

const LEVELS = [
  { code: "A2", name: "Elementary", description: "간단한 용어를 사용해 다양한 것들을 묘사하고 간단한 표현을 이해할 수 있어요" },
  { code: "B1", name: "Intermediate", description: "여행할 때 외국어를 구사할 수 있어요. 취미와 일, 가족에 관해 대화를 나눌 수 있어요." },
  { code: "B2", name: "Upper Intermediate", description: "복잡한 주제의 대화를 이해할 수 있고 막힘 없이 원어민과 대화를 나눌 수 있어요" },
  { code: "C1", name: "Advanced", description: "사교, 학술 또는 전문적인 상황에서 외국어 능력을 구사할 수 있으며, 복잡한 대화를 따라갈 수 있어요" },
] as const;

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3 | 5>(1);
  const [baseline, setBaseline] = useState<EnergyBaselineResponse | null>(null);
  const [isLoadingVoice, setIsLoadingVoice] = useState(false);
  const [voiceEntryFailed, setVoiceEntryFailed] = useState(false);
  const [level, setLevel] = useState<Level | null>(null);
  const [name, setName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
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
          setStep(result.status === "required" ? 3 : 5);
        }
      })
      .catch((caught: unknown) => {
        console.error("Voice registration status fetch failed", caught);
        if (!active) return;
        if (caught instanceof PallyApiError && caught.code === "unauthorized") router.replace("/");
        else if (caught instanceof PallyApiError && caught.code === "profile_not_found") setStep(1);
        else {
          setError(caught instanceof Error ? caught.message : "목소리 등록 상태를 불러오지 못했어요.");
          if (voiceOnly) setVoiceEntryFailed(true);
        }
      })
      .finally(() => { if (active) setIsLoadingVoice(false); });
    void pallyApi.getProfileAvatar()
      .then(({ avatar_url: nextAvatarUrl }) => {
        if (active) setAvatarUrl(nextAvatarUrl);
      })
      .catch((caught: unknown) => {
        console.error("Profile avatar fetch failed", caught);
        if (caught instanceof PallyApiError && caught.code === "unauthorized") {
          router.replace("/");
          return;
        }
        if (active) setError(caught instanceof Error ? caught.message : "프로필 사진을 불러오지 못했어요.");
      });
    return () => {
      active = false;
    };
  }, [router]);

  const goBack = () => setStep((value) => (value > 2 ? 2 : 1));
  const goNext = async () => {
    if (step === 5) {
      router.push("/home");
      return;
    }
    if (step === 1) {
      if (level === null) return;
      setStep(2);
      return;
    }

    if (level === null) {
      setError("영어 레벨을 선택해 주세요.");
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      await saveOnboardingProfile(pallyApi, { display_name: name, english_level: level });
      const result = await pallyApi.getEnergyBaseline();
      setBaseline(result);
      setStep(result.status === "required" ? 3 : 5);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "설정을 저장하지 못했어요.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoadingVoice) return <MobileShell><PageLoader message="목소리 등록 상태를 확인하고 있어요" /></MobileShell>;
  if (voiceEntryFailed) return (
    <MobileShell className="flex flex-col items-center justify-center gap-5 px-5">
      <p className="text-center text-body text-error" role="alert">{error}</p>
      <PrimaryButton onClick={() => window.location.reload()}>다시 불러오기</PrimaryButton>
    </MobileShell>
  );

  if (step === 3 && baseline?.status === "required") {
    return <EnergyBaselineRegistration configuration={baseline} onBack={goBack} onReady={() => setStep(5)} />;
  }

  if (step === 5) {
    return (
      <MobileShell className="flex flex-col px-5 pb-[90px] pt-[60px]">
        <button aria-label="이전 단계" className="-ml-2 grid size-11 place-items-center" onClick={goBack} type="button"><img alt="" className="-rotate-90" width={40} height={40} src="/onboarding/voice/back.svg" /></button>
        <h1 className="mt-8 text-title-1">다 됐어요!</h1>
        <p className="ml-[6px] mt-4 text-[16px] leading-5 text-text-tertiary">Pally와 함께 즐거운 공부 시간 되세요!<br />이름과 영어 레벨은 설정에서 언제든 변경할 수 있어요.</p>
        <img alt="Pally 캐릭터" className="mx-auto mt-[93px]" width={308} height={308} src="/onboarding/voice/pally-complete.svg" />
        <footer className="mt-auto pt-[37px]">
          <OnboardingProgress step={baseline?.status === "disabled" ? 3 : 5} totalSteps={baseline?.status === "disabled" ? 3 : 5} />
          <PrimaryButton className="mt-[54px]" onClick={() => router.push("/home")}>확인</PrimaryButton>
        </footer>
      </MobileShell>
    );
  }

  return (
    <MobileShell minHeight={820}>
      {isSaving ? <PageLoader message="설정을 저장하고 있어요" /> : null}
      {step === 1 ? (
        <>
          <PageHeader
            className="absolute left-0 top-[60px]"
            description={"Pally와 대화 하는 용어와 문장 길이를 결정할 수\n있도록 정보를 알려주세요"}
            title="영어 레벨은?"
            variant="intro"
          />
          <div className="absolute left-5 right-5 top-[220px] flex flex-col gap-3">
            {LEVELS.map((item) => {
              const selected = level === item.code;
              return (
                <LevelOption
                  code={item.code}
                  description={item.description}
                  key={item.code}
                  name={item.name}
                  onSelect={() => setLevel(item.code)}
                  selected={selected}
                />
              );
            })}
          </div>
        </>
      ) : null}

      {step === 2 ? (
        <>
          <button aria-label="이전 단계" className="absolute left-5 top-[77px] z-10 grid size-9 place-items-center" onClick={goBack} type="button">
            <img alt="" className="absolute left-px top-[10px] size-4" src="/icons/back.svg" />
          </button>
          <PageHeader
            className="absolute left-0 top-[60px]"
            description={"Pally와 대화 하는 용어와 문장 길이를 결정할 수\n있도록 정보를 알려주세요"}
            showBackLink={false}
            title="이름 정하기"
            variant="back"
          />
          <div className="absolute left-1/2 top-[220px] size-[150px] -translate-x-1/2 overflow-hidden rounded-full bg-[#dedede]">
            <img
              alt="프로필 사진"
              className={cn("size-full object-cover", !avatarUrl && "scale-125")}
              onError={() => {
                if (avatarUrl === null) return;
                console.error("Profile avatar image failed to load");
                setAvatarUrl(null);
              }}
              referrerPolicy="no-referrer"
              src={avatarUrl ?? "/pally/pally-character.svg"}
            />
          </div>
          <TextInput
            aria-label="이름"
            className="absolute left-5 top-[460px] w-[calc(100%-40px)]"
            maxLength={DISPLAY_NAME_MAX_LENGTH}
            onChange={(event) => setName(event.target.value)}
            placeholder="이름을 입력해 주세요"
            value={name}
          />
        </>
      ) : null}

      <div className={cn("absolute left-0 right-0", step === 1 ? "bottom-[174px]" : "bottom-[147px]")}>
        <OnboardingProgress step={step} totalSteps={baseline?.status === "disabled" ? 3 : 5} />
      </div>
      {error ? <p className="absolute bottom-[102px] left-5 right-5 text-center text-body-2 text-red-600" role="alert">{error}</p> : null}
      <PrimaryButton className="absolute bottom-[34px] left-5 w-[calc(100%-40px)]" disabled={isSaving || (step === 1 && level === null) || (step === 2 && !name.trim())} onClick={goNext}>
        {isSaving ? "저장 중..." : "확인"}
      </PrimaryButton>
    </MobileShell>
  );
}
