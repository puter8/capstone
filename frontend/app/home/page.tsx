"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { TalkButton } from "@/components/audio/TalkButton";
import { ChatBubble } from "@/components/chat/ChatBubble";
import { ConfirmDialog } from "@/components/dialogs/ConfirmDialog";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import PallyCanvas from "@/components/pally/PallyCanvas";
import { PageLoader } from "@/components/ui/PageLoader";
import { Toast } from "@/components/ui/Toast";
import { pallyApi, PallyApiError } from "@/lib/api";
import type { Subscription, UsageResponse } from "@/lib/api";
import { conversationTurnsToMessages } from "@/lib/api/conversation-messages";
import { requestPallyOpener } from "@/lib/api/opener";
import { markTitlePending } from "@/lib/api/pending-titles";
import {
  clearUserRouteData,
  forgetRememberedUser,
  invalidateConversationData,
  invalidateProfile,
  invalidateUsage,
  loadConversationPage,
  loadProfile,
  loadSubscription,
  loadUsage,
  patchStaleProfileAxes,
  patchStaleUsage,
  peekHomeSnapshot,
  rememberUser,
  schedulePrimaryRoutePrefetch,
  usageFromQuota,
} from "@/lib/api/route-data";
import type { HomeSnapshot } from "@/lib/api/route-data";
import { blobToMonoWav } from "@/lib/audio/blobToWav";
import { useRecorder } from "@/lib/audio/useRecorder";
import { usePally } from "@/lib/hooks/usePally";
import { initialState, reducer } from "@/lib/state/conversation";
import type { Message } from "@/lib/types/message";
import { supabase } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";
import { UsageSummary } from "@/components/usage/UsageSummary";

const CONVERSATION_KEY = "pally:conversationId";

// Returning to home paints the last known state instead of the full-screen loader.
// A conversation to restore (stored id or ?conversation_id) still needs the loader.
// Client-only: on a hard load the cache is empty, so server and client markup match.
function readHomeSnapshot(): HomeSnapshot | null {
  if (typeof window === "undefined") return null;
  if (new URLSearchParams(window.location.search).get("conversation_id")) return null;
  if (window.localStorage.getItem(CONVERSATION_KEY)) return null;
  return peekHomeSnapshot();
}

