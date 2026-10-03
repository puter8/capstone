// The backend generates a conversation title in the background after /complete.
// Until it lands, list responses fall back to the first user utterance, so we
// remember that fallback and treat a matching title as "still generating".

const TITLE_FALLBACK_MAX_CHARS = 60;
const TITLE_WAIT_MS = 10_000;

type PendingTitle = {
  fallbackTitle: string;
  expiresAt: number;
};

const pendingTitles = new Map<string, PendingTitle>();

// Mirrors backend `_truncate(transcript, 60)`: collapse whitespace, cut by code point.
function fallbackConversationTitle(firstTranscript: string): string | null {
  const collapsed = firstTranscript.split(/\s+/).filter(Boolean).join(" ");
  if (!collapsed) return null;
  return Array.from(collapsed).slice(0, TITLE_FALLBACK_MAX_CHARS).join("");
}

export function markTitlePending(conversationId: string, firstTranscript: string): void {
  const fallbackTitle = fallbackConversationTitle(firstTranscript);
  if (!fallbackTitle) return;
  pendingTitles.set(conversationId, { fallbackTitle, expiresAt: Date.now() + TITLE_WAIT_MS });
}

export function isTitlePending(conversationId: string, title: string | null, now: number): boolean {
  const pending = pendingTitles.get(conversationId);
  if (!pending) return false;
  if (now >= pending.expiresAt || title !== pending.fallbackTitle) {
    pendingTitles.delete(conversationId);
    return false;
  }
  return true;
}
