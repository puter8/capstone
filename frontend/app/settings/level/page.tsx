"use client";

import { useState } from "react";

import { MobileShell } from "@/components/layout/MobileShell";
import { LevelOption } from "@/components/onboarding/LevelOption";
import { PageHeader } from "@/components/ui/PageHeader";
import { PrimaryButton } from "@/components/ui/PrimaryButton";

const LEVELS = [
  { code: "A2", name: "Elementary", description: "간단한 용어를 사용해 다양한 것들을 묘사하고 간단한 표현을 이해할 수 있어요" },
  { code: "B1", name: "Intermediate", description: "여행할 때 외국어를 구사할 수 있어요. 취미와 일, 가족에 관해 대화를 나눌 수 있어요." },
  { code: "B2", name: "Upper Intermediate", description: "복잡한 주제의 대화를 이해할 수 있고 막힘 없이 원어민과 대화를 나눌 수 있어요" },
  { code: "C1", name: "Advanced", description: "사교, 학술 또는 전문적인 상황에서 외국어 능력을 구사할 수 있으며, 복잡한 대화를 따라갈 수 있어요" },
] as const;

export default function LevelSettingsPage() {
  const [level, setLevel] = useState("B1");

  return (
    <MobileShell>
      <PageHeader backHref="/my" className="absolute left-0 top-[60px]" description="Pally와 대화할 영어 난이도를 선택해 주세요." title="영어 레벨 변경" variant="back" />
      <div className="absolute left-5 right-5 top-[220px] flex flex-col gap-3">
        {LEVELS.map((item) => (
          <LevelOption code={item.code} description={item.description} key={item.code} name={item.name} onSelect={() => setLevel(item.code)} selected={level === item.code} />
        ))}
      </div>
      <PrimaryButton className="absolute bottom-[34px] left-5 w-[calc(100%-40px)]">확인</PrimaryButton>
    </MobileShell>
  );
}
