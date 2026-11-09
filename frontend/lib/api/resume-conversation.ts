import { pallyApi, PallyApiError } from "@/lib/api";
import { invalidateCurrentUserConversationData } from "@/lib/api/route-data";

export const CONVERSATION_STORAGE_KEY = "pally:conversationId";

/**
 * Reopens a finished conversation and hands it to the home screen.
 *
 * Shared by the v1 note card and the v2 session card; the caller decides
 * which home route receives the `conversation_id` query.
 */
export async function resumeConversation(conversationId: string, homePath: string): Promise<string> {
  try {
    await pallyApi.reopenConversation(conversationId);
  } catch (caught) {
    if (!(caught instanceof PallyApiError && caught.code === "conversation_already_active")) throw caught;
  }
  await invalidateCurrentUserConversationData(conversationId).catch((caught: unknown) => {
    console.error("Conversation cache invalidation failed", caught);
  });
  window.localStorage.setItem(CONVERSATION_STORAGE_KEY, conversationId);
  const separator = homePath.includes("?") ? "&" : "?";
  return `${homePath}${separator}conversation_id=${encodeURIComponent(conversationId)}`;
}
