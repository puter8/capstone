import { pallyApi } from "@/lib/api";
import type { OpenerResponse } from "@/lib/api/contracts";

// Keep the same key when retrying an opener for this conversation.
export function requestPallyOpener(conversationId: string, idempotencyKey: string): Promise<OpenerResponse> {
  return pallyApi.createOpener(conversationId, idempotencyKey);
}
