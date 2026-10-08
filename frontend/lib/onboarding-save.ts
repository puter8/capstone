import { PallyApiError } from "@/lib/api/contracts";
import type { OnboardingInput, PallyApi, ProfileResponse } from "@/lib/api/contracts";

/**
 * Saves the onboarding choices. The server accepts onboarding once; when the profile
 * is already onboarded (the user went back from the last step, used the browser's back
 * button, or retried after a lost response) the same values are applied as an edit.
 */
export async function saveOnboardingProfile(
  api: Pick<PallyApi, "onboard" | "updateProfile">,
  input: OnboardingInput,
): Promise<ProfileResponse> {
  try {
    return await api.onboard(input);
  } catch (error) {
    if (error instanceof PallyApiError && error.code === "conflict") return api.updateProfile(input);
    throw error;
  }
}
