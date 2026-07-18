"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";

import { TalkButton } from "@/components/audio/TalkButton";
import { ChatBubble } from "@/components/chat/ChatBubble";
import { MobileShell } from "@/components/layout/MobileShell";
import { BottomNav } from "@/components/nav/BottomNav";
import PallyCanvas from "@/components/pally/PallyCanvas";
import { Toast } from "@/components/ui/Toast";
import { blobToMonoWav } from "@/lib/audio/blobToWav";
import { useRecorder } from "@/lib/audio/useRecorder";
import { usePally } from "@/lib/hooks/usePally";
import { mockChat } from "@/lib/mocks/chat-mock";
import { initialState, reducer } from "@/lib/state/conversation";
import type { ChatApiResponse } from "@/lib/types/character";
import type { Message } from "@/lib/types/message";

const SESSION_KEY = "pally:sessionId";

function createSessionId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `session-${Date.now()}`;
}

export default function HomePage() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { axes, getAccumulatedAxes, revealAxes, updateFromChatResponse } = usePally();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (state.sessionId !== null) return;
    const stored = window.localStorage.getItem(SESSION_KEY);
    if (stored) {
      dispatch({ type: "sessionId/set", id: stored });
      return;
    }
    const id = createSessionId();
    window.localStorage.setItem(SESSION_KEY, id);
    dispatch({ type: "sessionId/set", id });
  }, [state.sessionId]);

  const transcribeAudio = useCallback(async (blob: Blob) => {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) throw new Error("NEXT_PUBLIC_BACKEND_URL is not configured");

    let audioBlob: Blob;
    let filename: string;
    try {
      audioBlob = await blobToMonoWav(blob);
      filename = "recording.wav";
    } catch (error) {
      console.warn("WAV conversion failed; sending the original recording.", error);
      audioBlob = blob;
      filename = "recording.webm";
    }

    const formData = new FormData();
    formData.append("audio", audioBlob, filename);
    const response = await fetch(`${backendUrl}/api/stt`, { method: "POST", body: formData });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`STT failed ${response.status}: ${text}`);
    }
    const data = (await response.json()) as { transcript: string };
    return data.transcript;
  }, []);

  const playTts = useCallback(async (encodedAudio: string) => {
    const bytes = Uint8Array.from(atob(encodedAudio), (character) => character.charCodeAt(0));
    const finish = () => dispatch({ type: "rec/speakingDone" });
    let played = false;
    const audioContext = audioContextRef.current;

    if (audioContext && audioContext.state !== "closed") {
      try {
        if (audioContext.state === "suspended") await audioContext.resume();
        const buffer = await audioContext.decodeAudioData(bytes.buffer.slice(0));
        const source = audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContext.destination);
        source.onended = finish;
        source.start();
        played = true;
      } catch (error) {
        console.warn("AudioContext playback failed; using HTMLAudioElement.", error);
      }
    }

    if (played) return;
    const url = URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" }));
    audioRef.current?.pause();
    const audio = new Audio(url);
    audioRef.current = audio;
    const done = () => {
      URL.revokeObjectURL(url);
      audioRef.current = null;
      finish();
    };
    audio.onended = done;
    audio.onerror = done;
    void audio.play().catch((error) => {
      console.warn("TTS playback failed.", error);
      done();
    });
  }, []);

  const handleProcessed = useCallback(
    async (utterance: string) => {
      if (!state.sessionId) return;
      try {
        const response = await mockChat({
          utterance,
          session_id: state.sessionId,
          level: "B1",
          current_axes: getAccumulatedAxes(),
          conversation_history: state.messages.map((message) => ({
            role: message.role,
            content: message.transcript,
          })),
        });
        const now = Date.now();
        const userMessage: Message = {
          id: `m-${now}-u`,
          sessionId: state.sessionId,
          role: "user",
          transcript: response.transcript,
          createdAt: new Date().toISOString(),
        };
        const pallyMessage: Message = {
          id: `m-${now}-p`,
          sessionId: state.sessionId,
          role: "pally",
          transcript: response.reply,
          createdAt: new Date().toISOString(),
        };
        dispatch({ type: "rec/processed", userMsg: userMessage, pallyMsg: pallyMessage });
        updateFromChatResponse(response as unknown as ChatApiResponse);

        if (response.tts_audio) {
          await playTts(response.tts_audio);
        } else {
          window.setTimeout(() => dispatch({ type: "rec/speakingDone" }), 3000);
        }
      } catch (error) {
        console.error("Conversation request failed.", error);
        dispatch({
          type: "rec/error",
          reason: "generic",
          message: error instanceof Error ? error.message : "응답을 가져오지 못했어요. 다시 시도해 주세요.",
        });
      }
    },
    [getAccumulatedAxes, playTts, state.messages, state.sessionId, updateFromChatResponse],
  );

  const recorder = useRecorder({
    onStart: () => dispatch({ type: "rec/start" }),
    onStop: async (blob, webSpeechTranscript) => {
      dispatch({ type: "rec/stop" });
      if (!state.sessionId) {
        dispatch({ type: "rec/error", reason: "generic", message: "세션을 만드는 중이에요. 잠시 후 다시 시도해 주세요." });
        return;
      }

      try {
        let utterance = webSpeechTranscript;
        if (!utterance) {
          if (!blob) throw new Error("녹음된 오디오를 찾을 수 없어요. 다시 시도해 주세요.");
          try {
            utterance = await transcribeAudio(blob);
          } catch (firstError) {
            console.warn("First STT request failed; retrying once.", firstError);
            await new Promise<void>((resolve) => window.setTimeout(resolve, 600));
            utterance = await transcribeAudio(blob);
          }
        }
        if (!utterance.trim()) throw new Error("음성 인식 결과가 비어 있어요. 다시 말해 주세요.");
        await handleProcessed(utterance);
      } catch (error) {
        console.error("Audio processing failed.", error);
        dispatch({
          type: "rec/error",
          reason: "generic",
          message: error instanceof Error ? error.message : "오디오 처리에 실패했어요.",
        });
      }
    },
    onPermissionDenied: () => dispatch({ type: "rec/error", reason: "permission-denied", message: "마이크 권한이 필요해요. 브라우저 설정에서 허용해 주세요." }),
    onError: (message) => dispatch({ type: "rec/error", reason: "generic", message }),
  });

  const handleSessionEnd = useCallback(() => {
    revealAxes();
    const newId = createSessionId();
    window.localStorage.setItem(SESSION_KEY, newId);
    dispatch({ type: "session/end", newId });
  }, [revealAxes]);

  const handlePressStart = useCallback(() => {
    void recorder.start();
  }, [recorder]);

  const handlePressStop = useCallback(() => {
    dispatch({ type: "rec/stop" });
    try {
      if (!audioContextRef.current) {
        const AudioContextConstructor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioContextRef.current = new AudioContextConstructor();
      }
      if (audioContextRef.current.state === "suspended") void audioContextRef.current.resume();
    } catch (error) {
      console.warn("AudioContext is unavailable.", error);
    }
    recorder.stop();
  }, [recorder]);

  const isIdle = state.rec.kind === "idle";
  const isProcessing = state.rec.kind === "processing";
  const isRecording = state.rec.kind === "recording";
  const errorVisible = state.rec.kind === "error";
  const showChatBubble = (state.messages.length > 0 || isRecording || isProcessing) && !errorVisible;
  const historyCoversScreen = state.historyOpen && !isIdle;

  return (
    <MobileShell>
      {showChatBubble ? (
        <>
          <button aria-label="대화 종료" className="absolute left-4 top-[23px] z-50 grid size-[41px] place-items-center border-0 bg-transparent p-0" onClick={handleSessionEnd} type="button">
            <svg aria-hidden="true" className="size-5" fill="none" viewBox="0 0 20 20">
              <path d="M4 4l12 12M16 4 4 16" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
            </svg>
          </button>
          <div className="absolute inset-x-0 top-0 z-10">
            <ChatBubble
              expanded={state.historyOpen}
              listening={isRecording}
              messages={state.messages}
              onToggleExpand={() => dispatch({ type: "history/toggle" })}
              thinking={isProcessing}
            />
          </div>
        </>
      ) : null}

      {!historyCoversScreen ? (
        <>
          <div className={`absolute left-1/2 -translate-x-1/2 ${showChatBubble ? "top-[382px]" : "top-[369px]"}`}>
            <PallyCanvas axes={axes} size={308} />
          </div>
          <div className={`absolute left-1/2 z-20 -translate-x-1/2 ${showChatBubble ? "top-[690px]" : "top-[649px]"}`}>
            <TalkButton onPressStart={handlePressStart} onPressStop={handlePressStop} rec={state.rec} />
          </div>
        </>
      ) : null}

      <div className="absolute bottom-[100px] inset-x-0 z-40 px-4">
        <Toast message={state.rec.kind === "error" ? state.rec.message : ""} onDismiss={() => dispatch({ type: "rec/dismissError" })} visible={errorVisible} />
      </div>

      {!showChatBubble ? <BottomNav /> : null}
    </MobileShell>
  );
}
