import { strict as assert } from "node:assert";
import { conversationCompleteResponseSchema, energyBaselineResponseSchema } from "../lib/api/schemas";

assert(energyBaselineResponseSchema.safeParse({ status: "required", baseline: null }).success);
assert(energyBaselineResponseSchema.safeParse({ status: "disabled", baseline: null }).success);
assert(!energyBaselineResponseSchema.safeParse({ status: "ready", baseline: null }).success);
const ready = { status: "ready", baseline: { range_st: 0, valid_clips: 3, method_version: "v1" } };
assert(energyBaselineResponseSchema.safeParse(ready).success, "Flat baseline is valid");
for (const range_st of [-1, NaN, Infinity]) {
  assert(!energyBaselineResponseSchema.safeParse({ ...ready, baseline: { ...ready.baseline, range_st } }).success);
}
assert(!energyBaselineResponseSchema.safeParse({ ...ready, baseline: { ...ready.baseline, valid_clips: 2 } }).success);
const completion = conversationCompleteResponseSchema.parse({
  conversation: { id: "d2193690-ec8b-43ae-9385-4f6b1e52bb8f", status: "completed" },
  current_axes: { Formality: 50, Energy: 65, Intimacy: 25, Humor: 10, Curiosity: 70 },
  energy: { status: "retained", score: null, reason: "insufficient_audio" },
  warnings: [{ code: "energy_unavailable", message: "이전 값을 유지했어요." }],
});
assert.equal(completion.current_axes?.Energy, 65);
assert.equal(completion.warnings[0].code, "energy_unavailable");
console.log("Energy API boundary checks passed.");
