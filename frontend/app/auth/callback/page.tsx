"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { Button } from "@/components/v2/Button";
import { IconSpinner } from "@/components/v2/icons";
import { Stage } from "@/components/v2/Stage";
import { pallyApi, PallyApiError } from "@/lib/api";
import { signInErrorMessage } from "@/lib/api/error-messages";
import { supabase } from "@/lib/supabase/client";
import { routes } from "@/lib/v2/routes";

export default function AuthCallbackV2Page() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const finishSignIn = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      const current = await supabase.auth.getSession();
      if (current.error) throw current.error;
      if (!current.data.session && code) {
        const exchanged = await supabase.auth.exchangeCodeForSession(code);
        if (exchanged.error) throw exchanged.error;
      }

      try {
        const { profile } = await pallyApi.getProfile();
        router.replace(profile.onboarding_completed ? routes.home : routes.onboarding);
      } catch (caught) {
        if (caught instanceof PallyApiError && caught.code === "profile_not_found") {
          router.replace(routes.onboarding);
          return;
        }
        throw caught;
      }
    };

    void finishSignIn()
      .catch((caught: unknown) => {
        console.error("Sign-in callback failed", caught);
        if (active) setError(signInErrorMessage(caught));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, [router]);

  return (
    <AppFrame className="items-center justify-center gap-p-4 px-p-5 text-center">
      <Stage glow={false} size="compact" />
      {isLoading ? (
        <p className="flex items-center gap-p-2 text-p-label text-p-text-secondary" role="status">
          <IconSpinner className="animate-spin motion-reduce:animate-none" size={20} />
          로그인 정보를 확인하고 있어요
        </p>
      ) : null}
      {error ? (
        <>
          <div className="flex flex-col gap-p-2" role="alert">
            <h1 className="text-p-section text-p-text">로그인을 확인하지 못했어요</h1>
            <p className="text-p-body text-p-text-secondary">{error}</p>
          </div>
          <Button onClick={() => router.replace(routes.login)}>로그인으로 돌아가기</Button>
        </>
      ) : null}
    </AppFrame>
  );
}
