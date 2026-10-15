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
    // Intimacy=eyebrows, Energy=body shape, Curiosity=body colour (continuous),
    // Formality=eyes, Humor=whole-body motion (inactive: fixed calm bob).
    const oY = Math.sin(t * 0.9) * 4;

    ctx.save();
    ctx.translate(cx, cy + oY);

    const [r, g, b] = curiosityRgb(ax.Curiosity);
    // Energy → body shape: calm=circle → lively=rounded square → energetic=8-point star
    const sT = tier(ax.Energy);

    ctx.shadowColor = `rgba(${r},${g},${b},0.45)`;
    ctx.shadowBlur  = 20;

    if (sT === 2) {
      drawStar(ctx, 8, bs * 1.15, bs * 0.63, 10);
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

        // 노란 마름모 (검정 원 안 중앙)
        const mx = px;
        const my = py;
        const hw = pupilR * 0.40; // 가로 반폭
        const hh = pupilR * 0.55; // 세로 반폭 (세로로 약간 길게)
        ctx.beginPath();
        ctx.moveTo(mx,      my - hh); // 위
        ctx.lineTo(mx + hw, my);      // 오른쪽
        ctx.lineTo(mx,      my + hh); // 아래
        ctx.lineTo(mx - hw, my);      // 왼쪽
        ctx.closePath();
        ctx.fillStyle = '#FFD700';
        ctx.fill();
      }

      ctx.restore();
    }

    // ── 눈썹 (Intimacy → acquaint=한쪽만 올린 눈썹 → buddy=부드러운 아치 → bestie=반듯한 일자) ──
    const iT     = tier(ax.Intimacy);
    const browY  = eyeBaseY - bs * 0.3;
    const browHw = bs * 0.12;
    ctx.strokeStyle = '#3a2a1a';
    ctx.lineCap     = 'round';
    ctx.lineWidth   = bs * (iT === 2 ? 0.055 : 0.045);
    for (const side of [-1, 1]) {
      const bx = side * eyeSpcX;
      ctx.beginPath();
      if (iT === 0 && side === 1) {
        // the right brow is raised and tilted up toward the outside
        ctx.moveTo(bx - browHw, browY - bs * 0.02);
        ctx.lineTo(bx + browHw, browY - bs * 0.12);
      } else if (iT === 1) {
        ctx.moveTo(bx - browHw, browY);
        ctx.quadraticCurveTo(bx, browY - bs * 0.1, bx + browHw, browY);
      } else {
        ctx.moveTo(bx - browHw, browY);
        ctx.lineTo(bx + browHw, browY);
      }
      ctx.stroke();
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
