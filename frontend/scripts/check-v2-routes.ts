/**
 * check:v2-routes
 *
 * Every link and redirect in the v2 screens must go through lib/v2/routes.ts so
 * that moving v2 onto the root routes later is a one-constant change. This
 * check fails on hard-coded app paths inside app/v2 and components/v2.
 *
 * A line may opt out with a trailing `// v2-routes-allow` comment when the
 * path is intentionally the v1 one (the KakaoPay return URL the backend
 * validates).
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const frontendRoot = path.resolve(__dirname, "..");
const ROOTS = ["app/v2", "components/v2"].map((dir) => path.join(frontendRoot, dir));
const PATH_LITERAL = /["'`](\/(?:home|history|ranking|my|onboarding|settings|auth)(?:[/?][^"'`]*)?)["'`]/g;

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) return walk(full);
    return /\.(ts|tsx)$/.test(entry) ? [full] : [];
  });
}

const offenders: string[] = [];
let scanned = 0;
for (const root of ROOTS) {
  for (const file of walk(root)) {
    scanned += 1;
    const lines = readFileSync(file, "utf8").split("\n");
    lines.forEach((line, index) => {
      if (line.includes("v2-routes-allow")) return;
      for (const match of Array.from(line.matchAll(PATH_LITERAL))) {
        offenders.push(`${path.relative(frontendRoot, file)}:${index + 1} uses literal path ${match[1]}`);
      }
    });
  }
}

assert.ok(scanned > 10, `expected to scan the v2 screens, scanned ${scanned} files`);
assert.deepEqual(offenders, [], `v2 code must route through lib/v2/routes.ts:\n${offenders.join("\n")}`);
console.log(`v2 route checks passed: ${scanned} files use lib/v2/routes.ts for app paths.`);
