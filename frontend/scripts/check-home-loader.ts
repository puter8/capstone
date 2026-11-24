/**
 * The home screen blocks on a full-screen loader only when there is an
 * unfinished conversation to bring back.
 *
 * Coming to an idle home used to wait on the session check, the voice baseline,
 * usage, the profile and a conversation read before anything was painted - a
 * blank screen on every cold start, including the common case where there was
 * nothing to restore at all. Painting at once is safe because the talk button
 * stays disabled until the restore finishes (controlsLocked in app/home/page.tsx).
 */
import { equal, match } from "node:assert/strict";
import { readFileSync } from "node:fs";

import { CONVERSATION_STORAGE_KEY, hasConversationToRestore, RESUME_INTENT_KEY }
  from "../lib/api/resume-conversation";

type Store = Record<string, string>;

function withBrowser(search: string, local: Store, session: Store): void {
  const store = (data: Store) => ({
    getItem: (key: string) => (key in data ? data[key] : null),
    setItem: (key: string, value: string) => { data[key] = value; },
    removeItem: (key: string) => { delete data[key]; },
  });
  (globalThis as { window?: unknown }).window = {
    location: { search },
    localStorage: store(local),
    sessionStorage: store(session),
  };
}

// Nothing stored: the idle home has nothing to wait for.
withBrowser("", {}, {});
equal(hasConversationToRestore(), false, "an idle home must not block on a loader");

// A conversation left unfinished on this device.
withBrowser("", { [CONVERSATION_STORAGE_KEY]: "conversation-1" }, {});
equal(hasConversationToRestore(), true, "an unfinished conversation is brought back");

// Opened from the history list, before the URL is committed.
withBrowser("", {}, { [RESUME_INTENT_KEY]: "conversation-2" });
equal(hasConversationToRestore(), true, "a resume marker must win over the idle home");

// The same resume once the query has landed.
withBrowser("?conversation_id=conversation-2", {}, {});
equal(hasConversationToRestore(), true, "?conversation_id is a conversation to restore");

// Reading must not consume the marker: the restore effect does that, and
// swallowing it here would drop the conversation the user asked to reopen.
const session: Store = { [RESUME_INTENT_KEY]: "conversation-3" };
withBrowser("", {}, session);
hasConversationToRestore();
equal(session[RESUME_INTENT_KEY], "conversation-3", "checking must not clear the resume marker");

// Server render has no storage to read and must not claim a restore.
delete (globalThis as { window?: unknown }).window;
equal(hasConversationToRestore(), false, "no window means nothing to restore");

// The screen must actually use it, not just export it.
const page = readFileSync(new URL("../app/home/page.tsx", import.meta.url), "utf8");
match(
  page,
  /if \(home\.isRestoring && !home\.paintedFromSnapshot && home\.restoringConversation\)/,
  "the loader must be gated on there being a conversation to restore",
);

// Painting the idle home early means Pally's axes are not loaded yet. The
// default axes are a yellow round Pally, which is a different character from
// almost every user's: it must not be drawn and then corrected.
match(
  page,
  /home\.hasRestoredPally \? \(\s*<>\s*<Stage axes=\{home\.axes\}/,
  "the idle stage must wait for the profile instead of drawing the default axes",
);
match(page, /Pally를 준비하고 있어요/, "the held stage slot must say Pally is on the way");

console.log("home loader: PASS");
