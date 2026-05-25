'use client';

import { useEffect, useRef, useCallback } from 'react';
import { Axes, DEFAULT_AXES } from '@/lib/types/character';

interface PallyCanvasProps {
  axes?: Axes;
  size?: number;
  className?: string;
}

function tier(v: number): 0 | 1 | 2 {
  if (v <= 33) return 0;
  if (v <= 66) return 1;
  return 2;
}

function intimacyRgb(v: number): [number, number, number] {
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
}: PallyCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef    = useRef<number>(0);
  const t0Ref     = useRef<number>(0);
  const axesRef   = useRef(axes);

  useEffect(() => { axesRef.current = axes; }, [axes]);

  const draw = useCallback((ctx: CanvasRenderingContext2D, t: number) => {
    const ax  = axesRef.current;
    const bs  = size * 0.36;
    const cx  = size / 2;
    const cy  = size / 2;
    ctx.clearRect(0, 0, size, size);

    const cT = tier(ax.Curiosity);
    let oY = 0, oX = 0;
    if      (cT === 0) { oY = Math.sin(t * 0.9) * 4; }
    else if (cT === 1) { oY = Math.sin(t * 1.8) * 8; }
    else               { oY = Math.sin(t * 3.2) * 7; oX = Math.cos(t * 3.2) * 5; }

    ctx.save();
    ctx.translate(cx + oX, cy + oY);

    const [r, g, b] = intimacyRgb(ax.Intimacy);
    const hT = tier(ax.Humor);
    const fT = tier(ax.Formality);

    ctx.shadowColor = `rgba(${r},${g},${b},0.45)`;
    ctx.shadowBlur  = 20;

    if (hT === 0) {
      const rectR = [0, bs * 0.18, bs * 0.75][fT];
      ctx.beginPath();
      ctx.roundRect(-bs, -bs, bs * 2, bs * 2, rectR);
    } else if (hT === 1) {
      const outerR = bs * 1.15;
      const innerR = bs * 0.63;
      const tipR   = [0, 10, 24][fT];
      drawStar(ctx, 8, outerR, innerR, tipR);
    } else {
      const outerR = bs * 1.28;
      const innerR = bs * 0.52;
      const tipR   = [0, 6, 16][fT];
      drawStar(ctx, 12, outerR, innerR, tipR);
    }

    const grad = ctx.createRadialGradient(-bs * 0.15, -bs * 0.2, bs * 0.05, 0, 0, bs);
    grad.addColorStop(0, `rgba(${Math.min(r+70,255)},${Math.min(g+70,255)},${Math.min(b+70,255)},1)`);
    grad.addColorStop(1, `rgba(${r},${g},${b},1)`);
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.shadowBlur = 0;

    // ── 눈 ───────────────────────────────────────────────────────────────
    const eT       = tier(ax.Energy);
    const eyeSpcX  = hT > 0 ? bs * 0.25 : bs * 0.34;
    const eyeBaseY = hT > 0 ? bs * 0.08 : -bs * 0.04;
    const blink    = Math.sin(t * 0.4) > 0.98;
    const scaleY   = blink ? 0.08 : 1;

    for (const ex of [-eyeSpcX, eyeSpcX]) {
      ctx.save();
      ctx.translate(ex, eyeBaseY);
      ctx.scale(1, scaleY);

      if (eT === 0) {
        // eye1: 작은 검정 점
        ctx.beginPath();
        ctx.arc(0, 0, bs * 0.08, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a1a';
        ctx.fill();

      } else if (eT === 1) {
        // eye2: 흰 원 + 검정 원 (위쪽 편심)
        const er       = bs * 0.17;
        const pupilR   = er * 0.72;
        const pupilOff = er * 0.18;
        ctx.beginPath();
        ctx.arc(0, 0, er, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        ctx.beginPath();
        ctx.arc(0, -pupilOff, pupilR, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a1a';
        ctx.fill();

      } else {
        // eye3: 흰 원 + 검정 원 + 노란 마름모
        const er       = bs * 0.17;
        const pupilR   = er * 0.72;
        const pupilOff = er * 0.18;

        // 흰 원
        ctx.beginPath();
        ctx.arc(0, 0, er, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();

        // 검정 원 (위쪽 편심)
        ctx.beginPath();
        ctx.arc(0, -pupilOff, pupilR, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a1a';
        ctx.fill();

        // 노란 마름모 (검정 원 안 중앙)
        const mx = 0;
        const my = -pupilOff;
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
