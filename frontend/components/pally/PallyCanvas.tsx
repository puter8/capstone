'use client';

import { useEffect, useRef, useCallback } from 'react';
import { Axes, DEFAULT_AXES } from '@/lib/types/character';

export type PallyGaze = 'center' | 'up-right';

interface PallyCanvasProps {
  axes?: Axes;
  size?: number;
  className?: string;
  /** Where the pupils look. 'up-right' is used while Pally is thinking. */
  gaze?: PallyGaze;
}

// Per-frame easing toward the target gaze so the pupils glide instead of jumping.
const GAZE_EASING = 0.15;

function tier(v: number): 0 | 1 | 2 {
  if (v <= 33) return 0;
  if (v <= 66) return 1;
  return 2;
}

// Normalizes an axis score to [0,1] for continuous (non-tiered) use.
function u(v: number): number {
  return Math.max(0, Math.min(100, v)) / 100;
}

// Intimacy → 몸통 색상 (2026-10-12, 축-요소 매핑 2차 수정으로 원래 의미적 짝
// 복원: "친밀할수록 따뜻한 색"). 신뢰도가 가장 높은(결정론적) 축이라 0~100
// 전체 범위를 연속 보간으로 그대로 쓴다 — 차분한 파랑 → 중립색 → 따뜻한 코랄.
function intimacyRgb(v: number): [number, number, number] {
  const t = u(v);
  let h: number, s: number, l: number;
  if (t <= 0.5) {
    const k = t / 0.5;
    h = 210 + (52 - 210) * k; s = 55 + (90 - 55) * k; l = 63 + (61 - 63) * k;
  } else {
    const k = (t - 0.5) / 0.5;
    h = 52 + (0 - 52) * k; s = 90 + (100 - 90) * k; l = 61 + (71 - 61) * k;
  }
  s /= 100; l /= 100;
  const kf = (n: number) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => Math.round((l - a * Math.max(-1, Math.min(kf(n) - 3, Math.min(9 - kf(n), 1)))) * 255);
  return [f(0), f(8), f(4)];
}

function drawStar(
  ctx: CanvasRenderingContext2D,
  points: number,
  outerR: number,
  innerR: number,
  tipR: number
) {
  const total = points * 2;
  const angleStep = Math.PI / points;

  const vertices: { x: number; y: number }[] = [];

  for (let i = 0; i < total; i++) {
    const angle = -Math.PI / 2 + i * angleStep;
    const radius = i % 2 === 0 ? outerR : innerR;
    vertices.push({
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    });
  }

  const cut = Math.max(0.05, Math.min(0.45, tipR / 60));

  ctx.beginPath();

  for (let i = 0; i < total; i++) {
    const prev = vertices[(i - 1 + total) % total];
    const cur = vertices[i];
    const next = vertices[(i + 1) % total];

    const start = {
      x: cur.x + (prev.x - cur.x) * cut,
      y: cur.y + (prev.y - cur.y) * cut,
    };
    const end = {
      x: cur.x + (next.x - cur.x) * cut,
      y: cur.y + (next.y - cur.y) * cut,
    };

    if (i === 0) ctx.moveTo(start.x, start.y);
    else ctx.lineTo(start.x, start.y);

    ctx.quadraticCurveTo(cur.x, cur.y, end.x, end.y);
  }

  ctx.closePath();
}

