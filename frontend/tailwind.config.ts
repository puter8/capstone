import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
      fontFamily: {
        sans: [
          "Pretendard Variable",
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "Roboto",
          "Helvetica Neue",
          "Segoe UI",
          "Apple SD Gothic Neo",
          "Noto Sans KR",
          "Malgun Gothic",
          "sans-serif",
        ],
      },
      // Typography tokens — source: Figma Design System page (node 184:148).
      // Each entry bakes in font-size, line-height, and font-weight.
      // See DESIGN.md for the canonical token table.
      fontSize: {
        "title-1": ["24px", { lineHeight: "36px", fontWeight: "600" }],
        "title-2": ["20px", { lineHeight: "28px", fontWeight: "600" }],
        "subtitle-sb": ["18px", { lineHeight: "24px", fontWeight: "600" }],
        subtitle: ["18px", { lineHeight: "24px", fontWeight: "400" }],
        "body-sb": ["16px", { lineHeight: "24px", fontWeight: "600" }],
        body: ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "body-2-sb": ["14px", { lineHeight: "24px", fontWeight: "600" }],
        "body-2": ["14px", { lineHeight: "24px", fontWeight: "400" }],
        "button-1": ["18px", { lineHeight: "24px", fontWeight: "600" }],
        "button-2-sb": ["16px", { lineHeight: "20px", fontWeight: "600" }],
        "button-2": ["16px", { lineHeight: "20px", fontWeight: "400" }],
        "button-3": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        "button-4": ["12px", { lineHeight: "16px", fontWeight: "400" }],
        "caption-1": ["12px", { lineHeight: "16px", fontWeight: "400" }],
        "caption-2": ["11px", { lineHeight: "12px", fontWeight: "400" }],
      },
    },
  },
  plugins: [],
};
export default config;
