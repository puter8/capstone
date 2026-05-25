'use client';

import { useCallback, useEffect, useReducer } from 'react';
import { reducer, initialState } from '@/lib/state/conversation';
import { useRecorder } from '@/lib/audio/useRecorder';
import { mockChat } from '@/lib/mocks/chat-mock';
import type { Message } from '@/lib/types/message';
import type { ChatApiResponse } from '@/lib/types/character';
import { usePally } from '@/lib/hooks/usePally';
import PallyCanvas from '@/components/pally/PallyCanvas';
import { EmptyGreeting } from '@/components/chat/EmptyGreeting';
import { ChatBubble } from '@/components/chat/ChatBubble';
import { TalkButton } from '@/components/audio/TalkButton';
import { BottomNav } from '@/components/nav/BottomNav';
import { Toast } from '@/components/ui/Toast';

// Layout coordinates from Figma 427:2216 "Pally talk - 새 채팅" (402×874):
//   empty-title       y=253  (gap 16 from hint)
//   empty-hint        y=293
//   Pally character   y=370  w=h=262 → ends y=632
//   TalkButton idle   y=616  w=h=104 → ends y=720 (overlaps character bottom 16px)
//   GNB               y=753  w=389 h=110
// All absolute-positioned relative to the 402-wide main container so the
// composition matches Figma 1:1 on mobile.

export default function Page() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { axes, updateFromChatResponse } = usePally();

  // Persist sessionId in localStorage so refresh reuses the same session.
  // SSR-safe: window check, only runs client-side.
  useEffect(() => {
    if (state.sessionId !== null) return;
    const KEY = 'pally:sessionId';
    const stored = window.localStorage.getItem(KEY);
    if (stored) {
      dispatch({ type: 'sessionId/set', id: stored });
      return;
    }
    const id =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `session-${Date.now()}`;
    window.localStorage.setItem(KEY, id);
    dispatch({ type: 'sessionId/set', id });
  }, [state.sessionId]);

  const handleProcessed = useCallback(
    async (utterance: string) => {
      if (!state.sessionId) return;
      try {
        const res = await mockChat({
          utterance,
          session_id: state.sessionId,
          level: 'B1',
        });
        const userMsg: Message = {
          id: `m-${Date.now()}-u`,
          sessionId: state.sessionId,
          role: 'user',
          transcript: res.transcript,
          createdAt: new Date().toISOString(),
        };
        const pallyMsg: Message = {
          id: `m-${Date.now()}-p`,
          sessionId: state.sessionId,
          role: 'pally',
          transcript: res.reply,
          createdAt: new Date().toISOString(),
        };
        dispatch({ type: 'rec/processed', userMsg, pallyMsg });
        // Update Pally character morph from response.axes.
        // mock ChatResponse vs 1B's ChatApiResponse only diverge on optional
        // fields the hook ignores — usePally only reads `axes`. Phase 2 swap
        // to real /api/chat returns ChatApiResponse directly.
        updateFromChatResponse(res as unknown as ChatApiResponse);
        // 1A has no TTS audio — hold speaking long enough to inspect the bubble.
        // Phase 2 (1C 연결) 때 실제 TTS playback end 시점으로 교체.
        window.setTimeout(() => dispatch({ type: 'rec/speakingDone' }), 6000);
      } catch {
        dispatch({
          type: 'rec/error',
          reason: 'generic',
          message: '응답을 가져오지 못했어요. 다시 시도해 주세요.',
        });
      }
    },
    [state.sessionId, updateFromChatResponse],
  );

  const recorder = useRecorder({
    onStart: () => dispatch({ type: 'rec/start' }),
    onStop: (blob) => {
      dispatch({ type: 'rec/stop' });
      // 1A: use Figma sample utterance. Phase 1C swaps to real STT result.
      void handleProcessed("I had no lunch I'm diet");
      void blob;
    },
    onPermissionDenied: () =>
      dispatch({
        type: 'rec/error',
        reason: 'permission-denied',
        message: '마이크 권한이 필요해요. 브라우저 설정에서 허용해주세요.',
      }),
    onError: (message) =>
      dispatch({ type: 'rec/error', reason: 'generic', message }),
  });

  const handlePressStart = useCallback(() => {
    void recorder.start();
  }, [recorder]);

  const handlePressStop = useCallback(() => {
    recorder.stop();
  }, [recorder]);

  const isIdle = state.rec.kind === 'idle';
  const isProcessing = state.rec.kind === 'processing';
  const isRecording = state.rec.kind === 'recording';
  const errorVisible = state.rec.kind === 'error';
  // Home is the entry surface. Greeting + character + orange mic in idle.
  // ChatBubble only appears during active conversation (processing/speaking).
  const showChatBubble = !isIdle && !isRecording && !errorVisible;
  const showEmptyGreeting = isIdle;
  // Character + TalkButton: hidden only when history is expanded *during* a live conversation.
  // In idle the greeting takes over, so historyOpen residue must not blank the screen.
  const historyCoversScreen = state.historyOpen && !isIdle;
  const showCharacter = !historyCoversScreen;

  // TalkButton y shifts when ChatBubble is above it.
  const talkButtonTop = showChatBubble ? 625 : 616;

  return (
    <main className="relative mx-auto w-full max-w-[402px] min-h-[874px] bg-surface overflow-hidden">
      {/* Top: ChatBubble (covers top region from y=0). Long mode covers character + button. */}
      {showChatBubble && (
        <div className="absolute top-0 inset-x-0 z-10">
          <ChatBubble
            messages={state.messages}
            expanded={state.historyOpen}
            thinking={isProcessing}
            onToggleExpand={() => dispatch({ type: 'history/toggle' })}
          />
        </div>
      )}

      {/* EmptyGreeting at y=253 (Figma empty-title) */}
      {showEmptyGreeting && (
        <div className="absolute top-[253px] inset-x-0 flex justify-center z-10">
          <EmptyGreeting />
        </div>
      )}

      {/* Pally character at y=370 (Figma Group 7) — 1B PallyCanvas with axes */}
      {showCharacter && (
        <div className="absolute top-[370px] left-1/2 -translate-x-1/2 z-0">
          <PallyCanvas axes={axes} size={262} />
        </div>
      )}

      {/* TalkButton at y=616/625 */}
      {!historyCoversScreen && (
        <div
          className="absolute left-1/2 -translate-x-1/2 z-20"
          style={{ top: talkButtonTop }}
        >
          <TalkButton
            rec={state.rec}
            onPressStart={handlePressStart}
            onPressStop={handlePressStop}
          />
        </div>
      )}

      {/* Toast above BottomNav */}
      <div className="absolute bottom-[100px] inset-x-0 px-4 z-40">
        <Toast
          message={state.rec.kind === 'error' ? state.rec.message : ''}
          visible={errorVisible}
          onDismiss={() => dispatch({ type: 'rec/dismissError' })}
        />
      </div>

      {/* GNB fixed at bottom */}
      <BottomNav />
    </main>
  );
}
