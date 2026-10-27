"use client";

import Image from "next/image";
import { useState } from "react";

import { AppFrame } from "@/components/v2/AppFrame";
import { Stage } from "@/components/v2/Stage";
import { Toast } from "@/components/v2/Toast";
import { supabase } from "@/lib/supabase/client";
import { routes } from "@/lib/v2/routes";
import { cn } from "@/lib/utils";

type Provider = "google" | "kakao";

const WORDMARK_STYLE = { fontVariationSettings: '"SOFT" 0, "WONK" 1' } as const;

export default function LoginV2Page() {
  const [isLoading, setIsLoading] = useState<Provider | null>(null);
  const [error, setError] = useState<string | null>(null);

  const signIn = async (provider: Provider) => {
    setIsLoading(provider);
    setError(null);
    const redirectTo = `${window.location.origin}${routes.authCallback}`;
    const { error: signInError } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo,
        // Override Kakao's default email scope; this app only has profile permissions.
        ...(provider === "kakao" ? { queryParams: { scope: "profile_nickname profile_image" } } : {}),
      },
    });
    if (signInError) {
      setError(signInError.message);
      setIsLoading(null);
    }
  };

  const buttonClass = "flex h-[52px] w-full items-center justify-center gap-p-2 rounded-p-input text-p-button transition-transform duration-p-fast ease-p-out active:scale-[0.98] disabled:opacity-60 disabled:active:scale-100 motion-reduce:transition-none";

  return (
    <AppFrame>
      <div className="flex flex-1 flex-col items-center justify-center gap-p-3 px-p-6 text-center">
        <span className="font-p-brand text-p-title-en text-p-text" lang="en" style={WORDMARK_STYLE}>
          Pally
        </span>
        <Stage glow={false} size="large" />
        <h1 className="text-p-heading tracking-[-0.02em] text-p-text">
          나를 가장 잘 아는
          <br />
          영어 친구, Pally
        </h1>
      </div>
      <div aria-busy={isLoading !== null} className="flex flex-col gap-p-3 px-p-5 pb-[calc(var(--p-space-8)+env(safe-area-inset-bottom))] pt-p-2">
        <button
          className={cn(buttonClass, "border border-p-border-control bg-p-surface text-p-text")}
          disabled={isLoading !== null}
          onClick={() => { void signIn("google"); }}
          type="button"
        >
          <Image alt="" height={20} src="/v2/google-g.svg" width={20} />
          {isLoading === "google" ? "Google로 연결하고 있어요" : "Google로 시작하기"}
        </button>
        <button
          className={cn(buttonClass, "bg-[#fee500] text-[rgba(0,0,0,0.85)]")}
          disabled={isLoading !== null}
          onClick={() => { void signIn("kakao"); }}
          type="button"
        >
          <Image alt="" height={20} src="/v2/kakao-symbol.svg" width={20} />
          {isLoading === "kakao" ? "카카오로 연결하고 있어요" : "카카오로 시작하기"}
        </button>
      </div>
      {error ? <Toast className="top-p-4" message={error} onDismiss={() => setError(null)} tone="error" /> : null}
    </AppFrame>
  );
}