export default function PallyCanvas({
  axes = DEFAULT_AXES,
  size = 280,
  className = '',
  gaze = 'center',
}: PallyCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef    = useRef<number>(0);
  const t0Ref     = useRef<number>(0);
  const axesRef   = useRef(axes);
  const gazeTargetRef = useRef(gaze === 'up-right' ? 1 : 0);
  const gazeRef   = useRef(gazeTargetRef.current);

  useEffect(() => { axesRef.current = axes; }, [axes]);
  useEffect(() => { gazeTargetRef.current = gaze === 'up-right' ? 1 : 0; }, [gaze]);

  const draw = useCallback((ctx: CanvasRenderingContext2D, t: number) => {
    const ax  = axesRef.current;
    const bs  = size * 0.36;
    const cx  = size / 2;
    const cy  = size / 2;
    ctx.clearRect(0, 0, size, size);

    // Humor → 전신 움직임 (2026-10-12, 의미적 짝 복원: "유머가 많을수록 통통
    // 튄다"). 그러나 Humor는 150개 라벨 중 140개가 0점일 만큼 이 코퍼스 자체에
    // 신호가 없어 측정이 사실상 불가능했던 축이다 — 점수를 좁은 범위로
    // 압축해도 tier() 경계(33/66) 안에 묻혀 변화가 아예 사라지므로(코덱스
    // 지적), 압축이 아니라 **점수와 무관한 고정 기본값**을 쓴다. 공통 생동감만
    // 유지하고, 근거 없는 "유머 반응"을 지어내지 않는다.
    const Ay = 4;
    const Ax = 0;
    const omega = 0.9;
    const oY = Ay * Math.sin(t * omega);
    const oX = Ax * Math.cos(t * omega);

    ctx.save();
    ctx.translate(cx + oX, cy + oY);

    const [r, g, b] = intimacyRgb(ax.Intimacy);

    // Energy → 몸통 형태·크기 (2026-10-12, 의미적 짝 복원: "활기찰수록
    // 뾰족해진다"). 점수와 무관하게 sT=1(8각별) 고정 — 근거는
    // docs/energy-voice-validation-result-2026-10-12.md: pYIN pitch-range 방식은
    // CREMA-D 검증 FAIL, Gemini 오디오 판단 방식은 CREMA-D 스크린 통과 후 ICSI
    // 대화 음성 사람 채점 게이트 진행 중. 게이트 통과 + 사용자 해제 승인 전까지
    // 비활성. 해제 시 `tier(ax.Energy)`로 교체하되, ax.Energy가 지금처럼 텍스트
    // 규칙(ai/analyzer.py)이 아니라 검증된 음성 채점에서 와야 한다.
    const sT: number = 1; // frozen until the voice-Energy gate passes and the owner approves

    // Formality → 형태 기본 라운딩의 미세 보정 (2026-10-12, 의미적 짝 복원:
    // "격식 있을수록 각진다"). 네 모델 전부 게이트 실패한 영구 저신뢰 축이라
    // 보정 폭을 ±5%로 작게 제한한다 — 형태 자체를 바꾸지 않고 다듬기만 한다.
    const formalityK = 1.05 - 0.10 * u(ax.Formality); // 105%(blunt) → 95%(formal)

    ctx.shadowColor = `rgba(${r},${g},${b},0.45)`;
    ctx.shadowBlur  = 20;

    if (sT === 0) {
      const rectR = bs * 0.18 * formalityK;
      ctx.beginPath();
      ctx.roundRect(-bs, -bs, bs * 2, bs * 2, rectR);
    } else if (sT === 1) {
      const outerR = bs * 1.15;
      const innerR = bs * 0.63;
      const tipR   = 10 * formalityK;
      drawStar(ctx, 8, outerR, innerR, tipR);
    } else {
      const outerR = bs * 1.28;
      const innerR = bs * 0.52;
      const tipR   = 6 * formalityK;
      drawStar(ctx, 12, outerR, innerR, tipR);
    }

    const grad = ctx.createRadialGradient(-bs * 0.15, -bs * 0.2, bs * 0.05, 0, 0, bs);
    grad.addColorStop(0, `rgba(${Math.min(r+70,255)},${Math.min(g+70,255)},${Math.min(b+70,255)},1)`);
    grad.addColorStop(1, `rgba(${r},${g},${b},1)`);
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.shadowBlur = 0;

    // ── 눈 (Curiosity → 세로비율, 2026-10-12 의미적 짝 복원: "호기심이
    // 많을수록 눈이 또렷해진다") ──
    // 기존 3단계(단순 점 / 흰자+검은자 / 장식 마름모) 중 "흰자+검은자" 모양
    // 하나로 고정한다. 세로비율은 저/중 2단계만 쓴다 — TfidfKnn 89.58%는
    // 저·중구간 분류 근거일 뿐이라 고구간엔 추가 표현을 두지 않고 중구간과
    // 같은 값으로 상한을 둔다(고구간 미검증).
    const eyeSpcX  = sT > 0 ? bs * 0.25 : bs * 0.34;
    const eyeBaseY = sT > 0 ? bs * 0.08 : -bs * 0.04;
    const blink      = Math.sin(t * 0.4) > 0.98;
    const blinkScaleY = blink ? 0.08 : 1;
    const eyeY = tier(ax.Curiosity) === 0 ? 0.90 : 1.10;
    // 0 = center, 1 = fully up-right
    gazeRef.current += (gazeTargetRef.current - gazeRef.current) * GAZE_EASING;
    const gz       = gazeRef.current;

    for (const ex of [-eyeSpcX, eyeSpcX]) {
      ctx.save();
      ctx.translate(ex, eyeBaseY);
      ctx.scale(1, blinkScaleY * eyeY);

      const er       = bs * 0.17;
      const pupilR   = er * 0.72;
      const pupilOff = er * 0.18;
      const px       = gz * er * 0.16;
      const py       = -pupilOff - gz * er * 0.04;

      ctx.beginPath();
      ctx.arc(0, 0, er, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.beginPath();
      ctx.arc(px, py, pupilR, 0, Math.PI * 2);
      ctx.fillStyle = '#1a1a1a';
      ctx.fill();

      ctx.restore();
    }

    ctx.restore();
  }, [size]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width  = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width  = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);

    const loop = (ts: number) => {
      if (!t0Ref.current) t0Ref.current = ts;
      draw(ctx, (ts - t0Ref.current) / 1000);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [size, draw]);

  return <canvas ref={canvasRef} className={className} aria-label="Pally character" />;
}
