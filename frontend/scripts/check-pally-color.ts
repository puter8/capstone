import { equal, ok } from "node:assert/strict";

import { curiosityBodyRgb, curiosityHighlightRgb, curiosityOklch, rgbToHex, type Rgb } from "../lib/pally-color";
import { curiosityToColor } from "../lib/types/character";

// Anchor colours agreed on 2026-11-24 (plan A, brand arc).
equal(rgbToHex(curiosityBodyRgb(0)), "#B0AADB");
equal(rgbToHex(curiosityBodyRgb(50)), "#EE9ABF");
equal(rgbToHex(curiosityBodyRgb(100)), "#F7C56D");
equal(curiosityToColor(50), "#EE9ABF");

// Out-of-range scores clamp to the ends.
equal(rgbToHex(curiosityBodyRgb(-20)), "#B0AADB");
equal(rgbToHex(curiosityBodyRgb(140)), "#F7C56D");

function srgbToOklabLightness([r, g, b]: Rgb): number {
  const lin = (c: number) => {
    const x = c / 255;
    return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  };
  const [lr, lg, lb] = [lin(r), lin(g), lin(b)];
  const l = Math.cbrt(0.4122214708 * lr + 0.536328835 * lg + 0.0514459929 * lb);
  const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
  const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
  return 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
}

for (let v = 0; v <= 100; v++) {
  const body = curiosityBodyRgb(v);
  const highlight = curiosityHighlightRgb(v);
  for (const channel of [...body, ...highlight]) {
    ok(Number.isInteger(channel) && channel >= 0 && channel <= 255, `channel out of range at ${v}`);
  }
  // Even perceived lightness is the point of the palette; the old HSL ramp swung 0.69-0.89.
  const lightness = srgbToOklabLightness(body);
  ok(lightness >= 0.75 && lightness <= 0.86, `lightness ${lightness.toFixed(3)} at ${v}`);
  ok(srgbToOklabLightness(highlight) > lightness, `highlight not lighter at ${v}`);
  // The path must not pass through green (OKLCH hue roughly 110-200).
  const [, , hue] = curiosityOklch(v);
  ok(hue < 110 || hue > 200, `green hue ${hue.toFixed(0)} at ${v}`);
}

console.log("pally-color checks passed");
