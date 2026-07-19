"use client";

import Image from "next/image";
import { useState } from "react";

import { MobileShell } from "@/components/layout/MobileShell";
import { PlanCard } from "@/components/profile/PlanCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { PrimaryButton } from "@/components/ui/PrimaryButton";

type Plan = "monthly" | "yearly";

export default function PlansPage() {
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);

  return (
    <MobileShell>
      <PageHeader
        backHref="/my"
        className="absolute left-0 top-[60px]"
        description={"Pally Pro를 구독하고 Pally와 제한 없이\n대화를 나눠보세요!"}
        title="요금제 및 결제"
        variant="back"
      />

      <h2 className="absolute left-0 right-0 top-[210px] text-center text-title-1 text-accent">Pally Pro</h2>
      <Image
        alt="Pally Pro 캐릭터"
        className="absolute left-[102px] top-[240px] size-[197px]"
        height={197}
        priority
        src="/pally/pally-pro.svg"
        width={197}
      />

      <div aria-label="요금제 선택" className="absolute left-[22px] right-[26px] top-[502px] flex gap-1" role="radiogroup">
        <PlanCard
          caption="1달마다 결제"
          className="flex-1"
          name="Monthly Plan"
          onSelect={() => setSelectedPlan("monthly")}
          plan="monthly"
          price="$ 9.99"
          selected={selectedPlan === "monthly"}
        />
        <PlanCard
          caption="7일간 무료 체험 / 1년마다 결제"
          className="flex-1"
          name="Yearly Plan"
          onSelect={() => setSelectedPlan("yearly")}
          plan="yearly"
          price="$ 99.99"
          selected={selectedPlan === "yearly"}
        />
      </div>

      <PrimaryButton className="absolute bottom-[34px] left-5 w-[calc(100%-40px)]" disabled={selectedPlan === null}>
        확인
      </PrimaryButton>
    </MobileShell>
  );
}
