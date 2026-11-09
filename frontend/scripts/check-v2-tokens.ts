/**
 * check:v2-tokens
 *
 * frontend/styles/v2-tokens.css copies docs/design/pally.tokens.css at :root.
 * This check fails when the two drift apart, except for the one documented
 * difference (--p-font-brand points at the next/font variable), and when
 * tailwind.config.ts references a --p-* variable that does not exist.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");

const sourceCss = readFileSync(path.join(repoRoot, "docs/design/pally.tokens.css"), "utf8");
const scopedCss = readFileSync(path.join(frontendRoot, "styles/v2-tokens.css"), "utf8");
const tailwindConfig = readFileSync(path.join(frontendRoot, "tailwind.config.ts"), "utf8");

const ALLOWED_DIFFERENCES = new Set(["--p-font-brand"]);

function readDeclarations(css: string): Map<string, string> {
  const declarations = new Map<string, string>();
  const pattern = /(--p-[a-z0-9-]+)\s*:\s*([^;]+);/g;
  for (const match of Array.from(css.matchAll(pattern))) {
    const [, name, value] = match;
    const existing = declarations.get(name);
    // Media-query overrides (page gutter, motion) repeat a name; the first value is the base one.
    if (existing === undefined) declarations.set(name, value.trim());
  }
  return declarations;
}

const source = readDeclarations(sourceCss);
const scoped = readDeclarations(scopedCss);

assert.ok(source.size > 50, `expected the design tokens source to define many --p-* tokens, found ${source.size}`);
assert.match(scopedCss, /:root\s*\{/, "design tokens must be available at :root");
assert.ok(!scopedCss.includes('[data-design="v2"]'), "root tokens must not depend on the removed v2 wrapper");

for (const [name, value] of Array.from(source)) {
  assert.ok(scoped.has(name), `missing in frontend copy: ${name}`);
  if (ALLOWED_DIFFERENCES.has(name)) continue;
  assert.equal(scoped.get(name), value, `value drift for ${name}`);
}
for (const name of Array.from(scoped.keys())) {
  assert.ok(source.has(name), `frontend copy defines a token the docs source does not: ${name}`);
}
assert.ok(
  scoped.get("--p-font-brand")?.startsWith("var(--font-fraunces)"),
  "--p-font-brand must start with var(--font-fraunces) so next/font's hashed family is used",
);

const referenced = new Set<string>();
for (const match of Array.from(tailwindConfig.matchAll(/var\((--p-[a-z0-9-]+)\)/g))) referenced.add(match[1]);
assert.ok(referenced.size > 30, `tailwind.config.ts should map the v2 tokens, found ${referenced.size} references`);
for (const name of Array.from(referenced)) {
  assert.ok(scoped.has(name), `tailwind.config.ts references an undefined token: ${name}`);
}

const sourceMediaBlocks = Array.from(sourceCss.matchAll(/@media[^{]+\{/g), (match) => match[0].trim());
const scopedMediaBlocks = Array.from(scopedCss.matchAll(/@media[^{]+\{/g), (match) => match[0].trim());
assert.deepEqual(scopedMediaBlocks, sourceMediaBlocks, "media queries must match the docs source");

console.log(`v2 token checks passed: ${source.size} tokens in sync, ${referenced.size} Tailwind references resolved.`);