export default function HomePage() {
  const router = useRouter();
  const [snapshot] = useState(readHomeSnapshot);
  const [state, dispatch] = useReducer(reducer, initialState);
  const { axes, getAccumulatedAxes, resetAxes, restoreAxes, revealAxes, updateFromChatResponse } = usePally(snapshot?.profile.current_axes);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const speakingTimerRef = useRef<number | null>(null);
  const pendingTurnRef = useRef<Promise<void> | null>(null);
  const closingRef = useRef(false);
  const openerRequestRef = useRef(0);
  const pendingOpenerRef = useRef<Promise<void> | null>(null);
  const openerKeyRef = useRef<string | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const firstUserTranscriptRef = useRef<string | null>(null);
  const userIdRef = useRef<string | null>(null);
  const [limitDialogOpen, setLimitDialogOpen] = useState(false);
  const [quotaExhausted, setQuotaExhausted] = useState(snapshot?.usage.remaining_turns === 0);
  const [isClosing, setIsClosing] = useState(false);
  // Controls stay disabled until the session and fresh data are verified, even when
  // the screen is already painted from the snapshot.
  const [isRestoring, setIsRestoring] = useState(true);
  const [paintedFromSnapshot, setPaintedFromSnapshot] = useState(snapshot !== null);
  const [hasRestoredPally, setHasRestoredPally] = useState(snapshot !== null);
  const [warning, setWarning] = useState<string | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(snapshot?.usage ?? null);
  const [subscription, setSubscription] = useState<Subscription | null>(snapshot?.subscription ?? null);

  useEffect(() => {
    let active = true;
    let cancelPrefetch: (() => void) | null = null;

    const restoreConversation = async () => {
      const auth = await supabase.auth.getSession();
      if (auth.error) throw auth.error;
      if (!auth.data.session) {
        forgetRememberedUser();
        if (snapshot) clearUserRouteData(snapshot.userId);
        router.replace("/");
        return;
      }

      const userId = auth.data.session.user.id;
      userIdRef.current = userId;
      if (snapshot && snapshot.userId !== userId) {
        // The painted data belongs to a previous account: drop it and load normally.
        clearUserRouteData(snapshot.userId);
        resetAxes();
        setUsage(null);
        setSubscription(null);
        setQuotaExhausted(false);
        setHasRestoredPally(false);
        setPaintedFromSnapshot(false);
      }
      rememberUser(userId);
      const requestedId = new URLSearchParams(window.location.search).get("conversation_id");
      const storedId = window.localStorage.getItem(CONVERSATION_KEY);
      const conversationId = requestedId ?? storedId;

      const usagePromise = loadUsage(userId);
      const profilePromise = loadProfile(userId);
      const detailPromise = conversationId
        ? loadConversationPage(userId, conversationId)
        : Promise.resolve(null);

      void loadSubscription(userId)
        .then((response) => {
          if (active) setSubscription(response.subscription);
        })
        .catch((error: unknown) => console.error("Subscription status failed", error));

      void pallyApi.recordActivityEvent({
        event_id: crypto.randomUUID(),
        event_type: "app_session_started",
        occurred_at: new Date().toISOString(),
      }).catch((error: unknown) => console.error("Activity event failed", error));

      const [usage, profileResponse, detail] = await Promise.all([
        usagePromise,
        profilePromise,
        detailPromise,
      ]);
      if (!active) return;

      if (active) {
        setUsage(usage);
        const exhausted = usage.remaining_turns === 0;
        setQuotaExhausted(exhausted);
        if (exhausted) setLimitDialogOpen(true);
      }

      // Undefined only against a backend deployed before profile.current_axes existed;
      // Pally then keeps the default look instead of guessing.
      const revealedAxes = profileResponse.profile.current_axes;
      if (active && revealedAxes) restoreAxes(revealedAxes);
      setHasRestoredPally(true);

      cancelPrefetch = schedulePrimaryRoutePrefetch(userId);
      if (!conversationId || !detail) return;

      if (detail.conversation.status !== "active") {
        window.localStorage.removeItem(CONVERSATION_KEY);
        router.replace("/home");
        return;
      }

      const messages = conversationTurnsToMessages(conversationId, detail.turns);
      if (!active) return;
      conversationIdRef.current = conversationId;
      firstUserTranscriptRef.current = messages.find((message) => message.role === "user")?.transcript ?? null;
      if (detail.conversation.turn_count > 0 && detail.conversation.current_axes) {
        updateFromChatResponse({ axes: detail.conversation.current_axes });
      }
      window.localStorage.setItem(CONVERSATION_KEY, conversationId);
      dispatch({ type: "session/load", id: conversationId, messages });
    };

    void restoreConversation()
      .catch((caught: unknown) => {
        if (caught instanceof PallyApiError && (caught.code === "not_found" || caught.code === "unauthorized")) {
          window.localStorage.removeItem(CONVERSATION_KEY);
          if (caught.code === "unauthorized") router.replace("/");
          return;
        }
        if (active) {
          dispatch({ type: "rec/error", reason: "generic", message: caught instanceof Error ? caught.message : "대화를 불러오지 못했어요." });
        }
      })
      .finally(() => {
        if (active) setIsRestoring(false);
      });
    return () => {
      active = false;
      cancelPrefetch?.();
    };
  }, [resetAxes, restoreAxes, router, snapshot, updateFromChatResponse]);

  const ensureConversation = useCallback(async () => {
    if (conversationIdRef.current) return conversationIdRef.current;
    const response = await pallyApi.createConversation(crypto.randomUUID());
    const conversationId = response.conversation.id;
    conversationIdRef.current = conversationId;
    window.localStorage.setItem(CONVERSATION_KEY, conversationId);
    if (!closingRef.current) dispatch({ type: "sessionId/set", id: conversationId });
    return conversationId;
  }, []);

  const stopPlayback = useCallback(() => {
    if (speakingTimerRef.current !== null) {
      window.clearTimeout(speakingTimerRef.current);
      speakingTimerRef.current = null;
    }

    const source = audioSourceRef.current;
    audioSourceRef.current = null;
    if (source) {
      source.onended = null;
      try {
        source.stop();
      } catch (error) {
        console.warn("TTS source stop failed.", error);
      }
      source.disconnect();
    }

    const audio = audioRef.current;
    audioRef.current = null;
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    }

    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  const playTts = useCallback(async (encodedAudio: string) => {
    stopPlayback();
    if (closingRef.current) return;

    const base64 = encodedAudio.startsWith("data:") ? encodedAudio.slice(encodedAudio.indexOf(",") + 1) : encodedAudio;
    const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
    let played = false;
    const audioContext = audioContextRef.current;

    if (audioContext && audioContext.state !== "closed") {
      try {
        if (audioContext.state === "suspended") await audioContext.resume();
        const buffer = await audioContext.decodeAudioData(bytes.buffer.slice(0));
        const source = audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContext.destination);
        if (closingRef.current) {
          source.disconnect();
          return;
        }
        audioSourceRef.current = source;
        source.onended = () => {
          if (audioSourceRef.current !== source) return;
          audioSourceRef.current = null;
          source.disconnect();
          if (!closingRef.current) dispatch({ type: "rec/speakingDone" });
        };
        source.start();
        played = true;
      } catch (error) {
        if (!closingRef.current) {
          console.warn("AudioContext playback failed; using HTMLAudioElement.", error);
        }
      }
    }

    if (played || closingRef.current) return;
    const url = URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" }));
    const audio = new Audio(url);
    audioUrlRef.current = url;
    audioRef.current = audio;
    let finished = false;
    const done = () => {
      if (finished) return;
      finished = true;
      const wasCurrent = audioRef.current === audio;
      if (wasCurrent) audioRef.current = null;
      if (audioUrlRef.current === url) audioUrlRef.current = null;
      URL.revokeObjectURL(url);
      if (wasCurrent && !closingRef.current) dispatch({ type: "rec/speakingDone" });
    };
    audio.onended = done;
    audio.onerror = done;
    void audio.play().catch((error) => {
      if (!closingRef.current) console.warn("TTS playback failed.", error);
      done();
    });
  }, [stopPlayback]);

  useEffect(() => {
    closingRef.current = false;
    return () => {
      closingRef.current = true;
      openerRequestRef.current += 1;
      stopPlayback();
    };
  }, [stopPlayback]);

  const handleProcessed = useCallback(
    async (blob: Blob) => {
      try {
        const conversationId = await ensureConversation();
        const response = await pallyApi.createTurn(conversationId, {
          audio: blob,
          client_started_at: new Date().toISOString(),
          idempotency_key: crypto.randomUUID(),
        });
        if (closingRef.current) return;

        const now = Date.now();
        const userMessage: Message = {
          id: `m-${now}-u`,
          sessionId: conversationId,
          role: "user",
          transcript: response.user.transcript,
          createdAt: response.created_at ?? new Date().toISOString(),
        };
        const pallyMessage: Message = {
          id: `m-${now}-p`,
          sessionId: conversationId,
          role: "pally",
          transcript: response.pally.text,
          createdAt: response.created_at ?? new Date().toISOString(),
          feedback: { items: response.feedback, pending: response.feedback_pending },
        };
        if (firstUserTranscriptRef.current === null) firstUserTranscriptRef.current = response.user.transcript;
        dispatch({ type: "rec/processed", userMsg: userMessage, pallyMsg: pallyMessage });
        updateFromChatResponse({ axes: response.axes });
        const userId = userIdRef.current;
        if (userId) {
          invalidateUsage(userId);
          invalidateConversationData(userId, conversationId);
        }
        const quota = response.quota;
        if (quota?.exhausted) {
          setQuotaExhausted(true);
          setLimitDialogOpen(true);
        }
        if (quota) {
          setUsage((current) => usageFromQuota(current, quota));
          if (userId) patchStaleUsage(userId, quota);
        }
        const notices = response.warnings.map((item) => item.message);
        if (response.replayed) notices.push("네트워크 재시도로 저장된 응답을 다시 불러왔어요.");
        setWarning(notices.length > 0 ? notices.join(" ") : null);

        if (response.pally.audio) {
          await playTts(response.pally.audio);
        } else {
          stopPlayback();
          speakingTimerRef.current = window.setTimeout(() => {
            speakingTimerRef.current = null;
            if (!closingRef.current) dispatch({ type: "rec/speakingDone" });
          }, 3000);
        }
      } catch (error) {
        console.error("Conversation request failed.", error);
        if (closingRef.current) return;
        if (error instanceof PallyApiError && error.code === "quota_exceeded") {
          setQuotaExhausted(true);
          setLimitDialogOpen(true);
        }
        dispatch({
          type: "rec/error",
          reason: "generic",
          message: error instanceof Error ? error.message : "응답을 가져오지 못했어요. 다시 시도해 주세요.",
        });
      }
    },
    [ensureConversation, playTts, stopPlayback, updateFromChatResponse],
  );

  const recorder = useRecorder({
    onStart: () => {
      if (!closingRef.current) {
        dispatch({ type: "rec/start" });
      }
    },
    onStop: (blob) => {
      if (closingRef.current) return;
      dispatch({ type: "rec/stop" });

      const pendingTurn = (async () => {
        try {
          if (!blob) throw new Error("목소리가 잘 들리지 않았어요. 조금 더 길게 말해 주세요.");
          const wavBlob = await blobToMonoWav(blob);
          await handleProcessed(wavBlob);
        } catch (error) {
          console.error("Audio processing failed.", error);
          if (closingRef.current) return;
          dispatch({
            type: "rec/error",
            reason: "generic",
            message: error instanceof Error ? error.message : "오디오 처리에 실패했어요.",
          });
        }
      })();
      pendingTurnRef.current = pendingTurn;
      void pendingTurn.then(() => {
        if (pendingTurnRef.current === pendingTurn) pendingTurnRef.current = null;
      });
    },
    onPermissionDenied: () => {
      if (!closingRef.current) {
        dispatch({ type: "rec/error", reason: "permission-denied", message: "마이크 권한이 필요해요. 브라우저 설정에서 허용해 주세요." });
      }
    },
    onError: (message) => {
      if (!closingRef.current) {
        dispatch({ type: "rec/error", reason: "generic", message });
      }
    },
  });

  const handleSessionEnd = useCallback(async () => {
    if (closingRef.current) return;
    closingRef.current = true;
    openerRequestRef.current += 1;
    setIsClosing(true);
    setWarning(null);
    recorder.cancel();
    stopPlayback();

    const pendingTurn = pendingTurnRef.current;
    // Wait for opener persistence before completing the session.
    const pendingOpener = pendingOpenerRef.current;
    if (pendingOpener) await pendingOpener;
    if (pendingTurn) {
      await pendingTurn;
      if (pendingTurnRef.current === pendingTurn) pendingTurnRef.current = null;
    }
    stopPlayback();

    try {
      const conversationId = conversationIdRef.current;
      const completed = conversationId ? await pallyApi.completeConversation(conversationId) : null;
      const userId = userIdRef.current;
      if (userId) {
        invalidateConversationData(userId, conversationId ?? undefined);
        // Ending a conversation recomputes profile traits on the backend.
        invalidateProfile(userId);
      }
      const firstUserTranscript = firstUserTranscriptRef.current;
      // The final axes are Pally's new look. Keep them as the stale profile value so
      // coming back to home does not flash the previous look before the reload.
      if (userId && firstUserTranscript) patchStaleProfileAxes(userId, getAccumulatedAxes());
      if (conversationId && firstUserTranscript) markTitlePending(conversationId, firstUserTranscript);
      if (completed && completed.warnings.length > 0) {
        setWarning(completed.warnings.map((item) => item.message).join(" "));
      }
      if (firstUserTranscript) revealAxes();
      conversationIdRef.current = null;
      firstUserTranscriptRef.current = null;
      openerKeyRef.current = null;
      window.localStorage.removeItem(CONVERSATION_KEY);
      dispatch({ type: "session/end" });
      router.replace("/home");
    } catch (caught) {
      dispatch({
        type: "rec/error",
        reason: "generic",
        message: caught instanceof Error ? caught.message : "대화를 종료하지 못했어요.",
      });
    } finally {
      closingRef.current = false;
      setIsClosing(false);
    }
  }, [getAccumulatedAxes, recorder, revealAxes, router, stopPlayback]);

  const handlePressStart = useCallback(() => {
    if (closingRef.current || quotaExhausted || isRestoring || !hasRestoredPally) return;
    void recorder.start();
  }, [hasRestoredPally, isRestoring, quotaExhausted, recorder]);

  // Must run inside a user gesture so mobile browsers allow TTS playback afterwards.
  const unlockAudio = useCallback(() => {
    try {
      if (!audioContextRef.current) {
        const AudioContextConstructor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioContextRef.current = new AudioContextConstructor();
      }
      if (audioContextRef.current.state === "suspended") void audioContextRef.current.resume();
    } catch (error) {
      console.warn("AudioContext is unavailable.", error);
    }
  }, []);

  const handlePressStop = useCallback(() => {
    if (closingRef.current) return;
    dispatch({ type: "rec/stop" });
    unlockAudio();
    recorder.stop();
  }, [recorder, unlockAudio]);

  const handleStartConversation = useCallback(() => {
    if (pendingOpenerRef.current || closingRef.current || quotaExhausted || isRestoring || !hasRestoredPally || state.messages.length > 0) return;
    unlockAudio();
    const requestId = openerRequestRef.current + 1;
    openerRequestRef.current = requestId;
    setWarning(null);
    dispatch({ type: "opener/request" });

    const pending = (async () => {
      try {
        const conversationId = await ensureConversation();
        if (openerRequestRef.current !== requestId || closingRef.current) return;
        openerKeyRef.current ??= crypto.randomUUID();
        const opener = await requestPallyOpener(conversationId, openerKeyRef.current);
        const userId = userIdRef.current;
        if (userId) invalidateConversationData(userId, conversationId);
        if (openerRequestRef.current !== requestId || closingRef.current) return;
        setWarning(opener.warnings.length ? opener.warnings.map((warning) => warning.message).join(" ") : null);
        dispatch({
          type: "opener/received",
          pallyMsg: {
            id: `m-${Date.now()}-opener`,
            sessionId: conversationId,
            role: "pally",
            transcript: opener.text,
            createdAt: new Date().toISOString(),
          },
        });
        if (opener.audio) {
          await playTts(opener.audio);
        } else {
          stopPlayback();
          speakingTimerRef.current = window.setTimeout(() => {
            speakingTimerRef.current = null;
            if (!closingRef.current) dispatch({ type: "rec/speakingDone" });
          }, 3000);
        }
      } catch (error) {
        console.error("Pally opener request failed.", error);
        if (openerRequestRef.current !== requestId || closingRef.current) return;
        if (error instanceof PallyApiError && error.code === "conversation_started") {
          try {
            const conversationId = conversationIdRef.current;
            if (!conversationId) throw new Error("대화를 다시 불러와 주세요.");
            const detail = await pallyApi.getConversation(conversationId, { limit: 50 });
            if (openerRequestRef.current !== requestId || closingRef.current) return;
            if (detail.conversation.status !== "active") throw new PallyApiError(409, "conversation_closed", "이미 종료된 대화예요.");
            const messages = conversationTurnsToMessages(conversationId, detail.turns);
            firstUserTranscriptRef.current = messages.find((message) => message.role === "user")?.transcript ?? null;
            if (detail.conversation.current_axes) updateFromChatResponse({ axes: detail.conversation.current_axes });
            dispatch({ type: "session/load", id: conversationId, messages });
            dispatch({ type: "rec/speakingDone" });
            setWarning("이미 시작된 대화를 불러왔어요. 이어서 말해 주세요.");
            return;
          } catch (restoreError) {
            console.error("Started conversation recovery failed", restoreError);
            error = restoreError;
          }
        }
        if (error instanceof PallyApiError && (error.code === "conversation_closed" || error.code === "not_found")) {
          const userId = userIdRef.current;
          if (userId) invalidateConversationData(userId, conversationIdRef.current ?? undefined);
          conversationIdRef.current = null;
          firstUserTranscriptRef.current = null;
          openerKeyRef.current = null;
          window.localStorage.removeItem(CONVERSATION_KEY);
          dispatch({ type: "session/end" });
          router.replace("/home");
        }
        dispatch({
          type: "rec/error",
          reason: "generic",
          message: error instanceof PallyApiError && error.code === "conversation_closed"
            ? "이미 종료된 대화예요. 대화 시작하기를 눌러 새로 시작해 주세요."
            : error instanceof PallyApiError && error.code === "opener_failed"
              ? "Pally가 먼저 말을 걸지 못했어요. 대화 시작하기를 눌러 다시 시도해 주세요."
              : error instanceof Error ? error.message : "Pally가 말을 걸지 못했어요. 다시 시도해 주세요.",
        });
      }
    })();
    pendingOpenerRef.current = pending;
    void pending.finally(() => {
      if (pendingOpenerRef.current === pending) pendingOpenerRef.current = null;
    });
  }, [ensureConversation, hasRestoredPally, isRestoring, playTts, quotaExhausted, router, state.messages.length, stopPlayback, unlockAudio, updateFromChatResponse]);

  const handleToggleHistory = useCallback(() => {
    if (!state.historyOpen) {
      const conversationId = conversationIdRef.current;
      if (conversationId) {
        void pallyApi.recordActivityEvent({
          event_id: crypto.randomUUID(),
          event_type: "transcript_expanded",
          occurred_at: new Date().toISOString(),
          conversation_id: conversationId,
        }).catch((error: unknown) => console.error("Activity event failed", error));
      }
    }
    dispatch({ type: "history/toggle" });
  }, [state.historyOpen]);

  const isIdle = state.rec.kind === "idle";
  const isProcessing = state.rec.kind === "processing";
  const isRecording = state.rec.kind === "recording";
  const errorVisible = state.rec.kind === "error";
  const showChatBubble = (state.messages.length > 0 || isRecording || isProcessing) && !errorVisible;
  const historyCoversScreen = state.historyOpen;
  // Pally speaks first: until the opener arrives there is nothing to reply to, so hide the mic.
  const showStartScreen = state.messages.length === 0 && (isIdle || errorVisible);

  if (isRestoring && !paintedFromSnapshot) {
    return (
      <MobileShell minHeight={640}>
        <PageLoader />
      </MobileShell>
    );
  }

  return (
    <MobileShell minHeight={showChatBubble ? 800 : 640}>
      <div className="absolute right-4 top-5 z-40">
        <UsageSummary subscription={subscription} usage={usage} />
      </div>
      {showChatBubble ? (
        <>
          <button aria-label="대화 종료" className="absolute left-4 top-[23px] z-50 grid size-[41px] place-items-center border-0 bg-transparent p-0" disabled={isClosing} onClick={() => { void handleSessionEnd(); }} type="button">
            <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 20 20">
              <path d="M4 4l12 12M16 4 4 16" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
            </svg>
          </button>
          <div className="absolute inset-x-0 top-0 z-10">
            <ChatBubble
              expanded={state.historyOpen}
              listening={isRecording}
              messages={state.messages}
              onToggleExpand={handleToggleHistory}
              thinking={isProcessing}
            />
          </div>
        </>
      ) : null}

      {!historyCoversScreen ? (
        <>
          <div
            className={cn(
              "absolute left-1/2 -translate-x-1/2 transition-[top,transform] duration-500 ease-out",
              showStartScreen ? "top-[calc(308px_+_min(0px,_100%_-_874px))] scale-75" : showChatBubble ? "top-[382px]" : "top-[calc(369px_+_min(0px,_100%_-_874px))]",
            )}
          >
            {hasRestoredPally ? (
              <PallyCanvas axes={axes} gaze={isProcessing ? "up-right" : "center"} size={308} />
            ) : (
              <div className="flex size-[308px] flex-col items-center justify-center gap-3 text-caption-1 text-primary" role="status">
                Pally를 불러오지 못했어요.
                <button className="underline underline-offset-4" onClick={() => window.location.reload()} type="button">
                  다시 불러오기
                </button>
              </div>
            )}
          </div>
          {showStartScreen ? (
            <div className="absolute inset-x-0 top-[calc(578px_+_min(0px,_100%_-_874px))] z-20 flex flex-col items-center px-4 text-center">
              <h2 className="text-title-1 text-text">Pally&apos;s here to chat!</h2>
              <p className="mt-1 text-body text-text-tertiary">소리를 켜고 시작해 주세요 <span aria-hidden="true">🔊</span></p>
              <button
                className="mt-4 h-20 w-[304px] max-w-full rounded-full bg-primary-soft p-2 transition-transform duration-150 active:scale-95 disabled:opacity-50"
                disabled={isClosing || isRestoring || !hasRestoredPally || quotaExhausted}
                onClick={() => { void handleStartConversation(); }}
                type="button"
              >
                <span className="grid size-full place-items-center rounded-full bg-primary text-button-1 text-white shadow-[0_4px_8px_rgba(0,0,0,0.12)]">
                  대화 시작하기
                </span>
              </button>
            </div>
          ) : (
            <div className={`absolute left-1/2 z-20 -translate-x-1/2 ${showChatBubble ? "top-[690px]" : "top-[calc(649px_+_min(0px,_100%_-_874px))]"}`}>
              <TalkButton disabled={isClosing || isRestoring || !hasRestoredPally || quotaExhausted} onPressStart={handlePressStart} onPressStop={handlePressStop} rec={state.rec} />
            </div>
          )}
        </>
      ) : null}

      <div
        className={cn(
          "absolute inset-x-0 z-40 px-4",
          // Toasts float 12px above the main action: start block (578px), talk button (649px), or chat-mode talk button (690px). Idle layouts shift up on short screens.
          showStartScreen
            ? "bottom-[calc(100%_-_566px_-_min(0px,_100%_-_874px))]"
            : showChatBubble
              ? "bottom-[calc(100%_-_678px)]"
              : "bottom-[calc(100%_-_637px_-_min(0px,_100%_-_874px))]",
        )}
      >
        <Toast message={state.rec.kind === "error" ? state.rec.message : ""} onDismiss={() => dispatch({ type: "rec/dismissError" })} visible={errorVisible} />
        <Toast message={warning ?? ""} onDismiss={() => setWarning(null)} visible={warning !== null} />
      </div>

      {!showChatBubble ? <BottomNav /> : null}
      {limitDialogOpen ? (
        <ConfirmDialog
          body="오늘 사용할 수 있는 무료 대화를 모두 사용했어요. 다음 KST 자정에 다시 충전돼요."
          confirmLabel="확인"
          onCancel={() => setLimitDialogOpen(false)}
          onConfirm={() => setLimitDialogOpen(false)}
          title="오늘의 대화를 모두 사용했어요"
        />
      ) : null}
    </MobileShell>
  );
}
