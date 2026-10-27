"use client";

/**
 * Conversation session logic for the home screen, shared by the v2 design.
 *
 * Ported from app/home/page.tsx so the screen can be purely presentational.
 * Keeps the invariants of the original:
 *   - `closingRef` is true while unmounting and from endSession until its
 *     finally block; every async continuation checks it before dispatching.
 *   - `unlockAudio()` runs synchronously inside a user gesture, before the
 *     first await, so mobile browsers allow TTS playback afterwards.
 *   - `openerRequestRef` invalidates stale opener requests.
 *
 * Adds the v2 dock capabilities: skipping Pally's playback, replaying the
 * last reply (current session only; the backend returns no audio URL), the
 * recording start time for the elapsed arc, and a one-button limit sheet.
 */

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";

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
import { MAX_DURATION_MS, useRecorder } from "@/lib/audio/useRecorder";
import { usePally } from "@/lib/hooks/usePally";
import { initialState, reducer, type ConversationState } from "@/lib/state/conversation";
import { supabase } from "@/lib/supabase/client";
import type { Axes } from "@/lib/types/character";
import type { Message } from "@/lib/types/message";

export const CONVERSATION_KEY = "pally:conversationId";

export type HomeRoutes = {
  /** Where to send a signed-out user. */
  login: string;
  /** This screen's own path, used to clear query params after a session ends. */
  home: string;
  /** Voice baseline registration, required before the first turn. */
  onboardingVoice: string;
};

export type HomeConversation = {
  state: ConversationState;
  axes: Axes;
  usage: UsageResponse | null;
  subscription: Subscription | null;
  displayName: string | null;
  warning: string | null;
  isRestoring: boolean;
  paintedFromSnapshot: boolean;
  hasRestoredPally: boolean;
  baselineAllowed: boolean;
  quotaExhausted: boolean;
  isClosing: boolean;
  limitSheetOpen: boolean;
  /** The last reply's audio is still in memory and can be replayed. */
  canReplay: boolean;
  replaying: boolean;
  maxRecordingMs: number;
  startConversation: () => void;
  pressStart: () => void;
  pressStop: () => void;
  skipPlayback: () => void;
  replayLastReply: () => void;
  toggleHistory: () => void;
  endSession: () => Promise<void>;
  dismissError: () => void;
  dismissWarning: () => void;
  closeLimitSheet: () => void;
};

// Returning to home paints the last known state instead of the full-screen loader.
// A conversation to restore (stored id or ?conversation_id) still needs the loader.
// Client-only: on a hard load the cache is empty, so server and client markup match.
function readHomeSnapshot(): HomeSnapshot | null {
  if (typeof window === "undefined") return null;
  if (new URLSearchParams(window.location.search).get("conversation_id")) return null;
  if (window.localStorage.getItem(CONVERSATION_KEY)) return null;
  return peekHomeSnapshot();
}

function decodeAudio(encodedAudio: string) {
  const base64 = encodedAudio.startsWith("data:") ? encodedAudio.slice(encodedAudio.indexOf(",") + 1) : encodedAudio;
  return Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
}

