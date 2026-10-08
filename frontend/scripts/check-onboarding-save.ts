import { deepEqual, equal, rejects } from "node:assert/strict";

import { PallyApiError } from "../lib/api/contracts";
import type { OnboardingInput, PallyApi } from "../lib/api/contracts";
import { mockPallyApi, resetMockPallyApi } from "../lib/api/mock-client";
import { saveOnboardingProfile } from "../lib/onboarding-save";

async function main() {
  // Step 2 -> confirm -> step 3 -> back -> step 2 -> confirm: onboarding runs twice.
  resetMockPallyApi();
  await saveOnboardingProfile(mockPallyApi, { display_name: "Claire", english_level: "B1" });
  const second = await saveOnboardingProfile(mockPallyApi, { display_name: "Claire Lee", english_level: "B2" });
  equal(second.profile.display_name, "Claire Lee");
  equal(second.profile.english_level, "B2");
  const saved = (await mockPallyApi.getProfile()).profile;
  deepEqual([saved.display_name, saved.english_level, saved.onboarding_completed], ["Claire Lee", "B2", true]);

  // Only "already onboarded" falls back to an edit; every other failure reaches the screen.
  const input: OnboardingInput = { display_name: "Claire", english_level: "A2" };
  for (const failure of [
    new PallyApiError(422, "validation_error", "입력한 내용을 확인해 주세요."),
    new PallyApiError(0, "network_error", "인터넷 연결을 확인하고 다시 시도해 주세요."),
    new PallyApiError(503, "persistence_failed", "데이터를 처리하지 못했어요."),
  ]) {
    let edits = 0;
    const api: Pick<PallyApi, "onboard" | "updateProfile"> = {
      onboard: async () => { throw failure; },
      updateProfile: async () => { edits += 1; throw new Error("updateProfile must not run"); },
    };
    await rejects(() => saveOnboardingProfile(api, input), (error: unknown) => error === failure);
    equal(edits, 0, `${failure.code} must not trigger an edit`);
  }

  // If the edit itself fails, that failure is what the user sees.
  const editFailure = new PallyApiError(503, "persistence_failed", "데이터를 처리하지 못했어요.");
  await rejects(
    () => saveOnboardingProfile({
      onboard: async () => { throw new PallyApiError(409, "conflict", "Onboarding already completed."); },
      updateProfile: async () => { throw editFailure; },
    }, input),
    (error: unknown) => error === editFailure,
  );

  resetMockPallyApi();
  console.log("Onboarding save checks passed: a second save becomes an edit; other failures are not hidden.");
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
