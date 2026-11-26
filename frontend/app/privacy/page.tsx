"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { TopBar } from "@/components/v2/TopBar";
import { routes } from "@/lib/v2/routes";

import { POLICY_EFFECTIVE_DATE, POLICY_SECTIONS } from "./policy-content";

export default function PrivacyPolicyPage() {
  const router = useRouter();

  // Opened from the login screen or My page: go back there. Opened directly
  // (no history in this tab): fall back to the login screen.
  const goBack = () => {
    if (window.history.length > 1) router.back();
    else router.replace(routes.login);
  };

  return (
    <AppFrame>
      <TopBar onBack={goBack} title="개인정보처리방침" variant="back" />
      <article className="flex flex-col gap-p-6 px-p-5 pb-p-8 pt-p-2">
        <p className="text-p-small text-p-text-secondary">
          Puter는 「개인정보 보호법」에 따라 이용자의 개인정보를 보호하고, 관련 고충을 신속하게
          처리하기 위해 다음과 같이 개인정보처리방침을 둡니다. Pally는 대학 캡스톤 디자인 과제로 운영되는 영어 회화 서비스예요.
        </p>
        {POLICY_SECTIONS.map((section) => (
          <PolicySection key={section.title} title={section.title}>
            {section.body}
          </PolicySection>
        ))}
        <p className="text-p-caption text-p-text-muted">시행일: {POLICY_EFFECTIVE_DATE}</p>
      </article>
    </AppFrame>
  );
}

function PolicySection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-p-2">
      <h2 className="text-p-label text-p-text">{title}</h2>
      <div className="flex flex-col gap-p-2 text-p-small text-p-text-secondary">{children}</div>
    </section>
  );
}
