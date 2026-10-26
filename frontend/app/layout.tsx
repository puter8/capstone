import type { Metadata, Viewport } from "next";
import { Fraunces } from "next/font/google";
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "./globals.css";
import "@/styles/v2-tokens.css";

// Fraunces is reserved for short English content and numerals.
const fraunces = Fraunces({
  weight: "variable",
  style: ["normal", "italic"],
  subsets: ["latin"],
  axes: ["SOFT", "WONK", "opsz"],
  display: "swap",
  variable: "--font-fraunces",
});

export const metadata: Metadata = {
  title: "Pally",
  description:
    "내 영어 발화 스타일에 반응하는 Pally — 한국인 영어학습자를 위한 음성 회화 동반자",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html className={fraunces.variable} lang="ko">
      <body className="min-h-dvh bg-p-bg text-p-text font-p-ui antialiased">
        {children}
      </body>
    </html>
  );
}
