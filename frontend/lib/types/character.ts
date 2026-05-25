/**
 * character.ts
 * ============
 * Phase 1B — 김민주 소유
 *
 * ai/analyzer.py + ai/matrix_engine.py 실제 출력 구조를 기반으로 정의한 TS 타입.
 * Canvas2D 렌더러(PallyCanvas)가 이 타입을 그대로 받아 렌더링하며 별도 변환 레이어 없음.
 *
 * 출처:
 *   analyzer.py → analyze_utterance() → Axes (5축 점수)
 *   matrix_engine.py → compute_character() → CharacterParams (시각 파라미터)
 *   matrix_engine.py → apply_ema() → Axes (EMA 보정 후)
 */

// ---------------------------------------------------------------------------
// 5축 점수 (Axes)
// analyzer.py analyze_utterance() 반환값과 1:1 대응
// matrix_engine.py apply_ema() 입출력도 동일 구조
// ---------------------------------------------------------------------------

export interface Axes {
  /** 격식도: 0=슬랭/비격식, 100=매우 격식체 */
  Formality: number;   // 0~100
  /** 에너지: 0=저에너지/차분, 100=고에너지/활발 */
  Energy: number;      // 0~100
  /** 친밀도: 0=거리감, 100=매우 친근 */
  Intimacy: number;    // 0~100
  /** 유머: 0=진지, 100=유머/장난기 */
  Humor: number;       // 0~100
  /** 호기심: 0=선언적, 100=탐구적/질문 */
  Curiosity: number;   // 0~100
}

/** 기본 5축 초기값 (세션 시작 전 / EMA prev 초기화용) */
export const DEFAULT_AXES: Axes = {
  Formality: 50,
  Energy: 30,
  Intimacy: 20,
  Humor: 10,
  Curiosity: 15,
};

// ---------------------------------------------------------------------------
// 캐릭터 시각 파라미터 (CharacterParams)
// matrix_engine.py compute_character() 반환값 + 시각 디자인 스펙 확장
//
// 시각 매핑 스펙 (이미지 기준):
//   Humor   → spikiness (뾰족함): 0~33=사각, 34~66=중간별, 67~100=날카로운별
//   Formality → borderRadius: 0=사각(radius 0), 50=둥글(radius 40), 100=원(radius 100)
//   Energy  → eyeType: 'small'(0~33) | 'large'(34~66) | 'glowing'(67~100)
//   Intimacy → bodyColor: 파랑(0) → 노랑(50) → 빨강(100)
//   Curiosity → animationSpeed: 'slow'(0~33) | 'medium'(34~66) | 'fast'(67~100)
// ---------------------------------------------------------------------------

export interface CharacterParams {
  // --- matrix_engine.py compute_character() 직접 출력 ---

  /** 캐주얼 말투 정도: 0=격식체, 100=슬랭 자유 사용 */
  tone_casual: number;    // 0~100

  /** 반응 에너지 수준: 0=차분, 100=매우 활발 */
  energy_level: number;  // 0~100

  /** 유머/장난기 정도: 0=진지, 100=밈·유머 모드 */
  humor_level: number;   // 0~100

  // --- Canvas2D 렌더링용 파생 시각 파라미터 ---
  // (Axes에서 직접 매핑, 별도 변환 없이 렌더러가 그대로 사용)

  /**
   * 몸통 뾰족함 (Humor 축 기반)
   * 0=완전한 사각형, 50=중간 별, 100=날카로운 별
   * Superformula m 파라미터와 연결됨
   */
  spikiness: number;     // 0~100

  /**
   * 모서리 둥글기 (Formality 축 기반)
   * 0=사각형(border-radius 0), 100=원(border-radius 100%)
   * CSS border-radius % 또는 Canvas arc radius로 변환
   */
  borderRadius: number;  // 0~100

  /**
   * 눈 타입 (Energy 축 기반)
   * 'small'  : 0~33  — 작고 검정, 낮은 에너지
   * 'large'  : 34~66 — 크고 검정, 중간 에너지
   * 'glowing': 67~100 — 크고 노란 빛, 고에너지
   */
  eyeType: 'small' | 'large' | 'glowing';

  /**
   * 몸통 색상 (Intimacy 축 기반)
   * 0   → 차가운 파랑  (#6B9FD4)
   * 50  → 따뜻한 노랑  (#F5E642)
   * 100 → 따뜻한 빨강  (#FF6B6B)
   * 렌더러에서 HSL 보간으로 처리
   */
  bodyColor: string;     // CSS 색상 문자열

