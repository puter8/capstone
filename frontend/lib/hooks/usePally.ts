/**
 * usePally.ts — Phase 1B 김민주
 * 
 * /api/chat 응답을 받아 PallyCanvas에 넘길 axes를 관리하는 hook.
 * 1A(이찬희)가 메인 화면에서 이 hook만 import해서 쓰면 됨.
 *
 * 사용법:
 *   const { axes, updateFromChatResponse, isLoading, setIsLoading } = usePally();
 *   <PallyCanvas axes={axes} />
 */

import { useState, useCallback } from 'react';
import { Axes, DEFAULT_AXES, ChatApiResponse } from '@/lib/types/character';

interface UsePallyReturn {
  /** PallyCanvas에 직접 넘길 axes */
  axes: Axes;
  /** /api/chat 응답 받으면 이 함수 호출 → axes 자동 업데이트 */
  updateFromChatResponse: (res: ChatApiResponse) => void;
  /** STT 녹음 중 / Gemini 응답 대기 중 여부 */
  isLoading: boolean;
  setIsLoading: (v: boolean) => void;
  /** axes 직접 리셋 (세션 초기화 시) */
  resetAxes: () => void;
}

export function usePally(): UsePallyReturn {
  const [axes, setAxes] = useState<Axes>(DEFAULT_AXES);
  const [isLoading, setIsLoading] = useState(false);

  const updateFromChatResponse = useCallback((res: ChatApiResponse) => {
    // /api/chat 응답의 axes를 그대로 PallyCanvas에 반영
    setAxes(res.axes);
  }, []);

  const resetAxes = useCallback(() => {
    setAxes(DEFAULT_AXES);
  }, []);

  return { axes, updateFromChatResponse, isLoading, setIsLoading, resetAxes };
}