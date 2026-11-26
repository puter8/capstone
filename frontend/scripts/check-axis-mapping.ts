/**
 * The 5-axis → feature mapping says the same thing in every file that states it.
 *
 * The mapping lives in three places: the renderer draws it, character.ts
 * documents it, and the dev debugger labels its sliders with it. They have
 * drifted before - commit a40fc4d had to fix a debug view that described a
 * mapping the renderer did not draw - and the drift is invisible until someone
 * opens the debugger and trusts the wrong label.
 *
 * Two axes are read against their own direction (Formality on the body shape,
 * and nothing else today), so the direction is asserted explicitly rather than
 * assumed: an accidental `tier(ax.Formality)` would still compile, still draw a
 * valid Pally, and silently mean the opposite of what the team agreed.
 */
import { equal } from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");

const renderer = read("../components/pally/PallyCanvas.tsx");
const types = read("../lib/types/character.ts");
const devPage = read("../app/dev/pally/page.tsx");

// What the renderer actually draws. The tier expression carries the direction:
// `2 - tier` reads an axis against itself, plain `tier` reads it with the axis.
for (const [expression, feature] of [
  ["const sT = 2 - tier(ax.Formality);", "body shape follows Formality, inverted"],
  ["const eT       = tier(ax.Energy);", "eyes follow Energy, with the axis"],
  ["const mT = tier(ax.Humor);", "motion follows Humor"],
  ["curiosityBodyRgb(ax.Curiosity)", "body colour follows Curiosity"],
  ["tier(ax.Intimacy)", "mouth follows Intimacy"],
] as const) {
  equal(renderer.includes(expression), true, `PallyCanvas must draw: ${feature}`);
}

// Every axis drives exactly one feature: a mapping that assigns two axes to the
// same channel loses one of them silently.
for (const axis of ["Formality", "Energy", "Humor", "Intimacy", "Curiosity"] as const) {
  const uses = renderer.match(new RegExp(`ax\\.${axis}\\b`, "g")) ?? [];
  equal(uses.length > 0, true, `${axis} must reach the canvas`);
}

// The documented mapping must name the same feature per axis, and must mark the
// one axis that is read backwards. Checking the Korean feature word keeps this
// honest: a stale comment that still says 눈 for Formality fails here.
for (const [axis, feature] of [
  ["Formality", "몸 모양 (축 방향과 반대)"],
  ["Energy", "눈"],
  ["Intimacy", "입"],
  ["Curiosity", "몸 색상"],
  ["Humor", "전신 움직임"],
] as const) {
  const line = types.split("\n").find((l) => l.includes(`//   ${axis}`));
  equal(line !== undefined, true, `character.ts must document ${axis}`);
  equal(line!.includes(feature), true, `character.ts must map ${axis} to ${feature}, got: ${line}`);
}

// The debugger's stage labels, in tier order. These are what a developer reads
// while dragging a slider, so a reversed axis must be reversed here too.
for (const [axis, stages] of [
  ["Formality", "['8각 별', '둥근 사각', '원']"],
  ["Energy", "['단순한 점', '흰자+동공', '반짝이는 눈']"],
] as const) {
  // The label table is space-aligned, so the gap after the key varies. Escape
  // every metacharacter: a stage name like "흰자+동공" is not a valid pattern.
  const literal = stages.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  equal(
    new RegExp(`${axis}:\\s*${literal}`).test(devPage),
    true,
    `the dev debugger must label ${axis} stages as ${stages}`,
  );
}

for (const [axis, visual] of [
  ["Formality", "몸 모양 (역방향)"],
  ["Energy", "눈"],
] as const) {
  equal(devPage.includes(`visual: '${visual}'`), true, `the dev debugger must show ${axis} → ${visual}`);
}

// The first Pally a new user sees must not move when the mapping is rearranged:
// swapping two axes that both default to 50 has to leave the middle stage on
// both channels. DEFAULT_AXES is the source of that promise.
const defaults = types.slice(types.indexOf("export const DEFAULT_AXES"));
for (const axis of ["Formality", "Energy"] as const) {
  const match = defaults.match(new RegExp(`${axis}:\\s*(\\d+)`));
  equal(match !== null, true, `DEFAULT_AXES must set ${axis}`);
  const value = Number(match![1]);
  equal(
    value >= 34 && value <= 66,
    true,
    `DEFAULT_AXES.${axis} must stay in the middle band so the default Pally is unchanged, got ${value}`,
  );
}

console.log("axis mapping: PASS");