  /**
   * 애니메이션 속도 (Curiosity 축 기반)
   * 'slow'   : 0~33  — 움직임 1 (느린 bob)
   * 'medium' : 34~66 — 움직임 2 (중간 bounce)
   * 'fast'   : 67~100 — 움직임 3 (빠른 wiggle)
   */
  animationSpeed: 'slow' | 'medium' | 'fast';
}

/** 기본 캐릭터 파라미터 (세션 시작 전 / 로딩 중 표시용) */
export const DEFAULT_CHARACTER_PARAMS: CharacterParams = {
  tone_casual: 50,
  energy_level: 20,
  humor_level: 10,
  spikiness: 0,
  borderRadius: 40,
  eyeType: 'small',
  bodyColor: '#B8C9E0',
  animationSpeed: 'slow',
};

// ---------------------------------------------------------------------------
// 유틸리티: Axes → CharacterParams 변환
// backend /api/chat 응답의 axes + character 필드를 FE에서 합성할 때 사용
// (백엔드가 CharacterParams 전체를 내려줄 때는 이 함수 불필요)
// ---------------------------------------------------------------------------

/**
 * Intimacy 점수(0~100)를 HSL 보간 색상으로 변환
 * 0   → hsl(210, 55%, 63%)  파랑
 * 50  → hsl(52,  90%, 61%)  노랑
 * 100 → hsl(0,   100%, 71%) 빨강
 */
export function intimacyToColor(intimacy: number): string {
  const t = Math.max(0, Math.min(100, intimacy)) / 100;
  if (t <= 0.5) {
    // 파랑 → 노랑
    const u = t / 0.5;
    const h = Math.round(210 + (52 - 210) * u);
    const s = Math.round(55 + (90 - 55) * u);
    const l = Math.round(63 + (61 - 63) * u);
    return `hsl(${h}, ${s}%, ${l}%)`;
  } else {
    // 노랑 → 빨강
    const u = (t - 0.5) / 0.5;
    const h = Math.round(52 + (0 - 52) * u);
    const s = Math.round(90 + (100 - 90) * u);
    const l = Math.round(61 + (71 - 61) * u);
    return `hsl(${h}, ${s}%, ${l}%)`;
  }
}

/** Energy 점수 → eyeType 변환 */
export function energyToEyeType(energy: number): CharacterParams['eyeType'] {
  if (energy <= 33) return 'small';
  if (energy <= 66) return 'large';
  return 'glowing';
}

/** Curiosity 점수 → animationSpeed 변환 */
export function curiosityToAnimSpeed(curiosity: number): CharacterParams['animationSpeed'] {
  if (curiosity <= 33) return 'slow';
  if (curiosity <= 66) return 'medium';
  return 'fast';
}

/**
 * Axes 전체를 CharacterParams로 변환
 * matrix_engine.py compute_character() 결과(tone/energy/humor)와
 * Axes 직접 매핑(visual params)을 합쳐서 완전한 CharacterParams를 만듦
 *
 * @param axes   EMA 보정 후 5축 점수
 * @param computed matrix_engine.compute_character() 결과 (백엔드에서 내려줌)
 */
export function axesToCharacterParams(
  axes: Axes,
  computed: Pick<CharacterParams, 'tone_casual' | 'energy_level' | 'humor_level'>
): CharacterParams {
  return {
    ...computed,
    spikiness: axes.Humor,
    borderRadius: axes.Formality,
    eyeType: energyToEyeType(axes.Energy),
    bodyColor: intimacyToColor(axes.Intimacy),
    animationSpeed: curiosityToAnimSpeed(axes.Curiosity),
  };
}

// ---------------------------------------------------------------------------
// /api/chat 응답 wire format (Phase 1C 백엔드와 동기화)
// backend/main.py ChatResponse Pydantic 모델과 대응
// ---------------------------------------------------------------------------

export interface ChatApiResponse {
  /** Pally 영어 응답 텍스트 */
  reply: string;
  /** TTS 음성 (base64 MP3) */
  tts_audio: string;
  /** EMA 보정 후 5축 점수 */
  axes: Axes;
  /** 캐릭터 파라미터 (matrix_engine 출력) */
  character: Pick<CharacterParams, 'tone_casual' | 'energy_level' | 'humor_level'>;
  /** 인라인 한국어 힌트 */
  hint_ko: {
    hint: string;
  };
}