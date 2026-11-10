export const CONVERSATION_STORAGE_KEY = "pally:conversationId";

/**
 * Marks a resume the home screen has not consumed yet, so it shows its loading
 * state instead of painting the idle home from the cached snapshot. Per tab and
 * read once, so a later visit does not reopen the conversation on its own.
 */
export const RESUME_INTENT_KEY = "pally:resumeConversationId";

/**
 * Hands a finished conversation to the home screen without writing to it.
 *
 * Opening a conversation must not change it. Reopening is deferred to the home
 * screen, which does it when the user sends the first turn, so entering a past
 * conversation and leaving it saves nothing.
 *
 * Shared by the v1 note card and the v2 session card; the caller decides
 * which home route receives the `conversation_id` query.
 */
export function resumeConversation(conversationId: string, homePath: string): string {
  // Nothing is invalidated here. This used to reopen the conversation, so the cached
  // list and detail were out of date the moment it was pressed; now that opening it
  // writes nothing, dropping them would only throw away a page that is still correct.
  // The query alone is not enough: a soft navigation can render home before the URL
  // is committed, and the idle screen would paint for a moment before the conversation.
  window.sessionStorage.setItem(RESUME_INTENT_KEY, conversationId);
  const separator = homePath.includes("?") ? "&" : "?";
  return `${homePath}${separator}conversation_id=${encodeURIComponent(conversationId)}`;
}
