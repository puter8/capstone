// Browser hardening for every page. HSTS is added by Vercel on its domains.
// ponytail: no Content-Security-Policy yet; Next's inline bootstrap scripts need a
// nonce setup, add one when the app moves past the 14.x line.
const SECURITY_HEADERS = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // The app records speech, so the microphone stays available to this origin only.
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep `next build` from replacing the CSS and manifests used by a running dev server.
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