export function useHomeConversation(routes: HomeRoutes): HomeConversation {
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
  const lastAudioRef = useRef<string | null>(null);
  const [limitSheetOpen, setLimitSheetOpen] = useState(false);
  const [quotaExhausted, setQuotaExhausted] = useState(snapshot?.usage.remaining_turns === 0);
  const [isClosing, setIsClosing] = useState(false);
  // Controls stay disabled until the session and fresh data are verified, even when
  // the screen is already painted from the snapshot.
  const [isRestoring, setIsRestoring] = useState(true);
  const [baselineAllowed, setBaselineAllowed] = useState(false);
  const [paintedFromSnapshot, setPaintedFromSnapshot] = useState(snapshot !== null);
  const [hasRestoredPally, setHasRestoredPally] = useState(snapshot !== null);
  const [warning, setWarning] = useState<string | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(snapshot?.usage ?? null);
  const [subscription, setSubscription] = useState<Subscription | null>(snapshot?.subscription ?? null);
  const [displayName, setDisplayName] = useState<string | null>(snapshot?.profile.display_name ?? null);
  const [canReplay, setCanReplay] = useState(false);
  const [replaying, setReplaying] = useState(false);

  useEffect(() => {
    let active = true;
    let cancelPrefetch: (() => void) | null = null;

    const restoreConversation = async () => {
      const auth = await supabase.auth.getSession();
      if (auth.error) throw auth.error;
      if (!auth.data.session) {
        forgetRememberedUser();
        if (snapshot) clearUserRouteData(snapshot.userId);
        router.replace(routes.login);
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
        setDisplayName(null);
        setQuotaExhausted(false);
        setHasRestoredPally(false);
        setPaintedFromSnapshot(false);
      }
      rememberUser(userId);
      const requestedId = new URLSearchParams(window.location.search).get("conversation_id");
      const storedId = window.localStorage.getItem(CONVERSATION_KEY);
      const conversationId = requestedId ?? storedId;

      const baseline = await pallyApi.getEnergyBaseline();
      if (!active) return;
      if (baseline.status === "required") {
        if (conversationId) window.localStorage.setItem(CONVERSATION_KEY, conversationId);
        router.replace(routes.onboardingVoice);
        return;
      }
      setBaselineAllowed(true);

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

      const [usageResponse, profileResponse, detail] = await Promise.all([
        usagePromise,
        profilePromise,
        detailPromise,
      ]);
      if (!active) return;

      setUsage(usageResponse);
      const exhausted = usageResponse.remaining_turns === 0;
      setQuotaExhausted(exhausted);
      if (exhausted) setLimitSheetOpen(true);

      // Undefined only against a backend deployed before profile.current_axes existed;
      // Pally then keeps the default look instead of guessing.
      const revealedAxes = profileResponse.profile.current_axes;
      if (revealedAxes) restoreAxes(revealedAxes);
      setDisplayName(profileResponse.profile.display_name);
      setHasRestoredPally(true);

      cancelPrefetch = schedulePrimaryRoutePrefetch(userId);
      if (!conversationId || !detail) return;

      if (detail.conversation.status !== "active") {
        window.localStorage.removeItem(CONVERSATION_KEY);
        router.replace(routes.home);
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
          if (caught.code === "unauthorized") router.replace(routes.login);
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
  }, [resetAxes, restoreAxes, router, routes.home, routes.login, routes.onboardingVoice, snapshot, updateFromChatResponse]);

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

  // Plays base64 audio through the unlocked AudioContext, falling back to an
  // HTMLAudioElement. `onDone` runs once when playback ends or fails to start.
  const playAudio = useCallback(async (encodedAudio: string, onDone: () => void) => {
    stopPlayback();
    if (closingRef.current) return;

    const bytes = decodeAudio(encodedAudio);
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
          if (!closingRef.current) onDone();
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
      if (wasCurrent && !closingRef.current) onDone();
    };
    audio.onended = done;
    audio.onerror = done;
    void audio.play().catch((error) => {
      if (!closingRef.current) console.warn("TTS playback failed.", error);
      done();
    });
  }, [stopPlayback]);

  const finishSpeaking = useCallback(() => {
    dispatch({ type: "rec/speakingDone" });
  }, []);

  // Plays Pally's reply and remembers it for the dock's replay button.
  const playReply = useCallback(async (encodedAudio: string | null | undefined) => {
    if (encodedAudio) {
      lastAudioRef.current = encodedAudio;
      setCanReplay(true);
      await playAudio(encodedAudio, finishSpeaking);
      return;
    }
    stopPlayback();
    speakingTimerRef.current = window.setTimeout(() => {
      speakingTimerRef.current = null;
      if (!closingRef.current) dispatch({ type: "rec/speakingDone" });
    }, 3000);
  }, [finishSpeaking, playAudio, stopPlayback]);

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
          segments: response.pally.segments,
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
          setLimitSheetOpen(true);
        }
        if (quota) {
          setUsage((current) => usageFromQuota(current, quota));
          if (userId) patchStaleUsage(userId, quota);
        }
        const notices = response.warnings.map((item) => item.message);
        if (response.replayed) notices.push("네트워크 재시도로 저장된 응답을 다시 불러왔어요.");
        setWarning(notices.length > 0 ? notices.join(" ") : null);

        await playReply(response.pally.audio);
      } catch (error) {
        console.error("Conversation request failed.", error);
        if (closingRef.current) return;
        if (error instanceof PallyApiError && error.code === "quota_exceeded") {
          setQuotaExhausted(true);
          setLimitSheetOpen(true);
        }
        dispatch({
          type: "rec/error",
          reason: "generic",
          message: error instanceof Error ? error.message : "응답을 가져오지 못했어요. 다시 시도해 주세요.",
        });
      }
    },
    [ensureConversation, playReply, updateFromChatResponse],
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

  const endSession = useCallback(async () => {
    if (closingRef.current) return;
    closingRef.current = true;
    openerRequestRef.current += 1;
    setIsClosing(true);
    setWarning(null);
    setReplaying(false);
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
      lastAudioRef.current = null;
      setCanReplay(false);
      window.localStorage.removeItem(CONVERSATION_KEY);
      dispatch({ type: "session/end" });
      router.replace(routes.home);
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
  }, [getAccumulatedAxes, recorder, revealAxes, router, routes.home, stopPlayback]);

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

  const pressStart = useCallback(() => {
    if (closingRef.current || replaying || quotaExhausted || isRestoring || !hasRestoredPally || !baselineAllowed) return;
    // The 30s auto-stop ends the recording without a gesture, so unlock here as well.
    unlockAudio();
    void recorder.start();
  }, [baselineAllowed, hasRestoredPally, isRestoring, quotaExhausted, recorder, replaying, unlockAudio]);

  const pressStop = useCallback(() => {
    if (closingRef.current) return;
    dispatch({ type: "rec/stop" });
    unlockAudio();
    recorder.stop();
  }, [recorder, unlockAudio]);

  const skipPlayback = useCallback(() => {
    if (closingRef.current) return;
    if (replaying) {
      stopPlayback();
      setReplaying(false);
      return;
    }
    if (state.rec.kind !== "speaking") return;
    stopPlayback();
    dispatch({ type: "rec/speakingDone" });
  }, [replaying, state.rec.kind, stopPlayback]);

  const replayLastReply = useCallback(() => {
    const encodedAudio = lastAudioRef.current;
    if (closingRef.current || replaying || !encodedAudio || state.rec.kind !== "idle") return;
    unlockAudio();
    setReplaying(true);
    void playAudio(encodedAudio, () => setReplaying(false)).catch((error: unknown) => {
      console.error("Replay failed.", error);
      setReplaying(false);
    });
  }, [playAudio, replaying, state.rec.kind, unlockAudio]);

  const startConversation = useCallback(() => {
    if (pendingOpenerRef.current || closingRef.current || quotaExhausted || isRestoring || !hasRestoredPally || !baselineAllowed || state.messages.length > 0) return;
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
        setWarning(opener.warnings.length ? opener.warnings.map((item) => item.message).join(" ") : null);
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
        await playReply(opener.audio);
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
          router.replace(routes.home);
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
  }, [baselineAllowed, ensureConversation, hasRestoredPally, isRestoring, playReply, quotaExhausted, router, routes.home, state.messages.length, unlockAudio, updateFromChatResponse]);

  const toggleHistory = useCallback(() => {
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

  const dismissError = useCallback(() => dispatch({ type: "rec/dismissError" }), []);
  const dismissWarning = useCallback(() => setWarning(null), []);
  const closeLimitSheet = useCallback(() => setLimitSheetOpen(false), []);

  return {
    state,
    axes,
    usage,
    subscription,
    displayName,
    warning,
    isRestoring,
    paintedFromSnapshot,
    hasRestoredPally,
    baselineAllowed,
    quotaExhausted,
    isClosing,
    limitSheetOpen,
    canReplay,
    replaying,
    maxRecordingMs: MAX_DURATION_MS,
    startConversation,
    pressStart,
    pressStop,
    skipPlayback,
    replayLastReply,
    toggleHistory,
    endSession,
    dismissError,
    dismissWarning,
    closeLimitSheet,
  };
}
