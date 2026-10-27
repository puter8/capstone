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

// Curiosity → body colour, continuous blue → yellow → red (final mapping, 2026-10-14).
function curiosityRgb(v: number): [number, number, number] {
  const t = Math.max(0, Math.min(100, v)) / 100;
  let h: number, s: number, l: number;
  if (t <= 0.5) {
    const u = t / 0.5;
    h = 210 + (52 - 210) * u; s = 55 + (90 - 55) * u; l = 63 + (61 - 63) * u;
  } else {
    const u = (t - 0.5) / 0.5;
    h = 52 + (0 - 52) * u; s = 90 + (100 - 90) * u; l = 61 + (71 - 61) * u;
  }
  s /= 100; l /= 100;
  const k = (n: number) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => Math.round((l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))) * 255);
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

    // Final mapping (Figma "Pally 5축 → 캐릭터 매핑 가이드", 2026-10-14):
    // Intimacy=mouth, Energy=body shape, Curiosity=body colour (continuous),
    // Formality=eyes, Humor=whole-body motion.
    //
    // Humor → 움직임(bob/bounce/wiggle): serious=거의 정지, ridiculous=활발한 wiggle.
    // 최종 매핑으로 옮길 때 고정 bob 으로 비워뒀던 자리에, 이전 매핑에서 쓰던 3단계를
    // 그대로 되돌린다. 0단계가 그 고정값과 같아 차분한 쪽 모습은 바뀌지 않는다.
    const mT = tier(ax.Humor);
    let oY = 0, oX = 0;
    if      (mT === 0) { oY = Math.sin(t * 0.9) * 4; }
    else if (mT === 1) { oY = Math.sin(t * 1.8) * 8; }
    else               { oY = Math.sin(t * 3.2) * 7; oX = Math.cos(t * 3.2) * 5; }

    ctx.save();
    ctx.translate(cx + oX, cy + oY);

    const [r, g, b] = curiosityRgb(ax.Curiosity);
    // Energy → body shape: calm=circle → lively=rounded square → energetic=8-point star
    const sT = tier(ax.Energy);

    ctx.shadowColor = `rgba(${r},${g},${b},0.45)`;
    ctx.shadowBlur  = 20;

    if (sT === 2) {
      // Tip angle comes from innerR/outerR: 0.63 gave a 46° spike, which read as sharp
      // rather than lively. 0.78 opens it to 70°. Raise innerR to blunt it further
      // (0.85 is 84°); tipR only rounds the very point and saturates at 27.
      drawStar(ctx, 8, bs * 1.15, bs * 0.78, 10);
    } else {
      ctx.beginPath();
      ctx.roundRect(-bs, -bs, bs * 2, bs * 2, sT === 0 ? bs : bs * 0.3);
    }

    const grad = ctx.createRadialGradient(-bs * 0.15, -bs * 0.2, bs * 0.05, 0, 0, bs);
    grad.addColorStop(0, `rgba(${Math.min(r+70,255)},${Math.min(g+70,255)},${Math.min(b+70,255)},1)`);
    grad.addColorStop(1, `rgba(${r},${g},${b},1)`);
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.shadowBlur = 0;

    // ── 눈 (Formality → blunt=단순한 점 → casual=흰자+동공 → formal=반짝이는 눈) ──
    const eT       = tier(ax.Formality);
    const eyeSpcX  = sT === 2 ? bs * 0.25 : bs * 0.34;
    const eyeBaseY = sT === 2 ? bs * 0.08 : -bs * 0.04;
    const blink    = Math.sin(t * 0.4) > 0.98;
    const scaleY   = blink ? 0.08 : 1;
    // 0 = center, 1 = fully up-right
    gazeRef.current += (gazeTargetRef.current - gazeRef.current) * GAZE_EASING;
    const gz       = gazeRef.current;

    for (const ex of [-eyeSpcX, eyeSpcX]) {
      ctx.save();
      ctx.translate(ex, eyeBaseY);
      ctx.scale(1, scaleY);

      if (eT === 0) {
        // eye1: 작은 검정 점
        ctx.beginPath();
        ctx.arc(gz * bs * 0.09, -gz * bs * 0.07, bs * 0.08, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a1a';
        ctx.fill();

      } else if (eT === 1) {
        // eye2: 흰 원 + 검정 원 (위쪽 편심)
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

      } else {
        // eye3: 흰 원 + 검정 원 + 노란 마름모
        const er       = bs * 0.17;
        const pupilR   = er * 0.72;
        const pupilOff = er * 0.18;
        const px       = gz * er * 0.16;
        const py       = -pupilOff - gz * er * 0.04;

        // 흰 원
        ctx.beginPath();
        ctx.arc(0, 0, er, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();

        // 검정 원 (위쪽 편심)
        ctx.beginPath();
        ctx.arc(px, py, pupilR, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a1a';
        ctx.fill();

        // 노란 반짝임. 4각 별 — 눈 안이 작아 꼭짓점이 많으면 뭉개져서 점으로
        // 보인다. 안쪽 반지름을 바깥의 28%로 깊게 파야 반짝임으로 읽히고, 그보다
        // 얕으면 마름모와 구별되지 않는다.
        // 동공 중앙이 아니라 좌상단에 둔다 — 눈에 비친 빛처럼 보이게. 시선과 함께
        // 움직이도록 동공 좌표(px, py)를 기준으로 한다.
        const sparkleOuter = pupilR * 0.45;
        const sparkleInner = sparkleOuter * 0.28;
        const sparkleX = px - pupilR * 0.30;
        const sparkleY = py - pupilR * 0.30;
        ctx.beginPath();
        for (let s = 0; s < 8; s++) {
          const a = -Math.PI / 2 + (s * Math.PI) / 4;
          const sr = s % 2 === 0 ? sparkleOuter : sparkleInner;
          const sx = sparkleX + Math.cos(a) * sr;
          // 세로로 살짝 길게 — 원래 마름모의 비율을 유지한다
          const sy = sparkleY + Math.sin(a) * sr * 1.25;
          if (s === 0) ctx.moveTo(sx, sy);
          else ctx.lineTo(sx, sy);
        }
        ctx.closePath();
        ctx.fillStyle = '#FFD700';
        ctx.fill();
      }

      ctx.restore();
    }

    // ── 입 (Intimacy → acquaint=ㅅ자 입 → buddy=작은 미소 → bestie=활짝 웃는 입) ──
    const iT     = tier(ax.Intimacy);
    const mouthY = eyeBaseY + bs * 0.27;
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineCap     = 'round';
    ctx.lineJoin    = 'round';
    ctx.lineWidth   = bs * 0.035;
    ctx.beginPath();
    if (iT === 0) {
      // 'ㅅ'-shaped mouth: both corners down, peak in the middle
      const w = bs * 0.09;
      ctx.moveTo(-w, mouthY + bs * 0.035);
      ctx.lineTo(0, mouthY - bs * 0.03);
      ctx.lineTo(w, mouthY + bs * 0.035);
    } else if (iT === 1) {
      const w = bs * 0.08;
      ctx.moveTo(-w, mouthY);
      ctx.quadraticCurveTo(0, mouthY + bs * 0.1, w, mouthY);
    } else {
      const w = bs * (sT === 2 ? 0.36 : 0.48); // narrower inside the star's inner valleys
      const top = mouthY - bs * 0.04;
      ctx.moveTo(-w - bs * 0.05, top - bs * 0.05);
      ctx.lineTo(-w, top);
      ctx.quadraticCurveTo(0, top + bs * 0.42, w, top);
      ctx.lineTo(w + bs * 0.05, top - bs * 0.05);
    }
    ctx.stroke();

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
