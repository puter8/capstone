import { mockPallyApi } from "@/lib/api/mock-client";
import type { PallyApi } from "@/lib/api/contracts";

// Single frontend swap point. Replace this instance with the HTTP client when
// the revised backend contract is implemented.
export const pallyApi: PallyApi = mockPallyApi;

export { PallyApiError } from "@/lib/api/contracts";
export type * from "@/lib/api/contracts";
