import type { Metadata, Viewport } from "next";
import "pretendard/dist/web/variable/pretendardvariable.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pally",
  description:
    "내 영어 발화 스타일에 반응하는 Pally — 한국인 영어학습자를 위한 음성 회화 동반자",
};

// Mobile viewport lock — Figma 402px target (per 01A-CONTEXT.md + commit a2c2bb4).
// maximumScale=1 prevents iOS Safari from auto-zooming when MediaRecorder
// permission prompts or input focus events fire.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="bg-surface text-text font-sans antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
