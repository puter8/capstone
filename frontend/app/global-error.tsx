"use client";

import { useEffect } from "react";

// Replaces the root layout when it fails, so it renders <html> and <body> itself. The browser
// builds this screen on its own (the server sends only an empty shell), and the stylesheet is
// not loaded in that case, so the styles are inline and copy the tokens from tailwind.config.ts.
const colors = { surface: "#fcf9f6", text: "#1c1a17", textTertiary: "#8c857a", primary: "#fe9012" };

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Root layout render failed", error);
  }, [error]);

  return (
    <html lang="ko">
      <body
        style={{
          margin: 0,
          minHeight: "100dvh",
          background: colors.surface,
          color: colors.text,
          fontFamily: "'Noto Sans KR', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
          wordBreak: "keep-all",
          WebkitFontSmoothing: "antialiased",
        }}
      >
        <main
          style={{
            boxSizing: "border-box",
            margin: "0 auto",
            maxWidth: 402,
            minHeight: "100dvh",
            padding: "0 20px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            gap: 32,
            textAlign: "center",
          }}
        >
          <div>
            <h1 style={{ margin: 0, fontSize: 24, lineHeight: "36px", fontWeight: 700 }}>문제가 생겼어요</h1>
            <p style={{ margin: "8px 0 0", fontSize: 16, lineHeight: "24px", color: colors.textTertiary }}>
              화면을 불러오는 중에 오류가 났어요. 다시 시도해 주세요.
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, width: "100%" }}>
            <button
              onClick={reset}
              style={{
                width: "100%",
                height: 56,
                border: 0,
                borderRadius: 12,
                background: colors.primary,
                color: "#ffffff",
                fontFamily: "inherit",
                fontSize: 16,
                lineHeight: "20px",
                fontWeight: 700,
                cursor: "pointer",
              }}
              type="button"
            >
              다시 시도
            </button>
            <a href="/home" style={{ fontSize: 16, lineHeight: "24px", color: colors.textTertiary, textDecoration: "underline" }}>
              홈으로 가기
            </a>
          </div>
        </main>
      </body>
    </html>
  );
}
