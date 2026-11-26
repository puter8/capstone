// Curiosity -> Pally body colour, "brand arc" (2026-11-24).
// Lavender (0) -> rose (50) -> apricot (100), interpolated in OKLCH so perceived
// lightness stays within 0.76-0.85 on the dark v2 ground and the path never passes
// through green. Chroma rises with Curiosity: a low score reads calm, a high one lively.
// It starts near the brand primary (#B7B5F2) and ends near the secondary (#F2DFA0).

export type Rgb = [number, number, number];

// [curiosity, L, C, hue]. Hue is unwrapped (440 = 80deg) so interpolation runs
// 290 -> 352 -> 440 through pink instead of back through green.
const ANCHORS: ReadonlyArray<readonly [number, number, number, number]> = [
  [0, 0.76, 0.07, 290],
  [50, 0.78, 0.11, 352],
  [100, 0.85, 0.12, 440],
];

// Highlight at the centre of the radial gradient: lighter and softer, same hue.
const HIGHLIGHT_LIGHTNESS_LIFT = 0.09;
const HIGHLIGHT_CHROMA_SCALE = 0.65;
const HIGHLIGHT_MAX_LIGHTNESS = 0.97;
const GAMUT_CHROMA_STEP = 0.002;
const GAMUT_EPSILON = 1e-4;

export function curiosityOklch(curiosity: number): [number, number, number] {
  const v = Math.max(0, Math.min(100, curiosity));
  const i = v <= ANCHORS[1][0] ? 0 : 1;
  const [t0, l0, c0, h0] = ANCHORS[i];
  const [t1, l1, c1, h1] = ANCHORS[i + 1];
  const u = (v - t0) / (t1 - t0);
  const hue = (((h0 + (h1 - h0) * u) % 360) + 360) % 360;
  return [l0 + (l1 - l0) * u, c0 + (c1 - c0) * u, hue];
}

function encodeSrgb(c: number): number {
  return c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055;
}

function oklchToSrgbUnclamped(l: number, c: number, h: number): Rgb {
  const hr = (h * Math.PI) / 180;
  const a = c * Math.cos(hr);
  const b = c * Math.sin(hr);
  const lc = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const mc = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const sc = (l - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    encodeSrgb(4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc),
    encodeSrgb(-1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc),
    encodeSrgb(-0.0041960863 * lc - 0.7034186147 * mc + 1.707614701 * sc),
  ];
}

function inGamut(rgb: Rgb): boolean {
  return rgb.every((x) => x >= -GAMUT_EPSILON && x <= 1 + GAMUT_EPSILON);
}

/** OKLCH -> sRGB 0-255. Out-of-gamut colours keep L and hue and lose chroma. */
export function oklchToRgb(l: number, c: number, h: number): Rgb {
  let chroma = c;
  let rgb = oklchToSrgbUnclamped(l, chroma, h);
  while (!inGamut(rgb) && chroma > 0) {
    chroma = Math.max(0, chroma - GAMUT_CHROMA_STEP);
    rgb = oklchToSrgbUnclamped(l, chroma, h);
  }
  return rgb.map((x) => Math.round(Math.max(0, Math.min(1, x)) * 255)) as Rgb;
}

export function curiosityBodyRgb(curiosity: number): Rgb {
  return oklchToRgb(...curiosityOklch(curiosity));
}

export function curiosityHighlightRgb(curiosity: number): Rgb {
  const [l, c, h] = curiosityOklch(curiosity);
  return oklchToRgb(
    Math.min(l + HIGHLIGHT_LIGHTNESS_LIFT, HIGHLIGHT_MAX_LIGHTNESS),
    c * HIGHLIGHT_CHROMA_SCALE,
    h,
  );
}

export function rgbToHex([r, g, b]: Rgb): string {
  return `#${[r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('').toUpperCase()}`;
}
